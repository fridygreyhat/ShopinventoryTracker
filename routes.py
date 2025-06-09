import logging
from datetime import datetime, timedelta
from decimal import Decimal
from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func, desc, and_
from app import app, db
from models import User, Category, Item, Sale, SaleItem, StockMovement, FinancialTransaction

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=True)
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.first_name}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password, or account is inactive.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get summary statistics
    total_items = Item.query.filter_by(is_active=True).count()
    low_stock_items = Item.query.filter(Item.is_active == True, Item.stock_quantity <= Item.minimum_stock).count()
    
    # Recent sales (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_sales = db.session.query(func.sum(Sale.total_amount)).filter(Sale.created_at >= thirty_days_ago).scalar() or 0
    
    # Today's sales
    today = datetime.utcnow().date()
    today_sales = db.session.query(func.sum(Sale.total_amount)).filter(func.date(Sale.created_at) == today).scalar() or 0
    
    # Recent transactions
    recent_transactions = Sale.query.order_by(desc(Sale.created_at)).limit(5).all()
    
    return render_template('dashboard.html',
                         total_items=total_items,
                         low_stock_items=low_stock_items,
                         recent_sales=recent_sales,
                         today_sales=today_sales,
                         recent_transactions=recent_transactions)

@app.route('/inventory')
@login_required
def inventory():
    search = request.args.get('search', '')
    category_id = request.args.get('category_id', type=int)
    
    query = Item.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(Item.name.contains(search))
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    items = query.order_by(Item.name).all()
    categories = Category.query.order_by(Category.name).all()
    
    return render_template('inventory.html', items=items, categories=categories, search=search, selected_category=category_id)

@app.route('/add_item', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        try:
            item = Item(
                name=request.form['name'],
                description=request.form.get('description', ''),
                sku=request.form['sku'],
                price=Decimal(request.form['price']),
                cost=Decimal(request.form.get('cost', 0)),
                stock_quantity=int(request.form.get('stock_quantity', 0)),
                minimum_stock=int(request.form.get('minimum_stock', 0)),
                category_id=int(request.form['category_id'])
            )
            
            db.session.add(item)
            db.session.commit()
            
            # Create initial stock movement if stock_quantity > 0
            if item.stock_quantity > 0:
                stock_movement = StockMovement(
                    movement_type='in',
                    quantity=item.stock_quantity,
                    reason='Initial stock',
                    item_id=item.id
                )
                db.session.add(stock_movement)
                db.session.commit()
            
            flash(f'Item "{item.name}" has been added successfully!', 'success')
            return redirect(url_for('inventory'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding item: {str(e)}', 'danger')
    
    categories = Category.query.order_by(Category.name).all()
    return render_template('add_item.html', categories=categories)

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    
    if request.method == 'POST':
        try:
            old_stock = item.stock_quantity
            
            item.name = request.form['name']
            item.description = request.form.get('description', '')
            item.sku = request.form['sku']
            item.price = Decimal(request.form['price'])
            item.cost = Decimal(request.form.get('cost', 0))
            item.minimum_stock = int(request.form.get('minimum_stock', 0))
            item.category_id = int(request.form['category_id'])
            
            new_stock = int(request.form.get('stock_quantity', 0))
            
            # Create stock movement if quantity changed
            if new_stock != old_stock:
                movement_type = 'in' if new_stock > old_stock else 'out'
                quantity = abs(new_stock - old_stock)
                
                stock_movement = StockMovement(
                    movement_type=movement_type,
                    quantity=quantity,
                    reason='Stock adjustment',
                    item_id=item.id
                )
                db.session.add(stock_movement)
                item.stock_quantity = new_stock
            
            db.session.commit()
            flash(f'Item "{item.name}" has been updated successfully!', 'success')
            return redirect(url_for('inventory'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating item: {str(e)}', 'danger')
    
    categories = Category.query.order_by(Category.name).all()
    return render_template('add_item.html', item=item, categories=categories)

@app.route('/sales')
@login_required
def sales():
    page = request.args.get('page', 1, type=int)
    sales = Sale.query.order_by(desc(Sale.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('sales.html', sales=sales)

@app.route('/pos')
@login_required
def pos():
    items = Item.query.filter_by(is_active=True).filter(Item.stock_quantity > 0).order_by(Item.name).all()
    return render_template('pos.html', items=items)

@app.route('/process_sale', methods=['POST'])
@login_required
def process_sale():
    try:
        cart_items = session.get('cart', [])
        if not cart_items:
            flash('Cart is empty!', 'warning')
            return redirect(url_for('pos'))
        
        # Calculate totals
        subtotal = Decimal('0')
        tax_rate = Decimal(request.form.get('tax_rate', '0')) / 100
        payment_method = request.form.get('payment_method', 'cash')
        
        # Create sale
        sale_number = f"SALE-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        sale = Sale(
            sale_number=sale_number,
            subtotal=Decimal('0'),  # Will be calculated
            tax_rate=tax_rate,
            tax_amount=Decimal('0'),  # Will be calculated
            total_amount=Decimal('0'),  # Will be calculated
            payment_method=payment_method,
            user_id=current_user.id
        )
        
        db.session.add(sale)
        db.session.flush()  # Get the sale ID
        
        # Process cart items
        for cart_item in cart_items:
            item = Item.query.get(cart_item['item_id'])
            if not item or item.stock_quantity < cart_item['quantity']:
                raise Exception(f"Insufficient stock for {item.name if item else 'unknown item'}")
            
            # Create sale item
            unit_price = Decimal(str(cart_item['price']))
            quantity = cart_item['quantity']
            total_price = unit_price * quantity
            
            sale_item = SaleItem(
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
                sale_id=sale.id,
                item_id=item.id
            )
            db.session.add(sale_item)
            
            # Update stock
            item.stock_quantity -= quantity
            
            # Create stock movement
            stock_movement = StockMovement(
                movement_type='out',
                quantity=quantity,
                reason=f'Sale {sale_number}',
                item_id=item.id
            )
            db.session.add(stock_movement)
            
            subtotal += total_price
        
        # Calculate tax and total
        tax_amount = subtotal * tax_rate
        total_amount = subtotal + tax_amount
        
        # Update sale totals
        sale.subtotal = subtotal
        sale.tax_amount = tax_amount
        sale.total_amount = total_amount
        
        db.session.commit()
        
        # Clear cart
        session.pop('cart', None)
        
        flash(f'Sale {sale_number} completed successfully! Total: ${total_amount:.2f}', 'success')
        return redirect(url_for('pos'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing sale: {str(e)}', 'danger')
        return redirect(url_for('pos'))

@app.route('/financial')
@login_required
def financial():
    page = request.args.get('page', 1, type=int)
    transaction_type = request.args.get('type', '')
    
    query = FinancialTransaction.query
    if transaction_type:
        query = query.filter_by(transaction_type=transaction_type)
    
    transactions = query.order_by(desc(FinancialTransaction.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Summary statistics
    total_income = db.session.query(func.sum(FinancialTransaction.amount)).filter_by(transaction_type='income').scalar() or 0
    total_expenses = db.session.query(func.sum(FinancialTransaction.amount)).filter_by(transaction_type='expense').scalar() or 0
    net_profit = total_income - total_expenses
    
    return render_template('financial.html', 
                         transactions=transactions,
                         total_income=total_income,
                         total_expenses=total_expenses,
                         net_profit=net_profit,
                         selected_type=transaction_type)

@app.route('/add_transaction', methods=['POST'])
@login_required
def add_transaction():
    try:
        transaction_number = f"TXN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        transaction = FinancialTransaction(
            transaction_number=transaction_number,
            transaction_type=request.form['transaction_type'],
            category=request.form['category'],
            amount=Decimal(request.form['amount']),
            tax_amount=Decimal(request.form.get('tax_amount', 0)),
            description=request.form['description'],
            notes=request.form.get('notes', ''),
            reference_number=request.form.get('reference_number', ''),
            user_id=current_user.id
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        flash('Transaction added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding transaction: {str(e)}', 'danger')
    
    return redirect(url_for('financial'))

@app.route('/users')
@login_required
def users():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.order_by(User.username).all()
    return render_template('users.html', users=users)

@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        user = User(
            username=request.form['username'],
            email=request.form['email'],
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            is_admin=bool(request.form.get('is_admin'))
        )
        user.set_password(request.form['password'])
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'User "{user.username}" has been created successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating user: {str(e)}', 'danger')
    
    return redirect(url_for('users'))

@app.route('/toggle_user_status/<int:user_id>')
@login_required
def toggle_user_status(user_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'warning')
        return redirect(url_for('users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User "{user.username}" has been {status}.', 'success')
    
    return redirect(url_for('users'))

# API endpoints for POS system
@app.route('/api/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    try:
        item_id = int(request.form['item_id'])
        quantity = int(request.form['quantity'])
        
        item = Item.query.get_or_404(item_id)
        
        if item.stock_quantity < quantity:
            return jsonify({'success': False, 'message': 'Insufficient stock'})
        
        cart = session.get('cart', [])
        
        # Check if item already in cart
        for cart_item in cart:
            if cart_item['item_id'] == item_id:
                cart_item['quantity'] += quantity
                break
        else:
            cart.append({
                'item_id': item_id,
                'name': item.name,
                'price': float(item.price),
                'quantity': quantity
            })
        
        session['cart'] = cart
        session.modified = True
        
        return jsonify({'success': True, 'message': 'Item added to cart'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/remove_from_cart', methods=['POST'])
@login_required
def remove_from_cart():
    try:
        item_id = int(request.form['item_id'])
        cart = session.get('cart', [])
        
        cart = [item for item in cart if item['item_id'] != item_id]
        session['cart'] = cart
        session.modified = True
        
        return jsonify({'success': True, 'message': 'Item removed from cart'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/get_cart')
@login_required
def get_cart():
    cart = session.get('cart', [])
    return jsonify({'cart': cart})

@app.route('/api/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    session.pop('cart', None)
    return jsonify({'success': True, 'message': 'Cart cleared'})

# Initialize default data
@app.before_first_request
def create_default_data():
    # Create default admin user if no users exist
    if User.query.count() == 0:
        admin = User(
            username='admin',
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Create default categories
        categories = [
            Category(name='Electronics', description='Electronic items and gadgets'),
            Category(name='Clothing', description='Apparel and accessories'),
            Category(name='Books', description='Books and publications'),
            Category(name='Home & Garden', description='Home and garden supplies'),
        ]
        
        for category in categories:
            db.session.add(category)
        
        db.session.commit()
        logging.info("Default admin user and categories created")

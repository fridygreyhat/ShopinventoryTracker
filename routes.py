import logging
from datetime import datetime, timedelta
from decimal import Decimal
from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func, desc, and_, or_
from app import app, db
from models import (User, Category, Item, Sale, SaleItem, StockMovement, FinancialTransaction, 
                    Location, LocationStock, StockTransfer, StockTransferItem, ChartOfAccounts, 
                    Journal, JournalEntry, GeneralLedger, CashFlow, BalanceSheet, BankAccount,
                    Customer, CustomerPurchaseHistory, LoyaltyTransaction)
from auth_service import authenticate_user, create_or_update_user, validate_email_format, validate_password_strength

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Validate email format
        email_valid, email_error = validate_email_format(email)
        if not email_valid:
            flash(email_error, 'danger')
            return render_template('login.html')
        
        # Authenticate user using enhanced auth service
        user = authenticate_user(email, password)
        
        if user:
            login_user(user, remember=True)
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.first_name or user.username}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        shop_name = request.form.get('shop_name', '').strip()
        
        # Validate password confirmation
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        # Prepare user data
        user_data = {
            'email': email,
            'password': password
        }
        
        extra_data = {
            'firstName': first_name,
            'lastName': last_name,
            'shopName': shop_name
        }
        
        # Create user using enhanced auth service
        user, error = create_or_update_user(user_data, extra_data)
        
        if user:
            # Create default location for new user
            default_location = Location(
                name=shop_name or 'Main Store',
                address='',
                location_type='store',
                user_id=user.id
            )
            db.session.add(default_location)
            db.session.commit()
            
            login_user(user)
            flash('Account created successfully! Welcome to your business management system.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(error, 'danger')
    
    return render_template('register.html')

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
    """Enhanced sales overview with payment types and installment management"""
    page = request.args.get('page', 1, type=int)
    sales = Sale.query.filter_by(user_id=current_user.id).order_by(desc(Sale.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Calculate metrics by payment type
    all_sales = Sale.query.filter_by(user_id=current_user.id).all()
    total_sales = sum(float(sale.total_amount) for sale in all_sales)
    cash_sales = sum(float(sale.total_amount) for sale in all_sales if sale.payment_type == 'cash')
    installment_sales = sum(float(sale.total_amount) for sale in all_sales if sale.payment_type == 'installment')
    other_sales = sum(float(sale.total_amount) for sale in all_sales if sale.payment_type == 'other')
    
    # Get installment plans summary
    from models import InstallmentPlan
    active_plans = InstallmentPlan.query.join(Sale).filter(
        Sale.user_id == current_user.id,
        InstallmentPlan.status == 'active'
    ).all()
    
    # Calculate outstanding amounts
    total_outstanding = sum(plan.outstanding_amount for plan in active_plans)
    overdue_count = sum(1 for plan in active_plans if plan.next_due_date and plan.next_due_date < datetime.now().date())
    
    return render_template('sales/list.html', 
                         sales=sales, 
                         total_sales=total_sales,
                         cash_sales=cash_sales,
                         installment_sales=installment_sales, 
                         other_sales=other_sales,
                         active_plans=active_plans,
                         total_outstanding=total_outstanding,
                         overdue_count=overdue_count)

@app.route('/new_sale')
@login_required
def new_sale():
    """Create a new sale with payment options"""
    items = Item.query.filter_by(user_id=current_user.id, is_active=True).filter(Item.stock_quantity > 0).order_by(Item.name).all()
    customers = Customer.query.filter_by(user_id=current_user.id).order_by(Customer.name).all()
    return render_template('sales/new_sale.html', items=items, customers=customers)

@app.route('/process_sale', methods=['POST'])
@login_required
def process_sale():
    """Process sale with cash, installment, or other payment options"""
    try:
        import json
        from datetime import date, timedelta
        
        # Get form data
        cart_data = request.form.get('cart_data')
        if not cart_data:
            flash('Cart is empty!', 'warning')
            return redirect(url_for('new_sale'))
        
        cart_items = json.loads(cart_data)
        total_amount = Decimal(request.form.get('total_amount', '0'))
        payment_type = request.form.get('payment_type', 'cash')
        customer_id = request.form.get('customer_id') or None
        notes = request.form.get('notes', '')
        
        # Validate customer for installment payments
        if payment_type == 'installment' and not customer_id:
            flash('Customer is required for installment payments!', 'danger')
            return redirect(url_for('new_sale'))
        
        # Create sale
        sale_number = f"SALE-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Determine payment status
        payment_status = 'paid' if payment_type == 'cash' else 'pending' if payment_type == 'installment' else 'paid'
        
        sale = Sale(
            sale_number=sale_number,
            total_amount=total_amount,
            payment_type=payment_type,
            payment_status=payment_status,
            notes=notes,
            user_id=current_user.id,
            customer_id=int(customer_id) if customer_id else None
        )
        
        db.session.add(sale)
        db.session.flush()  # Get the sale ID
        
        # Process cart items
        for cart_item in cart_items:
            item = Item.query.get(cart_item['id'])
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
        
        # Handle installment payment setup
        if payment_type == 'installment':
            down_payment = Decimal(request.form.get('down_payment', '0'))
            number_of_installments = int(request.form.get('number_of_installments', '12'))
            frequency = request.form.get('frequency', 'monthly')
            
            remaining_amount = total_amount - down_payment
            installment_amount = remaining_amount / number_of_installments
            
            # Calculate start date based on frequency
            if frequency == 'weekly':
                start_date = date.today() + timedelta(weeks=1)
            elif frequency == 'bi-weekly':
                start_date = date.today() + timedelta(weeks=2)
            else:  # monthly
                start_date = date.today() + timedelta(days=30)
            
            # Create installment plan
            from models import InstallmentPlan
            installment_plan = InstallmentPlan(
                sale_id=sale.id,
                customer_id=customer_id,
                total_amount=total_amount,
                down_payment=down_payment,
                remaining_amount=remaining_amount,
                number_of_installments=number_of_installments,
                installment_amount=installment_amount,
                frequency=frequency,
                start_date=start_date,
                status='active'
            )
            db.session.add(installment_plan)
            
            # Update payment status
            if down_payment > 0:
                sale.payment_status = 'partial'
        
        db.session.commit()
        
        flash(f'Sale {sale_number} completed successfully! Total: ${total_amount:.2f}', 'success')
        
        if payment_type == 'installment':
            flash(f'Installment plan created with {number_of_installments} payments of ${installment_amount:.2f}', 'info')
        
        return redirect(url_for('sales'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing sale: {str(e)}', 'danger')
        return redirect(url_for('new_sale'))

@app.route('/sale/<int:sale_id>')
@login_required
def sale_details(sale_id):
    """View detailed sale information"""
    sale = Sale.query.filter_by(id=sale_id, user_id=current_user.id).first_or_404()
    return render_template('sales/sale_details.html', sale=sale)

@app.route('/manage_installments/<int:sale_id>')
@login_required
def manage_installments(sale_id):
    """Manage installment payments for a sale"""
    sale = Sale.query.filter_by(id=sale_id, user_id=current_user.id).first_or_404()
    
    if sale.payment_type != 'installment':
        flash('This sale does not have an installment plan.', 'warning')
        return redirect(url_for('sales'))
    
    from models import InstallmentPlan, InstallmentPayment
    plan = InstallmentPlan.query.filter_by(sale_id=sale_id).first()
    payments = InstallmentPayment.query.filter_by(plan_id=plan.id).order_by(InstallmentPayment.payment_date.desc()).all() if plan else []
    
    return render_template('sales/manage_installments.html', sale=sale, plan=plan, payments=payments)

@app.route('/add_installment_payment', methods=['POST'])
@login_required
def add_installment_payment():
    """Record an installment payment"""
    try:
        from models import InstallmentPlan, InstallmentPayment
        
        plan_id = request.form.get('plan_id')
        amount = Decimal(request.form.get('amount'))
        payment_method = request.form.get('payment_method', 'cash')
        notes = request.form.get('notes', '')
        
        plan = InstallmentPlan.query.get_or_404(plan_id)
        
        # Verify user owns this plan
        if plan.sale.user_id != current_user.id:
            flash('Unauthorized access.', 'danger')
            return redirect(url_for('sales'))
        
        # Create payment record
        payment = InstallmentPayment(
            plan_id=plan_id,
            amount=amount,
            payment_method=payment_method,
            notes=notes,
            payment_date=datetime.utcnow().date()
        )
        db.session.add(payment)
        
        # Update plan totals
        plan.paid_amount += amount
        plan.outstanding_amount = plan.remaining_amount - plan.paid_amount
        
        # Update sale payment status
        if plan.outstanding_amount <= 0:
            plan.status = 'completed'
            plan.sale.payment_status = 'paid'
        elif plan.paid_amount > 0:
            plan.sale.payment_status = 'partial'
        
        db.session.commit()
        flash(f'Payment of ${amount:.2f} recorded successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error recording payment: {str(e)}', 'danger')
    
    return redirect(url_for('manage_installments', sale_id=plan.sale_id))

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
        
        # Create default location for the admin user
        default_location = Location(
            name='Main Store',
            address='Main Office',
            location_type='store',
            user_id=admin.id
        )
        db.session.add(default_location)
        db.session.commit()
        
        logging.info("Default admin user, categories, and location created")

# Location Management Routes
@app.route('/locations')
@login_required
def locations():
    user_locations = Location.query.filter_by(user_id=current_user.id, is_active=True).order_by(Location.name).all()
    return render_template('locations.html', locations=user_locations)

@app.route('/add_location', methods=['POST'])
@login_required
def add_location():
    try:
        location = Location(
            name=request.form['name'],
            address=request.form.get('address', ''),
            phone=request.form.get('phone', ''),
            email=request.form.get('email', ''),
            manager_name=request.form.get('manager_name', ''),
            location_type=request.form.get('location_type', 'store'),
            user_id=current_user.id
        )
        
        db.session.add(location)
        db.session.commit()
        
        flash(f'Location "{location.name}" has been created successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating location: {str(e)}', 'danger')
    
    return redirect(url_for('locations'))

@app.route('/edit_location/<int:location_id>', methods=['GET', 'POST'])
@login_required
def edit_location(location_id):
    location = Location.query.filter_by(id=location_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        try:
            location.name = request.form['name']
            location.address = request.form.get('address', '')
            location.phone = request.form.get('phone', '')
            location.email = request.form.get('email', '')
            location.manager_name = request.form.get('manager_name', '')
            location.location_type = request.form.get('location_type', 'store')
            
            db.session.commit()
            flash(f'Location "{location.name}" has been updated successfully!', 'success')
            return redirect(url_for('locations'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating location: {str(e)}', 'danger')
    
    return render_template('edit_location.html', location=location)

@app.route('/location_stock/<int:location_id>')
@login_required
def location_stock(location_id):
    location = Location.query.filter_by(id=location_id, user_id=current_user.id).first_or_404()
    
    # Get all items with their stock at this location
    items_query = db.session.query(Item, LocationStock).outerjoin(
        LocationStock, and_(Item.id == LocationStock.item_id, LocationStock.location_id == location_id)
    ).filter(Item.is_active == True).order_by(Item.name)
    
    items_stock = items_query.all()
    
    return render_template('location_stock.html', location=location, items_stock=items_stock)

@app.route('/update_location_stock', methods=['POST'])
@login_required
def update_location_stock():
    try:
        location_id = int(request.form['location_id'])
        item_id = int(request.form['item_id'])
        quantity = int(request.form['quantity'])
        minimum_stock = int(request.form.get('minimum_stock', 0))
        
        # Verify location belongs to current user
        location = Location.query.filter_by(id=location_id, user_id=current_user.id).first_or_404()
        
        # Check if location stock entry exists
        location_stock = LocationStock.query.filter_by(item_id=item_id, location_id=location_id).first()
        
        if location_stock:
            old_quantity = location_stock.quantity
            location_stock.quantity = quantity
            location_stock.min_stock_level = minimum_stock
            location_stock.last_updated = datetime.utcnow()
        else:
            location_stock = LocationStock(
                item_id=item_id,
                location_id=location_id,
                quantity=quantity,
                min_stock_level=minimum_stock,
                reserved_quantity=0,
                max_stock_level=quantity * 2,
                last_updated=datetime.utcnow()
            )
            db.session.add(location_stock)
            old_quantity = 0
        
        # Create stock movement record
        movement_type = 'in' if quantity > old_quantity else 'out' if quantity < old_quantity else 'adjustment'
        if quantity != old_quantity:
            stock_movement = StockMovement(
                movement_type=movement_type,
                quantity=abs(quantity - old_quantity),
                reason=f'Location stock update at {location.name}',
                item_id=item_id
            )
            db.session.add(stock_movement)
        
        db.session.commit()
        flash('Stock updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating stock: {str(e)}', 'danger')
    
    return redirect(url_for('location_stock', location_id=location_id))

@app.route('/stock_transfers')
@login_required
def stock_transfers():
    # Get transfers where user owns both locations
    user_location_ids = [loc.id for loc in Location.query.filter_by(user_id=current_user.id).all()]
    
    transfers = StockTransfer.query.filter(
        or_(StockTransfer.from_location_id.in_(user_location_ids),
            StockTransfer.to_location_id.in_(user_location_ids))
    ).order_by(desc(StockTransfer.created_at)).all()
    
    return render_template('stock_transfers.html', transfers=transfers)

@app.route('/create_transfer', methods=['GET', 'POST'])
@login_required
def create_transfer():
    if request.method == 'POST':
        try:
            from_location_id = int(request.form['from_location_id'])
            to_location_id = int(request.form['to_location_id'])
            
            if from_location_id == to_location_id:
                flash('Source and destination locations cannot be the same.', 'danger')
                return redirect(url_for('create_transfer'))
            
            # Verify both locations belong to current user
            from_location = Location.query.filter_by(id=from_location_id, user_id=current_user.id).first_or_404()
            to_location = Location.query.filter_by(id=to_location_id, user_id=current_user.id).first_or_404()
            
            transfer_number = f"TRF-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            transfer = StockTransfer(
                transfer_number=transfer_number,
                from_location_id=from_location_id,
                to_location_id=to_location_id,
                notes=request.form.get('notes', ''),
                initiated_by=current_user.id
            )
            
            db.session.add(transfer)
            db.session.flush()  # Get the transfer ID
            
            # Add transfer items
            item_ids = request.form.getlist('item_id[]')
            quantities = request.form.getlist('quantity[]')
            
            for item_id, quantity in zip(item_ids, quantities):
                if item_id and quantity and int(quantity) > 0:
                    # Check if enough stock available at source location
                    source_stock = LocationStock.query.filter_by(
                        item_id=int(item_id), 
                        location_id=from_location_id
                    ).first()
                    
                    if not source_stock or source_stock.quantity < int(quantity):
                        raise Exception(f"Insufficient stock for item ID {item_id} at {from_location.name}")
                    
                    transfer_item = StockTransferItem(
                        transfer_id=transfer.id,
                        item_id=int(item_id),
                        quantity=int(quantity)
                    )
                    db.session.add(transfer_item)
            
            db.session.commit()
            flash(f'Stock transfer {transfer_number} created successfully!', 'success')
            return redirect(url_for('stock_transfers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating transfer: {str(e)}', 'danger')
    
    # GET request - show form
    user_locations = Location.query.filter_by(user_id=current_user.id, is_active=True).all()
    items = Item.query.filter_by(is_active=True).order_by(Item.name).all()
    
    return render_template('create_transfer.html', locations=user_locations, items=items)

@app.route('/complete_transfer/<int:transfer_id>', methods=['POST'])
@login_required
def complete_transfer(transfer_id):
    try:
        transfer = StockTransfer.query.get_or_404(transfer_id)
        
        # Verify user has access to this transfer
        if (transfer.from_location.user_id != current_user.id or 
            transfer.to_location.user_id != current_user.id):
            flash('Access denied.', 'danger')
            return redirect(url_for('stock_transfers'))
        
        if transfer.status != 'pending':
            flash('Transfer has already been processed.', 'warning')
            return redirect(url_for('stock_transfers'))
        
        # Process each item in the transfer
        for transfer_item in transfer.transfer_items:
            # Reduce stock at source location
            source_stock = LocationStock.query.filter_by(
                item_id=transfer_item.item_id,
                location_id=transfer.from_location_id
            ).first()
            
            if source_stock:
                source_stock.quantity -= transfer_item.quantity
            
            # Increase stock at destination location
            dest_stock = LocationStock.query.filter_by(
                item_id=transfer_item.item_id,
                location_id=transfer.to_location_id
            ).first()
            
            if dest_stock:
                dest_stock.quantity += transfer_item.quantity
            else:
                dest_stock = LocationStock(
                    item_id=transfer_item.item_id,
                    location_id=transfer.to_location_id,
                    quantity=transfer_item.quantity,
                    minimum_stock=0
                )
                db.session.add(dest_stock)
            
            # Create stock movement records
            out_movement = StockMovement(
                movement_type='out',
                quantity=transfer_item.quantity,
                reason=f'Transfer {transfer.transfer_number} to {transfer.to_location.name}',
                item_id=transfer_item.item_id
            )
            
            in_movement = StockMovement(
                movement_type='in',
                quantity=transfer_item.quantity,
                reason=f'Transfer {transfer.transfer_number} from {transfer.from_location.name}',
                item_id=transfer_item.item_id
            )
            
            db.session.add(out_movement)
            db.session.add(in_movement)
        
        # Update transfer status
        transfer.status = 'completed'
        transfer.completed_at = datetime.utcnow()
        
        db.session.commit()
        flash(f'Transfer {transfer.transfer_number} completed successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error completing transfer: {str(e)}', 'danger')
    
    return redirect(url_for('stock_transfers'))

# Financial Management Routes
@app.route('/accounting')
@login_required
def accounting_dashboard():
    """Accounting dashboard with financial overview"""
    from enhanced_financial_service import FinancialService
    
    financial_service = FinancialService(current_user.id)
    
    # Get recent journals
    recent_journals = Journal.query.filter_by(user_id=current_user.id).order_by(desc(Journal.created_at)).limit(10).all()
    
    # Get account summary
    accounts = ChartOfAccounts.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    # Calculate current period P&L (this month)
    start_date = datetime.now().replace(day=1)
    end_date = datetime.now()
    pl_data = financial_service.calculate_profit_loss(start_date, end_date)
    
    return render_template('accounting/dashboard.html', 
                         recent_journals=recent_journals,
                         accounts=accounts,
                         pl_data=pl_data)

@app.route('/accounting/chart-of-accounts')
@login_required
def chart_of_accounts():
    """Chart of accounts management"""
    accounts = ChartOfAccounts.query.filter_by(user_id=current_user.id).order_by(ChartOfAccounts.account_code).all()
    
    # Group by account type
    grouped_accounts = {}
    for account in accounts:
        if account.account_type not in grouped_accounts:
            grouped_accounts[account.account_type] = []
        grouped_accounts[account.account_type].append(account)
    
    return render_template('accounting/chart_of_accounts.html', grouped_accounts=grouped_accounts)

@app.route('/accounting/initialize-accounts', methods=['POST'])
@login_required
def initialize_chart_of_accounts():
    """Initialize default chart of accounts for user"""
    from enhanced_financial_service import FinancialService
    
    financial_service = FinancialService(current_user.id)
    
    if financial_service.initialize_chart_of_accounts():
        flash('Chart of accounts initialized successfully!', 'success')
    else:
        flash('Error initializing chart of accounts', 'danger')
    
    return redirect(url_for('chart_of_accounts'))

@app.route('/accounting/journal-entries')
@login_required
def journal_entries():
    """View journal entries"""
    page = request.args.get('page', 1, type=int)
    journals = Journal.query.filter_by(user_id=current_user.id).order_by(desc(Journal.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('accounting/journal_entries.html', journals=journals)

@app.route('/accounting/journal-entry/<int:journal_id>')
@login_required
def view_journal_entry(journal_id):
    """View specific journal entry details"""
    journal = Journal.query.filter_by(id=journal_id, user_id=current_user.id).first_or_404()
    return render_template('accounting/journal_entry_detail.html', journal=journal)

@app.route('/accounting/reports/profit-loss')
@login_required
def profit_loss_report():
    """Profit and Loss report"""
    from enhanced_financial_service import FinancialService
    
    # Get date parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    else:
        # Default to current month
        start_date = datetime.now().replace(day=1)
        end_date = datetime.now()
    
    financial_service = FinancialService(current_user.id)
    pl_data = financial_service.calculate_profit_loss(start_date, end_date)
    
    return render_template('accounting/profit_loss.html', 
                         pl_data=pl_data,
                         start_date=start_date,
                         end_date=end_date)

@app.route('/accounting/reports/balance-sheet')
@login_required
def balance_sheet_report():
    """Balance sheet report"""
    from enhanced_financial_service import FinancialService
    
    # Get date parameter
    as_of_date_str = request.args.get('as_of_date')
    
    if as_of_date_str:
        as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d')
    else:
        as_of_date = datetime.now()
    
    financial_service = FinancialService(current_user.id)
    balance_sheet_data = financial_service.generate_balance_sheet(as_of_date)
    
    return render_template('accounting/balance_sheet.html', 
                         balance_sheet_data=balance_sheet_data,
                         as_of_date=as_of_date)

@app.route('/accounting/reports/trial-balance')
@login_required
def trial_balance_report():
    """Trial balance report"""
    from enhanced_financial_service import FinancialService
    
    # Get date parameter
    as_of_date_str = request.args.get('as_of_date')
    
    if as_of_date_str:
        as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d')
    else:
        as_of_date = datetime.now()
    
    financial_service = FinancialService(current_user.id)
    trial_balance_data = financial_service.generate_trial_balance(as_of_date)
    
    return render_template('accounting/trial_balance.html', 
                         trial_balance_data=trial_balance_data,
                         as_of_date=as_of_date)

@app.route('/accounting/bank-accounts')
@login_required
def bank_accounts():
    """Bank accounts management"""
    accounts = BankAccount.query.filter_by(user_id=current_user.id).all()
    return render_template('accounting/bank_accounts.html', accounts=accounts)

@app.route('/accounting/bank-account/add', methods=['GET', 'POST'])
@login_required
def add_bank_account():
    """Add new bank account"""
    if request.method == 'POST':
        try:
            account = BankAccount(
                account_name=request.form['account_name'],
                account_number=request.form.get('account_number', ''),
                bank_name=request.form.get('bank_name', ''),
                account_type=request.form['account_type'],
                current_balance=float(request.form.get('current_balance', 0)),
                user_id=current_user.id
            )
            
            db.session.add(account)
            db.session.commit()
            
            flash('Bank account added successfully!', 'success')
            return redirect(url_for('bank_accounts'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding bank account: {str(e)}', 'danger')
    
    return render_template('accounting/add_bank_account.html')

# Customer Management Routes
@app.route('/customers')
@login_required
def customers():
    """Display all customers for the current user"""
    customers = Customer.query.filter_by(user_id=current_user.id).order_by(Customer.name).all()
    return render_template('customers/list.html', customers=customers)

@app.route('/customers/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    """Add a new customer"""
    if request.method == 'POST':
        try:
            customer = Customer(
                name=request.form['name'],
                email=request.form.get('email') or None,
                phone=request.form.get('phone') or None,
                address=request.form.get('address') or None,
                customer_type=request.form.get('customer_type', 'retail'),
                credit_limit=float(request.form.get('credit_limit', 0)),
                preferred_payment_method=request.form.get('preferred_payment_method'),
                user_id=current_user.id
            )
            
            db.session.add(customer)
            db.session.commit()
            
            flash('Customer added successfully!', 'success')
            return redirect(url_for('customers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding customer: {str(e)}', 'danger')
    
    return render_template('customers/add.html')

@app.route('/customers/<int:customer_id>')
@login_required
def customer_profile(customer_id):
    """Display customer profile and purchase history"""
    customer = Customer.query.filter_by(id=customer_id, user_id=current_user.id).first_or_404()
    
    # Get purchase history
    purchases = Sale.query.filter_by(customer_id=customer_id, user_id=current_user.id).order_by(Sale.created_at.desc()).limit(10).all()
    
    # Calculate metrics using the provided function
    from customer_management import calculate_customer_metrics
    metrics = calculate_customer_metrics(db, customer_id)
    
    return render_template('customers/profile.html', customer=customer, purchases=purchases, metrics=metrics)

@app.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    """Edit customer information"""
    customer = Customer.query.filter_by(id=customer_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        try:
            customer.name = request.form['name']
            customer.email = request.form.get('email') or None
            customer.phone = request.form.get('phone') or None
            customer.address = request.form.get('address') or None
            customer.customer_type = request.form.get('customer_type', 'retail')
            customer.credit_limit = float(request.form.get('credit_limit', 0))
            customer.preferred_payment_method = request.form.get('preferred_payment_method')
            customer.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Customer updated successfully!', 'success')
            return redirect(url_for('customer_profile', customer_id=customer_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating customer: {str(e)}', 'danger')
    
    return render_template('customers/edit.html', customer=customer)

# Smart Automation Routes
@app.route('/automation')
@login_required
def automation_dashboard():
    """Smart automation dashboard"""
    from smart_automation import SmartAutomationEngine
    
    try:
        engine = SmartAutomationEngine(current_user.id)
        
        # Get current analysis
        patterns = engine.analyze_inventory_patterns()
        purchase_orders = engine.generate_auto_purchase_orders()
        notifications = engine.generate_smart_notifications()
        
        # Calculate summary metrics
        total_items_analyzed = len(patterns)
        high_priority_orders = len([po for po in purchase_orders if po.urgency_level in ['high', 'critical']])
        critical_notifications = len([n for n in notifications if n.priority in ['high', 'critical']])
        
        automation_summary = {
            'total_items_analyzed': total_items_analyzed,
            'purchase_orders_needed': len(purchase_orders),
            'high_priority_orders': high_priority_orders,
            'notifications_count': len(notifications),
            'critical_notifications': critical_notifications,
            'last_analysis': datetime.utcnow()
        }
        
        return render_template('automation/dashboard.html', 
                             patterns=patterns,
                             purchase_orders=purchase_orders,
                             notifications=notifications,
                             summary=automation_summary)
                             
    except Exception as e:
        flash(f'Error loading automation dashboard: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/automation/purchase-orders')
@login_required
def automation_purchase_orders():
    """View and manage auto-generated purchase orders"""
    from smart_automation import SmartAutomationEngine
    
    try:
        engine = SmartAutomationEngine(current_user.id)
        purchase_orders = engine.generate_auto_purchase_orders()
        
        # Group by urgency
        orders_by_urgency = {
            'critical': [po for po in purchase_orders if po.urgency_level == 'critical'],
            'high': [po for po in purchase_orders if po.urgency_level == 'high'],
            'medium': [po for po in purchase_orders if po.urgency_level == 'medium'],
            'low': [po for po in purchase_orders if po.urgency_level == 'low']
        }
        
        return render_template('automation/purchase_orders.html', 
                             orders_by_urgency=orders_by_urgency,
                             total_orders=len(purchase_orders))
                             
    except Exception as e:
        flash(f'Error loading purchase orders: {str(e)}', 'danger')
        return redirect(url_for('automation_dashboard'))

@app.route('/automation/notifications')
@login_required
def automation_notifications():
    """View smart notifications"""
    from smart_automation import SmartAutomationEngine
    
    try:
        engine = SmartAutomationEngine(current_user.id)
        notifications = engine.generate_smart_notifications()
        
        # Group by type
        notifications_by_type = {}
        for notification in notifications:
            notif_type = notification.notification_type
            if notif_type not in notifications_by_type:
                notifications_by_type[notif_type] = []
            notifications_by_type[notif_type].append(notification)
        
        return render_template('automation/notifications.html', 
                             notifications=notifications,
                             notifications_by_type=notifications_by_type)
                             
    except Exception as e:
        flash(f'Error loading notifications: {str(e)}', 'danger')
        return redirect(url_for('automation_dashboard'))

@app.route('/automation/run-analysis', methods=['POST'])
@login_required
def run_automation_analysis():
    """Manually trigger automation analysis"""
    from smart_automation import run_automation_for_user
    
    try:
        results = run_automation_for_user(current_user.id)
        
        flash(f'Automation analysis completed: {results["patterns_analyzed"]} items analyzed, '
              f'{len(results["purchase_orders"])} purchase orders generated, '
              f'{len(results["notifications"])} notifications created', 'success')
              
    except Exception as e:
        flash(f'Error running automation analysis: {str(e)}', 'danger')
    
    return redirect(url_for('automation_dashboard'))

# Call the function to create default data
with app.app_context():
    create_default_data()

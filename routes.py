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
                    Customer, CustomerPurchaseHistory, LoyaltyTransaction, OnDemandProduct, OnDemandOrder)
from auth_service import authenticate_user, create_or_update_user, validate_email_format, validate_password_strength

def calculate_financial_metrics(user_id, date_filter=None, period='all'):
    """Calculate comprehensive financial metrics including gross profit"""
    
    # Base queries filtered by user and date
    sales_query = Sale.query.filter_by(user_id=user_id)
    transactions_query = FinancialTransaction.query.filter_by(user_id=user_id)
    
    if date_filter:
        if period == 'today':
            sales_query = sales_query.filter(func.date(Sale.created_at) == date_filter)
            transactions_query = transactions_query.filter(func.date(FinancialTransaction.created_at) == date_filter)
        else:
            sales_query = sales_query.filter(func.date(Sale.created_at) >= date_filter)
            transactions_query = transactions_query.filter(func.date(FinancialTransaction.created_at) >= date_filter)
    
    # Sales and Revenue Calculations
    total_sales_count = sales_query.count()
    total_revenue = sales_query.with_entities(func.sum(Sale.total_amount)).scalar() or 0
    
    # Calculate Cost of Goods Sold (COGS) from sales
    cogs_subquery = db.session.query(
        func.sum(SaleItem.quantity * SaleItem.unit_cost).label('total_cogs')
    ).join(Sale).filter(Sale.user_id == user_id)
    
    if date_filter:
        if period == 'today':
            cogs_subquery = cogs_subquery.filter(func.date(Sale.created_at) == date_filter)
        else:
            cogs_subquery = cogs_subquery.filter(func.date(Sale.created_at) >= date_filter)
    
    total_cogs = cogs_subquery.scalar() or 0
    
    # Gross Profit Calculations
    gross_profit = total_revenue - total_cogs
    gross_profit_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    # Operating Expenses
    total_expenses = transactions_query.filter_by(transaction_type='expense').with_entities(
        func.sum(FinancialTransaction.amount)
    ).scalar() or 0
    
    # Other Income
    other_income = transactions_query.filter_by(transaction_type='income').with_entities(
        func.sum(FinancialTransaction.amount)
    ).scalar() or 0
    
    # Net Profit Calculations
    net_profit = gross_profit + other_income - total_expenses
    net_profit_margin = (net_profit / (total_revenue + other_income) * 100) if (total_revenue + other_income) > 0 else 0
    
    # Average Transaction Value
    avg_transaction_value = (total_revenue / total_sales_count) if total_sales_count > 0 else 0
    
    # Inventory Value (Current Stock Value)
    inventory_value = db.session.query(
        func.sum(Item.stock_quantity * Item.buying_price)
    ).filter_by(user_id=user_id, is_active=True).scalar() or 0
    
    # Inventory Turnover (COGS / Average Inventory Value)
    inventory_turnover = (total_cogs / inventory_value) if inventory_value > 0 else 0
    
    # Tax calculations
    total_tax_collected = sales_query.with_entities(func.sum(Sale.tax_amount)).scalar() or 0
    
    # Payment method breakdown
    payment_methods = db.session.query(
        Sale.payment_method,
        func.count(Sale.id).label('count'),
        func.sum(Sale.total_amount).label('total')
    ).filter_by(user_id=user_id)
    
    if date_filter:
        if period == 'today':
            payment_methods = payment_methods.filter(func.date(Sale.created_at) == date_filter)
        else:
            payment_methods = payment_methods.filter(func.date(Sale.created_at) >= date_filter)
    
    payment_breakdown = payment_methods.group_by(Sale.payment_method).all()
    
    # Top selling items
    top_items = db.session.query(
        Item.name,
        func.sum(SaleItem.quantity).label('total_sold'),
        func.sum(SaleItem.quantity * SaleItem.unit_price).label('total_revenue'),
        func.sum(SaleItem.quantity * (SaleItem.unit_price - SaleItem.unit_cost)).label('total_profit')
    ).join(SaleItem).join(Sale).filter(Sale.user_id == user_id)
    
    if date_filter:
        if period == 'today':
            top_items = top_items.filter(func.date(Sale.created_at) == date_filter)
        else:
            top_items = top_items.filter(func.date(Sale.created_at) >= date_filter)
    
    top_items = top_items.group_by(Item.id, Item.name).order_by(desc('total_sold')).limit(5).all()
    
    return {
        'total_sales_count': total_sales_count,
        'total_revenue': float(total_revenue),
        'total_cogs': float(total_cogs),
        'gross_profit': float(gross_profit),
        'gross_profit_margin': float(gross_profit_margin),
        'total_expenses': float(total_expenses),
        'other_income': float(other_income),
        'net_profit': float(net_profit),
        'net_profit_margin': float(net_profit_margin),
        'avg_transaction_value': float(avg_transaction_value),
        'inventory_value': float(inventory_value),
        'inventory_turnover': float(inventory_turnover),
        'total_tax_collected': float(total_tax_collected),
        'payment_breakdown': payment_breakdown,
        'top_items': top_items,
        'period': period
    }

# Register authentication blueprint
from auth import auth_bp
app.register_blueprint(auth_bp)

# Import language routes
from language_routes import language_bp
app.register_blueprint(language_bp)

# Import admin routes
from admin_routes import admin_bp
app.register_blueprint(admin_bp)

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# Login route handled by auth blueprint

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
                buying_price=Decimal(request.form['buying_price']),
                wholesale_price=Decimal(request.form['wholesale_price']),
                retail_price=Decimal(request.form['retail_price']),
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
            item.buying_price = Decimal(request.form['buying_price'])
            item.wholesale_price = Decimal(request.form['wholesale_price'])
            item.retail_price = Decimal(request.form['retail_price'])
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
    items = Item.query.filter_by(is_active=True).filter(Item.stock_quantity > 0).order_by(Item.name).all()
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
        customer_type = request.form.get('customer_type', 'walk_in')
        customer_id = request.form.get('customer_id') or None
        notes = request.form.get('notes', '')
        
        # Handle new customer creation
        if customer_type == 'new':
            new_customer_name = request.form.get('new_customer_name', '').strip()
            if not new_customer_name:
                flash('Customer name is required for new customers!', 'danger')
                return redirect(url_for('new_sale'))
            
            # Create new customer
            new_customer = Customer(
                name=new_customer_name,
                email=request.form.get('new_customer_email', '').strip() or None,
                phone=request.form.get('new_customer_phone', '').strip() or None,
                address=request.form.get('new_customer_address', '').strip() or None,
                user_id=current_user.id
            )
            db.session.add(new_customer)
            db.session.flush()  # Get the new customer ID
            customer_id = new_customer.id
            flash(f'New customer "{new_customer_name}" added successfully!', 'success')
        
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
        sold_item_ids = []
        for cart_item in cart_items:
            item = Item.query.get(cart_item['id'])
            if not item or item.stock_quantity < cart_item['quantity']:
                raise Exception(f"Insufficient stock for {item.name if item else 'unknown item'}")
            
            # Create sale item with cost tracking
            unit_price = Decimal(str(cart_item['price']))
            unit_cost = item.buying_price  # Use buying price as cost
            quantity = cart_item['quantity']
            total_price = unit_price * quantity
            
            sale_item = SaleItem(
                quantity=quantity,
                unit_price=unit_price,
                unit_cost=unit_cost,
                total_price=total_price,
                sale_id=sale.id,
                item_id=item.id
            )
            db.session.add(sale_item)
            
            # Update stock
            item.stock_quantity -= quantity
            sold_item_ids.append(item.id)
            
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
        
        # Send sale notifications
        try:
            from sms_service import sms_service
            
            # Send SMS notification to business owner
            customer_name = None
            if customer_id:
                customer = Customer.query.get(customer_id)
                customer_name = customer.name if customer else None
            
            sms_service.send_sale_notification(current_user, sale.id, float(total_amount), customer_name)
            
            # Send order confirmation SMS to customer if they have a phone number
            if customer_id and customer and customer.phone:
                sms_service.send_order_confirmation(
                    customer.phone, 
                    customer.name, 
                    sale.id, 
                    float(total_amount), 
                    current_user.shop_name
                )
                
        except Exception as e:
            logging.error(f"Error sending sale SMS notifications: {str(e)}")
        
        # Check for low stock alerts after successful sale
        try:
            from notification_service import NotificationService
            NotificationService.check_stock_after_sale(current_user.id, sold_item_ids)
        except Exception as e:
            logging.error(f"Error checking post-sale notifications: {str(e)}")
        
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
    period = request.args.get('period', 'all')  # all, today, week, month, year
    
    # Date filtering
    date_filter = None
    if period == 'today':
        date_filter = datetime.utcnow().date()
    elif period == 'week':
        date_filter = datetime.utcnow().date() - timedelta(days=7)
    elif period == 'month':
        date_filter = datetime.utcnow().date() - timedelta(days=30)
    elif period == 'year':
        date_filter = datetime.utcnow().date() - timedelta(days=365)
    
    # Build query
    query = FinancialTransaction.query.filter_by(user_id=current_user.id)
    if transaction_type:
        query = query.filter_by(transaction_type=transaction_type)
    if date_filter:
        if period == 'today':
            query = query.filter(func.date(FinancialTransaction.created_at) == date_filter)
        else:
            query = query.filter(func.date(FinancialTransaction.created_at) >= date_filter)
    
    transactions = query.order_by(desc(FinancialTransaction.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Calculate comprehensive financial metrics
    financial_metrics = calculate_financial_metrics(current_user.id, date_filter, period)
    
    return render_template('financial.html', 
                         transactions=transactions,
                         metrics=financial_metrics,
                         selected_type=transaction_type,
                         selected_period=period)

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
        
        # No default categories - users will create their own
        
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

# On-Demand Products Routes
@app.route('/on-demand-products')
@login_required
def on_demand_products():
    """Display on-demand products management"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category_id = request.args.get('category_id', type=int)
    
    # Build query
    query = OnDemandProduct.query.filter_by(user_id=current_user.id, is_active=True)
    
    if search:
        query = query.filter(OnDemandProduct.name.contains(search))
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    products = query.order_by(OnDemandProduct.name).paginate(
        page=page, per_page=20, error_out=False
    )
    
    categories = Category.query.order_by(Category.name).all()
    
    return render_template('on_demand/products.html', 
                         products=products, 
                         categories=categories,
                         search=search,
                         category_id=category_id)

@app.route('/on-demand-products/add', methods=['GET', 'POST'])
@login_required
def add_on_demand_product():
    """Add a new on-demand product"""
    if request.method == 'POST':
        try:
            product = OnDemandProduct(
                name=request.form['name'],
                description=request.form.get('description'),
                category_id=int(request.form['category_id']) if request.form.get('category_id') else None,
                estimated_cost=float(request.form['estimated_cost']),
                selling_price=float(request.form['selling_price']),
                supplier_name=request.form.get('supplier_name'),
                supplier_contact=request.form.get('supplier_contact'),
                estimated_delivery_days=int(request.form.get('estimated_delivery_days', 7)),
                minimum_order_quantity=int(request.form.get('minimum_order_quantity', 1)),
                user_id=current_user.id
            )
            
            db.session.add(product)
            db.session.commit()
            
            flash('On-demand product added successfully!', 'success')
            return redirect(url_for('on_demand_products'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding product: {str(e)}', 'danger')
    
    categories = Category.query.order_by(Category.name).all()
    return render_template('on_demand/add_product.html', categories=categories)

@app.route('/on-demand-products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_on_demand_product(product_id):
    """Edit an on-demand product"""
    product = OnDemandProduct.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        try:
            product.name = request.form['name']
            product.description = request.form.get('description')
            product.category_id = int(request.form['category_id']) if request.form.get('category_id') else None
            product.estimated_cost = float(request.form['estimated_cost'])
            product.selling_price = float(request.form['selling_price'])
            product.supplier_name = request.form.get('supplier_name')
            product.supplier_contact = request.form.get('supplier_contact')
            product.estimated_delivery_days = int(request.form.get('estimated_delivery_days', 7))
            product.minimum_order_quantity = int(request.form.get('minimum_order_quantity', 1))
            product.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('Product updated successfully!', 'success')
            return redirect(url_for('on_demand_products'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'danger')
    
    categories = Category.query.order_by(Category.name).all()
    return render_template('on_demand/edit_product.html', product=product, categories=categories)

@app.route('/on-demand-orders')
@login_required
def on_demand_orders():
    """Display on-demand orders"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = OnDemandOrder.query.filter_by(user_id=current_user.id)
    
    if status:
        query = query.filter_by(status=status)
    
    orders = query.order_by(OnDemandOrder.order_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('on_demand/orders.html', orders=orders, status=status)

@app.route('/on-demand-orders/create/<int:product_id>', methods=['GET', 'POST'])
@login_required
def create_on_demand_order(product_id):
    """Create an order for an on-demand product"""
    product = OnDemandProduct.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        try:
            quantity = int(request.form['quantity'])
            unit_price = float(request.form['unit_price'])
            total_amount = quantity * unit_price
            advance_payment = float(request.form.get('advance_payment', 0))
            
            order_number = f"OD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # Calculate expected delivery date
            expected_delivery = datetime.utcnow().date() + timedelta(days=product.estimated_delivery_days)
            
            order = OnDemandOrder(
                order_number=order_number,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                total_amount=total_amount,
                customer_id=int(request.form['customer_id']) if request.form.get('customer_id') else None,
                customer_name=request.form.get('customer_name'),
                customer_phone=request.form.get('customer_phone'),
                customer_email=request.form.get('customer_email'),
                payment_method=request.form.get('payment_method'),
                expected_delivery_date=expected_delivery,
                notes=request.form.get('notes'),
                advance_payment=advance_payment,
                remaining_payment=total_amount - advance_payment,
                user_id=current_user.id
            )
            
            # Set payment status
            if advance_payment >= total_amount:
                order.payment_status = 'paid'
            elif advance_payment > 0:
                order.payment_status = 'partial'
            else:
                order.payment_status = 'pending'
            
            db.session.add(order)
            db.session.commit()
            
            flash(f'Order {order_number} created successfully!', 'success')
            return redirect(url_for('on_demand_orders'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating order: {str(e)}', 'danger')
    
    customers = Customer.query.filter_by(user_id=current_user.id).order_by(Customer.name).all()
    return render_template('on_demand/create_order.html', product=product, customers=customers)

@app.route('/on-demand-orders/<int:order_id>/update-status', methods=['POST'])
@login_required
def update_order_status(order_id):
    """Update order status"""
    order = OnDemandOrder.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    
    try:
        new_status = request.form['status']
        order.status = new_status
        
        if new_status == 'delivered':
            order.actual_delivery_date = datetime.utcnow().date()
        
        db.session.commit()
        flash('Order status updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating status: {str(e)}', 'danger')
    
    return redirect(url_for('on_demand_orders'))

@app.route('/profit-margin-analysis')
@login_required
def profit_margin_analysis():
    """Comprehensive profit margin analysis dashboard"""
    
    # Get filter parameters
    category_id = request.args.get('category_id', type=int)
    date_range = request.args.get('date_range', '30')  # days
    sort_by = request.args.get('sort_by', 'profit_margin')
    
    # Calculate date range
    end_date = datetime.utcnow()
    if date_range == '7':
        start_date = end_date - timedelta(days=7)
    elif date_range == '30':
        start_date = end_date - timedelta(days=30)
    elif date_range == '90':
        start_date = end_date - timedelta(days=90)
    elif date_range == '365':
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)
    
    # Get inventory items with profit calculations
    query = Item.query.filter_by(user_id=current_user.id, is_active=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    items = query.all()
    
    # Calculate profit metrics for each item
    profit_analysis = []
    total_inventory_value = 0
    total_potential_profit = 0
    total_sold_profit = 0
    total_expenses = 0
    
    for item in items:
        # Basic profit calculations
        buying_price = float(item.buying_price or 0)
        wholesale_price = float(item.wholesale_price or 0)
        retail_price = float(item.retail_price or 0)
        current_stock = item.stock_quantity
        
        # Calculate margins
        wholesale_margin = ((wholesale_price - buying_price) / buying_price * 100) if buying_price > 0 else 0
        retail_margin = ((retail_price - buying_price) / buying_price * 100) if buying_price > 0 else 0
        
        # Get sales data for this period
        sales_query = db.session.query(SaleItem).join(Sale).filter(
            SaleItem.item_id == item.id,
            Sale.user_id == current_user.id,
            Sale.created_at >= start_date,
            Sale.created_at <= end_date
        )
        
        sales_data = sales_query.all()
        units_sold = sum(sale_item.quantity for sale_item in sales_data)
        revenue = sum(float(sale_item.total_price) for sale_item in sales_data)
        cost_of_goods_sold = units_sold * buying_price
        actual_profit = revenue - cost_of_goods_sold
        
        # Calculate inventory metrics
        inventory_value = current_stock * buying_price
        potential_retail_profit = current_stock * (retail_price - buying_price)
        potential_wholesale_profit = current_stock * (wholesale_price - buying_price)
        
        # Turnover rate
        turnover_rate = (units_sold / current_stock * 100) if current_stock > 0 else 0
        
        profit_analysis.append({
            'item': item,
            'buying_price': buying_price,
            'wholesale_price': wholesale_price,
            'retail_price': retail_price,
            'wholesale_margin': wholesale_margin,
            'retail_margin': retail_margin,
            'current_stock': current_stock,
            'units_sold': units_sold,
            'revenue': revenue,
            'cost_of_goods_sold': cost_of_goods_sold,
            'actual_profit': actual_profit,
            'inventory_value': inventory_value,
            'potential_retail_profit': potential_retail_profit,
            'potential_wholesale_profit': potential_wholesale_profit,
            'turnover_rate': turnover_rate,
            'profit_per_unit_retail': retail_price - buying_price,
            'profit_per_unit_wholesale': wholesale_price - buying_price
        })
        
        total_inventory_value += inventory_value
        total_potential_profit += potential_retail_profit
        total_sold_profit += actual_profit
    
    # Get expenses for the period
    expenses_query = FinancialTransaction.query.filter_by(
        user_id=current_user.id,
        transaction_type='expense'
    ).filter(
        FinancialTransaction.created_at >= start_date,
        FinancialTransaction.created_at <= end_date
    )
    
    expenses = expenses_query.all()
    total_expenses = sum(float(expense.amount) for expense in expenses)
    
    # Sort analysis based on user preference
    if sort_by == 'profit_margin':
        profit_analysis.sort(key=lambda x: x['retail_margin'], reverse=True)
    elif sort_by == 'actual_profit':
        profit_analysis.sort(key=lambda x: x['actual_profit'], reverse=True)
    elif sort_by == 'turnover':
        profit_analysis.sort(key=lambda x: x['turnover_rate'], reverse=True)
    elif sort_by == 'inventory_value':
        profit_analysis.sort(key=lambda x: x['inventory_value'], reverse=True)
    
    # Calculate overall metrics
    net_profit = total_sold_profit - total_expenses
    overall_margin = (total_sold_profit / (total_sold_profit + total_expenses) * 100) if (total_sold_profit + total_expenses) > 0 else 0
    
    # Top performing items
    top_profit_items = sorted(profit_analysis, key=lambda x: x['actual_profit'], reverse=True)[:5]
    top_margin_items = sorted(profit_analysis, key=lambda x: x['retail_margin'], reverse=True)[:5]
    low_margin_items = sorted(profit_analysis, key=lambda x: x['retail_margin'])[:5]
    
    # Category breakdown
    category_analysis = {}
    for analysis in profit_analysis:
        category_name = analysis['item'].category.name if analysis['item'].category else 'Uncategorized'
        if category_name not in category_analysis:
            category_analysis[category_name] = {
                'total_profit': 0,
                'total_revenue': 0,
                'total_inventory_value': 0,
                'item_count': 0
            }
        
        category_analysis[category_name]['total_profit'] += analysis['actual_profit']
        category_analysis[category_name]['total_revenue'] += analysis['revenue']
        category_analysis[category_name]['total_inventory_value'] += analysis['inventory_value']
        category_analysis[category_name]['item_count'] += 1
    
    # Get all categories for filter
    categories = Category.query.order_by(Category.name).all()
    
    return render_template('profit_analysis.html',
        profit_analysis=profit_analysis,
        categories=categories,
        category_id=category_id,
        date_range=date_range,
        sort_by=sort_by,
        total_inventory_value=total_inventory_value,
        total_potential_profit=total_potential_profit,
        total_sold_profit=total_sold_profit,
        total_expenses=total_expenses,
        net_profit=net_profit,
        overall_margin=overall_margin,
        top_profit_items=top_profit_items,
        top_margin_items=top_margin_items,
        low_margin_items=low_margin_items,
        category_analysis=category_analysis,
        start_date=start_date,
        end_date=end_date
    )

@app.route('/categories')
@login_required
def categories_management():
    """Category management dashboard with subcategory support"""
    
    # Get filter parameters
    search = request.args.get('search', '')
    show_subcategories = request.args.get('show_subcategories', 'true') == 'true'
    
    # Build query for root categories or all categories
    if show_subcategories:
        query = Category.query.filter_by(is_active=True)
    else:
        query = Category.query.filter_by(parent_id=None, is_active=True)
    
    if search:
        query = query.filter(Category.name.ilike(f'%{search}%'))
    
    categories = query.order_by(Category.sort_order, Category.name).all()
    
    # Calculate statistics for each category
    category_stats = []
    for category in categories:
        # Get all items in this category and subcategories
        all_items = category.get_all_items()
        active_items = [item for item in all_items if item.is_active]
        
        # Count items
        item_count = len(active_items)
        subcategory_count = len(category.get_descendants())
        
        # Calculate total inventory value
        total_value = sum((item.buying_price or 0) * item.stock_quantity for item in active_items)
        total_retail_value = sum((item.retail_price or 0) * item.stock_quantity for item in active_items)
        
        # Count low stock items
        low_stock_count = sum(1 for item in active_items if item.stock_quantity <= item.minimum_stock)
        
        # Calculate recent sales (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        from sqlalchemy import func
        item_ids = [item.id for item in active_items]
        recent_sales = 0
        if item_ids:
            recent_sales = db.session.query(func.sum(SaleItem.quantity)).join(Sale).filter(
                SaleItem.item_id.in_(item_ids),
                Sale.created_at >= thirty_days_ago
            ).scalar() or 0
        
        category_stats.append({
            'category': category,
            'item_count': item_count,
            'subcategory_count': subcategory_count,
            'total_value': total_value,
            'total_retail_value': total_retail_value,
            'low_stock_count': low_stock_count,
            'recent_sales': recent_sales,
            'potential_profit': total_retail_value - total_value
        })
    
    return render_template('categories_management.html', 
                         category_stats=category_stats,
                         search=search,
                         show_subcategories=show_subcategories)

@app.route('/categories/add', methods=['GET', 'POST'])
@login_required
def add_category():
    """Add a new category with subcategory support"""
    
    # Get all active categories for parent selection
    parent_categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    
    if request.method == 'POST':
        try:
            name = request.form['name'].strip()
            description = request.form.get('description', '').strip()
            parent_id = request.form.get('parent_id')
            sort_order = request.form.get('sort_order', '0')
            
            # Convert parent_id and sort_order
            parent_id = int(parent_id) if parent_id and parent_id != '' else None
            try:
                sort_order = int(sort_order) if sort_order else 0
            except ValueError:
                sort_order = 0
            
            # Check if category already exists with same name and parent
            existing_category = Category.query.filter_by(name=name, parent_id=parent_id).first()
            if existing_category:
                if parent_id:
                    parent = Category.query.get(parent_id)
                    flash(f'Subcategory with this name already exists under "{parent.name}"!', 'danger')
                else:
                    flash('Root category with this name already exists!', 'danger')
                return redirect(url_for('add_category'))
            
            # Validate parent exists if specified
            if parent_id:
                parent = Category.query.get(parent_id)
                if not parent or not parent.is_active:
                    flash('Selected parent category does not exist!', 'danger')
                    return redirect(url_for('add_category'))
            
            # Create new category
            category = Category(
                name=name,
                description=description if description else None,
                parent_id=parent_id,
                sort_order=sort_order,
                is_active=True
            )
            
            db.session.add(category)
            db.session.commit()
            
            if parent_id:
                parent = Category.query.get(parent_id)
                flash(f'Subcategory "{name}" added under "{parent.name}" successfully!', 'success')
            else:
                flash(f'Category "{name}" added successfully!', 'success')
            return redirect(url_for('categories_management'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding category: {str(e)}', 'danger')
    
    return render_template('add_category.html', parent_categories=parent_categories)

@app.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    """Edit a category"""
    
    category = Category.query.get_or_404(category_id)
    
    if request.method == 'POST':
        try:
            name = request.form['name'].strip()
            description = request.form.get('description', '').strip()
            
            # Check if another category with this name exists
            existing_category = Category.query.filter(
                Category.name == name,
                Category.id != category_id
            ).first()
            
            if existing_category:
                flash('Another category with this name already exists!', 'danger')
                return redirect(url_for('edit_category', category_id=category_id))
            
            # Update category
            category.name = name
            category.description = description if description else None
            
            db.session.commit()
            
            flash(f'Category "{name}" updated successfully!', 'success')
            return redirect(url_for('categories_management'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating category: {str(e)}', 'danger')
    
    return render_template('edit_category.html', category=category)

@app.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    """Delete a category"""
    
    category = Category.query.get_or_404(category_id)
    
    try:
        # Check if category has items
        item_count = Item.query.filter_by(category_id=category_id).count()
        
        if item_count > 0:
            flash(f'Cannot delete category "{category.name}" because it has {item_count} items. Move or delete the items first.', 'danger')
            return redirect(url_for('categories_management'))
        
        # Delete category
        db.session.delete(category)
        db.session.commit()
        
        flash(f'Category "{category.name}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {str(e)}', 'danger')
    
    return redirect(url_for('categories_management'))

@app.route('/categories/<int:category_id>/items')
@login_required
def category_items(category_id):
    """View items in a specific category"""
    
    category = Category.query.get_or_404(category_id)
    
    # Get filter parameters
    search = request.args.get('search', '')
    stock_filter = request.args.get('stock_filter', 'all')  # 'all', 'low_stock', 'out_of_stock'
    sort_by = request.args.get('sort_by', 'name')
    page = request.args.get('page', 1, type=int)
    
    # Build query
    query = Item.query.filter_by(category_id=category_id, is_active=True)
    
    if search:
        query = query.filter(Item.name.ilike(f'%{search}%'))
    
    if stock_filter == 'low_stock':
        query = query.filter(Item.stock_quantity <= Item.minimum_stock)
    elif stock_filter == 'out_of_stock':
        query = query.filter(Item.stock_quantity == 0)
    
    # Apply sorting
    if sort_by == 'name':
        query = query.order_by(Item.name)
    elif sort_by == 'stock':
        query = query.order_by(Item.stock_quantity.desc())
    elif sort_by == 'price':
        query = query.order_by(Item.retail_price.desc())
    elif sort_by == 'margin':
        query = query.order_by((Item.retail_price - Item.buying_price).desc())
    
    items = query.paginate(page=page, per_page=20, error_out=False)
    
    # Get all categories for bulk move functionality
    categories = Category.query.order_by(Category.name).all()
    
    return render_template('category_items.html',
                         category=category,
                         items=items,
                         categories=categories,
                         search=search,
                         stock_filter=stock_filter,
                         sort_by=sort_by)

@app.route('/categories/<int:category_id>/bulk-update', methods=['POST'])
@login_required
def bulk_update_category_items(category_id):
    """Bulk update items in a category"""
    
    category = Category.query.get_or_404(category_id)
    
    try:
        action = request.form.get('action')
        selected_items = request.form.getlist('selected_items')
        
        if not selected_items:
            flash('No items selected!', 'warning')
            return redirect(url_for('category_items', category_id=category_id))
        
        items = Item.query.filter(Item.id.in_(selected_items)).all()
        
        if action == 'update_prices':
            # Bulk price update
            percentage = float(request.form.get('price_percentage', 0))
            
            for item in items:
                if percentage != 0:
                    # Update retail price by percentage
                    new_price = float(item.retail_price) * (1 + percentage / 100)
                    item.retail_price = round(new_price, 2)
                    
                    # Update wholesale price proportionally
                    if item.wholesale_price:
                        new_wholesale = float(item.wholesale_price) * (1 + percentage / 100)
                        item.wholesale_price = round(new_wholesale, 2)
            
            flash(f'Updated prices for {len(items)} items by {percentage}%', 'success')
            
        elif action == 'move_category':
            # Move items to another category
            new_category_id = int(request.form.get('new_category_id'))
            new_category = Category.query.get(new_category_id)
            
            if new_category:
                for item in items:
                    item.category_id = new_category_id
                
                flash(f'Moved {len(items)} items to "{new_category.name}" category', 'success')
            else:
                flash('Invalid category selected!', 'danger')
                
        elif action == 'update_status':
            # Bulk status update
            new_status = request.form.get('new_status') == 'active'
            
            for item in items:
                item.is_active = new_status
            
            status_text = 'activated' if new_status else 'deactivated'
            flash(f'{status_text.capitalize()} {len(items)} items', 'success')
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating items: {str(e)}', 'danger')
    
    return redirect(url_for('category_items', category_id=category_id))

# Call the function to create default data
with app.app_context():
    create_default_data()


@app.route('/route-map')
@login_required
def route_map():
    """Display comprehensive application route mapping"""
    return render_template('route_map.html')

@app.route('/api/routes')
@login_required
def api_routes():
    """API endpoint to get all application routes dynamically"""
    import re
    from collections import defaultdict
    
    # Get all registered routes from Flask app
    routes_data = []
    blueprints_data = defaultdict(lambda: {'name': '', 'prefix': '', 'route_count': 0, 'routes': []})
    
    for rule in app.url_map.iter_rules():
        # Skip static files and internal routes
        if rule.endpoint in ['static', '_debug_toolbar.static']:
            continue
            
        # Parse blueprint and function name
        blueprint_name = 'main'
        function_name = rule.endpoint
        
        if '.' in rule.endpoint:
            blueprint_name, function_name = rule.endpoint.split('.', 1)
        
        # Determine file based on blueprint
        file_mapping = {
            'main': 'routes.py',
            'auth': 'auth.py', 
            'admin_portal': 'admin_portal.py',
            'admin': 'admin_routes.py',
            'sms': 'routes_sms.py',
            'language': 'language_routes.py'
        }
        
        # Get blueprint prefix
        blueprint_prefix = ''
        for bp_name, blueprint in app.blueprints.items():
            if bp_name == blueprint_name:
                blueprint_prefix = blueprint.url_prefix or ''
                break
        
        route_info = {
            'path': str(rule.rule),
            'full_path': str(rule.rule),
            'methods': sorted(list(rule.methods - {'HEAD', 'OPTIONS'})),
            'blueprint': blueprint_name,
            'function': function_name,
            'file': file_mapping.get(blueprint_name, 'unknown.py'),
            'endpoint': rule.endpoint
        }
        
        routes_data.append(route_info)
        
        # Update blueprint data
        if blueprint_name not in blueprints_data:
            blueprints_data[blueprint_name] = {
                'name': blueprint_name,
                'prefix': blueprint_prefix,
                'route_count': 0,
                'routes': [],
                'file': file_mapping.get(blueprint_name, 'unknown.py')
            }
        
        blueprints_data[blueprint_name]['route_count'] += 1
        blueprints_data[blueprint_name]['routes'].append(route_info)
    
    # Sort routes by path
    routes_data.sort(key=lambda x: x['full_path'])
    
    return jsonify({
        'total_routes': len(routes_data),
        'routes': routes_data,
        'blueprints': dict(blueprints_data),
        'files_analyzed': len(set(route['file'] for route in routes_data))
    })

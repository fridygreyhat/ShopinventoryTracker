from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from models import User, Customer, Sale
from sms_service import sms_service
from sms_scheduler import sms_scheduler
import logging

# Create SMS routes blueprint
sms_bp = Blueprint('sms', __name__, url_prefix='/sms')

@sms_bp.route('/dashboard')
@login_required
def dashboard():
    """SMS dashboard showing statistics and recent activity"""
    try:
        # Get SMS statistics
        total_customers = Customer.query.filter_by(user_id=current_user.id).filter(
            Customer.phone.isnot(None)
        ).count()
        
        recent_sales = Sale.query.filter_by(user_id=current_user.id).filter(
            Sale.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        # Check SMS service status
        sms_enabled = current_user.sms_notifications and current_user.phone is not None
        
        stats = {
            'customers_with_sms': total_customers,
            'recent_sales': recent_sales,
            'sms_enabled': sms_enabled,
            'phone_configured': current_user.phone is not None
        }
        
        return render_template('sms/dashboard.html', stats=stats)
        
    except Exception as e:
        logging.error(f"SMS dashboard error: {str(e)}")
        flash('Error loading SMS dashboard', 'error')
        return redirect(url_for('dashboard'))

@sms_bp.route('/send-bulk', methods=['GET', 'POST'])
@login_required
def send_bulk_sms():
    """Send bulk SMS to customers"""
    if request.method == 'POST':
        try:
            message = request.form.get('message', '').strip()
            recipient_type = request.form.get('recipient_type', 'all')
            
            if not message:
                flash('Message content is required', 'error')
                return render_template('sms/bulk_send.html')
            
            # Get customer phone numbers based on selection
            customers_query = Customer.query.filter_by(user_id=current_user.id).filter(
                Customer.phone.isnot(None)
            )
            
            if recipient_type == 'recent':
                # Customers with sales in last 30 days
                from datetime import timedelta
                recent_date = datetime.utcnow() - timedelta(days=30)
                customer_ids = db.session.query(Sale.customer_id).filter(
                    Sale.user_id == current_user.id,
                    Sale.created_at >= recent_date,
                    Sale.customer_id.isnot(None)
                ).distinct().subquery()
                customers_query = customers_query.filter(Customer.id.in_(customer_ids))
            
            customers = customers_query.all()
            
            if not customers:
                flash('No customers found with phone numbers', 'warning')
                return render_template('sms/bulk_send.html')
            
            # Send bulk SMS
            phone_numbers = [customer.phone for customer in customers]
            business_signature = f"\n\n- {current_user.shop_name or 'Mauzo TZ'}"
            full_message = message + business_signature
            
            results = sms_service.send_bulk_sms(phone_numbers, full_message)
            
            flash(f'Bulk SMS sent: {results["success"]} successful, {results["failed"]} failed', 
                  'success' if results['success'] > 0 else 'error')
                  
            if results['failed'] > 0:
                flash(f'Failed numbers: {", ".join(results["errors"])}', 'warning')
            
            return redirect(url_for('sms.dashboard'))
            
        except Exception as e:
            logging.error(f"Bulk SMS error: {str(e)}")
            flash('Failed to send bulk SMS', 'error')
    
    # Get customer counts for display
    total_customers = Customer.query.filter_by(user_id=current_user.id).filter(
        Customer.phone.isnot(None)
    ).count()
    
    return render_template('sms/bulk_send.html', total_customers=total_customers)

@sms_bp.route('/send-promotional', methods=['GET', 'POST'])
@login_required
def send_promotional():
    """Send promotional SMS to selected customers"""
    if request.method == 'POST':
        try:
            promotion_text = request.form.get('promotion_text', '').strip()
            customer_ids = request.form.getlist('customer_ids')
            
            if not promotion_text:
                flash('Promotion text is required', 'error')
                return render_template('sms/promotional.html')
            
            if not customer_ids:
                flash('Please select at least one customer', 'error')
                return render_template('sms/promotional.html')
            
            # Send promotional SMS to selected customers
            customers = Customer.query.filter(
                Customer.id.in_(customer_ids),
                Customer.user_id == current_user.id,
                Customer.phone.isnot(None)
            ).all()
            
            success_count = 0
            for customer in customers:
                success = sms_service.send_promotional_sms(
                    customer.phone,
                    customer.name,
                    promotion_text,
                    current_user.shop_name
                )
                if success:
                    success_count += 1
            
            flash(f'Promotional SMS sent to {success_count} out of {len(customers)} customers', 'success')
            return redirect(url_for('sms.dashboard'))
            
        except Exception as e:
            logging.error(f"Promotional SMS error: {str(e)}")
            flash('Failed to send promotional SMS', 'error')
    
    # Get customers for selection
    customers = Customer.query.filter_by(user_id=current_user.id).filter(
        Customer.phone.isnot(None)
    ).all()
    
    return render_template('sms/promotional.html', customers=customers)

@sms_bp.route('/payment-reminders')
@login_required
def payment_reminders():
    """Manual trigger for payment reminders"""
    try:
        sms_scheduler.send_payment_reminders()
        sms_scheduler.send_upcoming_payment_reminders()
        flash('Payment reminders sent successfully', 'success')
    except Exception as e:
        logging.error(f"Manual payment reminders error: {str(e)}")
        flash('Failed to send payment reminders', 'error')
    
    return redirect(url_for('sms.dashboard'))

@sms_bp.route('/test-sms', methods=['POST'])
@login_required
def test_sms_endpoint():
    """Test SMS endpoint for AJAX calls"""
    try:
        phone = request.json.get('phone', current_user.phone)
        if not phone:
            return jsonify({'success': False, 'message': 'Phone number required'})
        
        test_message = f"Test SMS from {current_user.shop_name or 'Mauzo TZ'} - SMS notifications are working correctly!"
        success = sms_service.send_sms(phone, test_message)
        
        return jsonify({
            'success': success,
            'message': f'Test SMS {"sent successfully" if success else "failed"} to {phone}'
        })
        
    except Exception as e:
        logging.error(f"Test SMS endpoint error: {str(e)}")
        return jsonify({'success': False, 'message': 'SMS test failed'})

@sms_bp.route('/customer/<int:customer_id>/send', methods=['POST'])
@login_required
def send_customer_sms(customer_id):
    """Send SMS to specific customer"""
    try:
        customer = Customer.query.filter_by(
            id=customer_id, 
            user_id=current_user.id
        ).first()
        
        if not customer:
            flash('Customer not found', 'error')
            return redirect(url_for('manage_customers'))
        
        if not customer.phone:
            flash('Customer has no phone number', 'error')
            return redirect(url_for('manage_customers'))
        
        message = request.form.get('message', '').strip()
        if not message:
            flash('Message content is required', 'error')
            return redirect(url_for('manage_customers'))
        
        # Add business signature
        full_message = f"{message}\n\n- {current_user.shop_name or 'Mauzo TZ'}"
        
        success = sms_service.send_sms(customer.phone, full_message)
        
        if success:
            flash(f'SMS sent successfully to {customer.name}', 'success')
        else:
            flash(f'Failed to send SMS to {customer.name}', 'error')
        
        return redirect(url_for('manage_customers'))
        
    except Exception as e:
        logging.error(f"Customer SMS error: {str(e)}")
        flash('Failed to send SMS', 'error')
        return redirect(url_for('manage_customers'))

@sms_bp.route('/settings')
@login_required
def sms_settings():
    """SMS settings and configuration"""
    return render_template('sms/settings.html', user=current_user)
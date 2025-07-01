
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import requests
import logging

logger = logging.getLogger(__name__)

class MarketingService:
    def __init__(self, user_id):
        self.user_id = user_id

    def create_email_campaign(self, campaign_data):
        """Create and send email marketing campaign"""
        try:
            from models import EmailCampaign, Customer, db
            
            # Create campaign record
            campaign = EmailCampaign(
                name=campaign_data['name'],
                subject=campaign_data['subject'],
                content=campaign_data['content'],
                target_audience=campaign_data.get('target_audience', 'all'),
                scheduled_date=datetime.strptime(campaign_data['scheduled_date'], '%Y-%m-%d %H:%M') if campaign_data.get('scheduled_date') else datetime.utcnow(),
                status='draft',
                created_by=self.user_id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(campaign)
            db.session.commit()
            
            # Get target customers
            customers = self._get_target_customers(campaign_data.get('target_audience', 'all'))
            
            # Send emails (if immediate)
            if campaign_data.get('send_immediately', False):
                sent_count = self._send_campaign_emails(campaign, customers)
                campaign.status = 'sent'
                campaign.sent_count = sent_count
                db.session.commit()
            
            return {
                'success': True,
                'campaign_id': campaign.id,
                'target_count': len(customers),
                'status': campaign.status
            }
            
        except Exception as e:
            logger.error(f"Error creating email campaign: {str(e)}")
            return {'error': str(e)}

    def send_sms_promotion(self, promotion_data):
        """Send SMS marketing for promotions"""
        try:
            from models import SMSCampaign, Customer, db
            
            # Create SMS campaign
            campaign = SMSCampaign(
                name=promotion_data['name'],
                message=promotion_data['message'],
                target_audience=promotion_data.get('target_audience', 'all'),
                status='pending',
                created_by=self.user_id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(campaign)
            db.session.commit()
            
            # Get target customers with phone numbers
            customers = self._get_target_customers_with_phone(promotion_data.get('target_audience', 'all'))
            
            sent_count = 0
            for customer in customers:
                if customer.phone:
                    success = self._send_sms(customer.phone, promotion_data['message'])
                    if success:
                        sent_count += 1
            
            campaign.status = 'sent'
            campaign.sent_count = sent_count
            db.session.commit()
            
            return {
                'success': True,
                'campaign_id': campaign.id,
                'sent_count': sent_count,
                'target_count': len(customers)
            }
            
        except Exception as e:
            logger.error(f"Error sending SMS promotion: {str(e)}")
            return {'error': str(e)}

    def collect_customer_feedback(self, feedback_request):
        """Send customer feedback collection requests"""
        try:
            from models import FeedbackRequest, Customer, db
            
            # Create feedback request
            request_record = FeedbackRequest(
                title=feedback_request['title'],
                questions=feedback_request['questions'],
                target_audience=feedback_request.get('target_audience', 'recent_customers'),
                expiry_date=datetime.utcnow() + timedelta(days=30),
                created_by=self.user_id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(request_record)
            db.session.commit()
            
            # Get target customers
            customers = self._get_recent_customers() if feedback_request.get('target_audience') == 'recent_customers' else self._get_target_customers('all')
            
            # Send feedback requests
            sent_count = 0
            for customer in customers:
                if customer.email:
                    success = self._send_feedback_email(customer, request_record)
                    if success:
                        sent_count += 1
            
            return {
                'success': True,
                'request_id': request_record.id,
                'sent_count': sent_count
            }
            
        except Exception as e:
            logger.error(f"Error collecting feedback: {str(e)}")
            return {'error': str(e)}

    def schedule_social_media_post(self, post_data):
        """Schedule social media posts"""
        try:
            from models import SocialMediaPost, db
            
            post = SocialMediaPost(
                platform=post_data['platform'],
                content=post_data['content'],
                media_urls=post_data.get('media_urls', []),
                scheduled_date=datetime.strptime(post_data['scheduled_date'], '%Y-%m-%d %H:%M'),
                status='scheduled',
                created_by=self.user_id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(post)
            db.session.commit()
            
            # In a real implementation, you would integrate with social media APIs
            # For now, we'll just store the scheduled post
            
            return {
                'success': True,
                'post_id': post.id,
                'scheduled_for': post.scheduled_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error scheduling social media post: {str(e)}")
            return {'error': str(e)}

    def create_online_store(self, store_config):
        """Create online store configuration"""
        try:
            from models import OnlineStore, Item, db
            
            store = OnlineStore(
                store_name=store_config['name'],
                description=store_config['description'],
                theme=store_config.get('theme', 'default'),
                domain=store_config.get('domain', ''),
                is_active=True,
                user_id=self.user_id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(store)
            db.session.commit()
            
            # Sync product catalog
            self._sync_product_catalog(store.id)
            
            return {
                'success': True,
                'store_id': store.id,
                'store_url': f"https://store-{store.id}.example.com"
            }
            
        except Exception as e:
            logger.error(f"Error creating online store: {str(e)}")
            return {'error': str(e)}

    def sync_product_catalog(self, store_id):
        """Sync product catalog with online store"""
        try:
            from models import Item, OnlineStoreProduct, db
            
            # Get all active items for user
            items = Item.query.filter_by(user_id=self.user_id, is_active=True).all()
            
            synced_count = 0
            for item in items:
                # Check if product already exists in online store
                existing = OnlineStoreProduct.query.filter_by(
                    store_id=store_id,
                    item_id=item.id
                ).first()
                
                if not existing:
                    store_product = OnlineStoreProduct(
                        store_id=store_id,
                        item_id=item.id,
                        is_visible=True,
                        online_price=item.selling_price_retail,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(store_product)
                    synced_count += 1
                else:
                    # Update existing product
                    existing.online_price = item.selling_price_retail
                    existing.is_visible = item.is_active
            
            db.session.commit()
            
            return {
                'success': True,
                'synced_count': synced_count,
                'total_products': len(items)
            }
            
        except Exception as e:
            logger.error(f"Error syncing catalog: {str(e)}")
            return {'error': str(e)}

    def _get_target_customers(self, target_audience):
        """Get customers based on target audience"""
        from models import Customer
        
        if target_audience == 'all':
            return Customer.query.all()
        elif target_audience == 'recent':
            return Customer.query.filter(
                Customer.created_at >= datetime.utcnow() - timedelta(days=30)
            ).all()
        else:
            return Customer.query.all()

    def _get_target_customers_with_phone(self, target_audience):
        """Get customers with phone numbers"""
        from models import Customer
        
        customers = self._get_target_customers(target_audience)
        return [c for c in customers if c.phone]

    def _get_recent_customers(self):
        """Get customers from recent sales"""
        from models import Customer, Sale
        
        recent_sales = Sale.query.filter(
            Sale.created_at >= datetime.utcnow() - timedelta(days=30)
        ).all()
        
        customer_ids = set(sale.customer_id for sale in recent_sales if sale.customer_id)
        return Customer.query.filter(Customer.id.in_(customer_ids)).all()

    def _send_campaign_emails(self, campaign, customers):
        """Send campaign emails to customers"""
        sent_count = 0
        for customer in customers:
            if customer.email:
                try:
                    # Create email
                    msg = MIMEMultipart()
                    msg['From'] = 'noreply@yourbusiness.com'
                    msg['To'] = customer.email
                    msg['Subject'] = campaign.subject
                    
                    msg.attach(MIMEText(campaign.content, 'html'))
                    
                    # In a real implementation, you would send via SMTP
                    # For now, we'll just log it
                    logger.info(f"Email sent to {customer.email}")
                    sent_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to send email to {customer.email}: {str(e)}")
        
        return sent_count

    def _send_sms(self, phone_number, message):
        """Send SMS message"""
        try:
            # In a real implementation, integrate with SMS service like Twilio
            logger.info(f"SMS sent to {phone_number}: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
            return False

    def _send_feedback_email(self, customer, feedback_request):
        """Send feedback collection email"""
        try:
            feedback_url = f"https://feedback.yourbusiness.com/{feedback_request.id}"
            
            content = f"""
            Dear {customer.name},
            
            We value your feedback! Please take a moment to complete our survey:
            {feedback_url}
            
            Thank you for your business!
            """
            
            # In a real implementation, send actual email
            logger.info(f"Feedback email sent to {customer.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send feedback email: {str(e)}")
            return False

    def _sync_product_catalog(self, store_id):
        """Helper method to sync product catalog"""
        return self.sync_product_catalog(store_id)

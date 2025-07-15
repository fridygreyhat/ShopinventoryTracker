from datetime import datetime, timedelta
from flask import current_app
from models import db, Customer, EmailCampaign, SMSCampaign, OnlineStore
import logging
import uuid

logger = logging.getLogger(__name__)

class MarketingService:
    def __init__(self, user_id):
        self.user_id = user_id

    def create_email_campaign(self, campaign_data):
        """Create email marketing campaign"""
        try:
            campaign = EmailCampaign(
                name=campaign_data['name'],
                subject=campaign_data['subject'],
                content=campaign_data['content'],
                target_audience=campaign_data.get('target_audience', 'all'),
                scheduled_date=datetime.strptime(campaign_data['scheduled_date'], '%Y-%m-%d %H:%M') if campaign_data.get('scheduled_date') else None,
                created_by=self.user_id
            )

            db.session.add(campaign)
            db.session.commit()

            return {
                'success': True,
                'campaign_id': campaign.id,
                'message': 'Email campaign created successfully'
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating email campaign: {str(e)}")
            return {'success': False, 'error': str(e)}

    def send_sms_promotion(self, promotion_data):
        """Send SMS promotion"""
        try:
            # Get target customers
            customers = Customer.query.filter_by(user_id=self.user_id).all()

            campaign = SMSCampaign(
                name=promotion_data['name'],
                message=promotion_data['message'],
                target_audience=promotion_data.get('target_audience', 'all'),
                created_by=self.user_id
            )

            db.session.add(campaign)

            # In a real implementation, you'd integrate with SMS service here
            sent_count = 0
            for customer in customers:
                if customer.phone:
                    # Mock SMS sending
                    sent_count += 1

            campaign.sent_count = sent_count
            campaign.status = 'sent'
            db.session.commit()

            return {
                'success': True,
                'campaign_id': campaign.id,
                'sent_count': sent_count,
                'message': f'SMS promotion sent to {sent_count} customers'
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error sending SMS promotion: {str(e)}")
            return {'success': False, 'error': str(e)}

    def collect_customer_feedback(self, feedback_data):
        """Collect customer feedback"""
        try:
            # Create feedback request
            from models import FeedbackRequest

            feedback_request = FeedbackRequest(
                title=feedback_data['title'],
                questions=feedback_data['questions'],
                target_audience=feedback_data.get('target_audience', 'all'),
                expiry_date=datetime.strptime(feedback_data['expiry_date'], '%Y-%m-%d') if feedback_data.get('expiry_date') else None,
                created_by=self.user_id
            )

            db.session.add(feedback_request)
            db.session.commit()

            return {
                'success': True,
                'feedback_id': feedback_request.id,
                'message': 'Feedback request created successfully'
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating feedback request: {str(e)}")
            return {'success': False, 'error': str(e)}

    def schedule_social_media_post(self, post_data):
        """Schedule social media post"""
        try:
            from models import SocialMediaPost

            post = SocialMediaPost(
                platform=post_data['platform'],
                content=post_data['content'],
                media_urls=post_data.get('media_urls', []),
                scheduled_date=datetime.strptime(post_data['scheduled_date'], '%Y-%m-%d %H:%M'),
                created_by=self.user_id
            )

            db.session.add(post)
            db.session.commit()

            return {
                'success': True,
                'post_id': post.id,
                'message': 'Social media post scheduled successfully'
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error scheduling social media post: {str(e)}")
            return {'success': False, 'error': str(e)}

    def create_online_store(self, store_data):
        """Create online store"""
        try:
            store = OnlineStore(
                store_name=store_data['store_name'],
                description=store_data.get('description', ''),
                theme=store_data.get('theme', 'default'),
                domain=store_data.get('domain'),
                user_id=self.user_id
            )

            db.session.add(store)
            db.session.commit()

            return {
                'success': True,
                'store_id': store.id,
                'message': 'Online store created successfully'
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating online store: {str(e)}")
            return {'success': False, 'error': str(e)}

    def sync_product_catalog(self, store_id):
        """Sync product catalog with online store"""
        try:
            from models import Item, OnlineStoreProduct

            # Get store
            store = OnlineStore.query.filter_by(id=store_id, user_id=self.user_id).first()
            if not store:
                return {'success': False, 'error': 'Store not found'}

            # Get all active items
            items = Item.query.filter_by(user_id=self.user_id, is_active=True).all()

            synced_count = 0
            for item in items:
                # Check if already synced
                existing = OnlineStoreProduct.query.filter_by(
                    store_id=store_id,
                    item_id=item.id
                ).first()

                if not existing:
                    store_product = OnlineStoreProduct(
                        store_id=store_id,
                        item_id=item.id,
                        online_price=item.retail_price
                    )
                    db.session.add(store_product)
                    synced_count += 1

            db.session.commit()

            return {
                'success': True,
                'synced_count': synced_count,
                'message': f'Synced {synced_count} products to online store'
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error syncing product catalog: {str(e)}")
            return {'success': False, 'error': str(e)}
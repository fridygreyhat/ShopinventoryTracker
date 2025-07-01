
import json
import csv
import io
import zipfile
from datetime import datetime, timedelta
import boto3
import pandas as pd
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class DataManagementService:
    def __init__(self, user_id):
        self.user_id = user_id

    def create_automated_backup(self):
        """Create automated backup of user data"""
        try:
            from models import Item, Sale, Customer, FinancialTransaction, db
            
            backup_data = {
                'metadata': {
                    'user_id': self.user_id,
                    'backup_date': datetime.utcnow().isoformat(),
                    'version': '1.0'
                },
                'items': [],
                'sales': [],
                'customers': [],
                'transactions': []
            }
            
            # Get user data
            items = Item.query.filter_by(user_id=self.user_id).all()
            sales = Sale.query.filter_by(user_id=self.user_id).all()
            customers = Customer.query.all()  # Assuming customers are shared
            transactions = FinancialTransaction.query.all()
            
            # Serialize data
            backup_data['items'] = [item.to_dict() for item in items]
            backup_data['sales'] = [sale.to_dict() for sale in sales]
            backup_data['customers'] = [customer.to_dict() for customer in customers]
            backup_data['transactions'] = [tx.to_dict() for tx in transactions]
            
            # Create backup file
            backup_json = json.dumps(backup_data, indent=2)
            
            # Save to cloud storage (mock implementation)
            backup_filename = f"backup_{self.user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            
            return {
                'success': True,
                'backup_file': backup_filename,
                'backup_size': len(backup_json),
                'records_count': {
                    'items': len(backup_data['items']),
                    'sales': len(backup_data['sales']),
                    'customers': len(backup_data['customers']),
                    'transactions': len(backup_data['transactions'])
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return {'error': str(e)}

    def export_data_multiple_formats(self, data_type, format_type):
        """Export data in multiple formats (CSV, JSON, Excel)"""
        try:
            from models import Item, Sale, Customer, FinancialTransaction
            
            # Get data based on type
            data = []
            if data_type == 'items':
                items = Item.query.filter_by(user_id=self.user_id).all()
                data = [item.to_dict() for item in items]
            elif data_type == 'sales':
                sales = Sale.query.filter_by(user_id=self.user_id).all()
                data = [sale.to_dict() for sale in sales]
            elif data_type == 'customers':
                customers = Customer.query.all()
                data = [customer.to_dict() for customer in customers]
            elif data_type == 'transactions':
                transactions = FinancialTransaction.query.all()
                data = [tx.to_dict() for tx in transactions]
            
            if format_type == 'csv':
                if not data:
                    return {'error': 'No data to export'}
                
                output = io.StringIO()
                if data:
                    writer = csv.DictWriter(output, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
                
                return {
                    'format': 'csv',
                    'content': output.getvalue(),
                    'filename': f"{data_type}_export_{datetime.now().strftime('%Y%m%d')}.csv"
                }
                
            elif format_type == 'json':
                return {
                    'format': 'json',
                    'content': json.dumps(data, indent=2),
                    'filename': f"{data_type}_export_{datetime.now().strftime('%Y%m%d')}.json"
                }
                
            elif format_type == 'excel':
                df = pd.DataFrame(data)
                output = io.BytesIO()
                df.to_excel(output, index=False, engine='xlsxwriter')
                
                return {
                    'format': 'excel',
                    'content': output.getvalue(),
                    'filename': f"{data_type}_export_{datetime.now().strftime('%Y%m%d')}.xlsx"
                }
                
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            return {'error': str(e)}

    def create_price_version_control(self, item_id, old_price, new_price, reason):
        """Create version control for price changes"""
        try:
            from models import PriceHistory, db
            
            price_history = PriceHistory(
                item_id=item_id,
                old_price=old_price,
                new_price=new_price,
                change_reason=reason,
                changed_by=self.user_id,
                change_date=datetime.utcnow()
            )
            
            db.session.add(price_history)
            db.session.commit()
            
            return {'success': True, 'history_id': price_history.id}
            
        except Exception as e:
            logger.error(f"Error creating price history: {str(e)}")
            return {'error': str(e)}

    def archive_old_records(self, archive_before_date):
        """Archive old records to improve performance"""
        try:
            from models import Sale, FinancialTransaction, ArchivedSale, ArchivedTransaction, db
            
            archived_count = 0
            
            # Archive old sales
            old_sales = Sale.query.filter(Sale.created_at < archive_before_date).all()
            for sale in old_sales:
                archived_sale = ArchivedSale(
                    original_id=sale.id,
                    data=sale.to_dict(),
                    archived_date=datetime.utcnow(),
                    user_id=self.user_id
                )
                db.session.add(archived_sale)
                db.session.delete(sale)
                archived_count += 1
            
            # Archive old transactions
            old_transactions = FinancialTransaction.query.filter(
                FinancialTransaction.created_at < archive_before_date
            ).all()
            
            for transaction in old_transactions:
                archived_tx = ArchivedTransaction(
                    original_id=transaction.id,
                    data=transaction.to_dict(),
                    archived_date=datetime.utcnow(),
                    user_id=self.user_id
                )
                db.session.add(archived_tx)
                db.session.delete(transaction)
                archived_count += 1
            
            db.session.commit()
            
            return {
                'success': True,
                'archived_count': archived_count,
                'archive_date': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error archiving records: {str(e)}")
            db.session.rollback()
            return {'error': str(e)}

    def schedule_automated_backups(self, frequency='daily'):
        """Schedule automated backups"""
        try:
            from models import BackupSchedule, db
            
            schedule = BackupSchedule(
                user_id=self.user_id,
                frequency=frequency,
                next_backup=self._calculate_next_backup(frequency),
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            db.session.add(schedule)
            db.session.commit()
            
            return {'success': True, 'schedule_id': schedule.id}
            
        except Exception as e:
            logger.error(f"Error scheduling backup: {str(e)}")
            return {'error': str(e)}

    def _calculate_next_backup(self, frequency):
        """Calculate next backup time based on frequency"""
        now = datetime.utcnow()
        if frequency == 'daily':
            return now + timedelta(days=1)
        elif frequency == 'weekly':
            return now + timedelta(weeks=1)
        elif frequency == 'monthly':
            return now + timedelta(days=30)
        else:
            return now + timedelta(days=1)

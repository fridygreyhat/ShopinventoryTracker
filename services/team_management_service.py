
from datetime import datetime, timedelta
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class TeamManagementService:
    def __init__(self, user_id):
        self.user_id = user_id

    def track_employee_performance(self, employee_id, period_start, period_end):
        """Track employee performance metrics"""
        try:
            from models import Sale, SaleItem, Employee, db
            from sqlalchemy import func
            
            # Get sales by employee
            employee_sales = Sale.query.filter(
                Sale.employee_id == employee_id,
                Sale.created_at >= period_start,
                Sale.created_at <= period_end
            ).all()
            
            # Calculate metrics
            total_sales = len(employee_sales)
            total_revenue = sum(sale.total_amount for sale in employee_sales)
            avg_sale_value = total_revenue / total_sales if total_sales > 0 else 0
            
            # Get items sold
            items_sold = db.session.query(
                func.sum(SaleItem.quantity)
            ).join(Sale).filter(
                Sale.employee_id == employee_id,
                Sale.created_at >= period_start,
                Sale.created_at <= period_end
            ).scalar() or 0
            
            performance_data = {
                'employee_id': employee_id,
                'period': {
                    'start': period_start.isoformat(),
                    'end': period_end.isoformat()
                },
                'metrics': {
                    'total_sales': total_sales,
                    'total_revenue': float(total_revenue),
                    'average_sale_value': float(avg_sale_value),
                    'items_sold': int(items_sold),
                    'sales_per_day': total_sales / ((period_end - period_start).days + 1)
                },
                'ranking': self._calculate_employee_ranking(employee_id, period_start, period_end)
            }
            
            return performance_data
            
        except Exception as e:
            logger.error(f"Error tracking employee performance: {str(e)}")
            return {'error': str(e)}

    def calculate_commission(self, employee_id, period_start, period_end):
        """Calculate employee commission"""
        try:
            from models import Sale, Employee, CommissionRule, db
            
            # Get employee commission rules
            employee = Employee.query.get(employee_id)
            if not employee:
                return {'error': 'Employee not found'}
            
            # Get sales for the period
            employee_sales = Sale.query.filter(
                Sale.employee_id == employee_id,
                Sale.created_at >= period_start,
                Sale.created_at <= period_end
            ).all()
            
            total_sales_amount = sum(sale.total_amount for sale in employee_sales)
            
            # Calculate commission based on rules
            commission_rate = employee.commission_rate or 0.05  # Default 5%
            base_commission = total_sales_amount * commission_rate
            
            # Apply bonuses
            bonus_commission = 0
            if total_sales_amount > 10000:  # Bonus for high sales
                bonus_commission = total_sales_amount * 0.01
            
            total_commission = base_commission + bonus_commission
            
            return {
                'employee_id': employee_id,
                'period': {
                    'start': period_start.isoformat(),
                    'end': period_end.isoformat()
                },
                'sales_amount': float(total_sales_amount),
                'commission_rate': commission_rate,
                'base_commission': float(base_commission),
                'bonus_commission': float(bonus_commission),
                'total_commission': float(total_commission)
            }
            
        except Exception as e:
            logger.error(f"Error calculating commission: {str(e)}")
            return {'error': str(e)}

    def manage_shifts(self, employee_id, shift_data):
        """Manage employee shifts and scheduling"""
        try:
            from models import Shift, db
            
            shift = Shift(
                employee_id=employee_id,
                shift_date=datetime.strptime(shift_data['date'], '%Y-%m-%d').date(),
                start_time=datetime.strptime(shift_data['start_time'], '%H:%M').time(),
                end_time=datetime.strptime(shift_data['end_time'], '%H:%M').time(),
                shift_type=shift_data.get('type', 'regular'),
                notes=shift_data.get('notes', ''),
                created_by=self.user_id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(shift)
            db.session.commit()
            
            return {
                'success': True,
                'shift_id': shift.id,
                'message': 'Shift scheduled successfully'
            }
            
        except Exception as e:
            logger.error(f"Error managing shift: {str(e)}")
            db.session.rollback()
            return {'error': str(e)}

    def process_inventory_transfer(self, from_location, to_location, items):
        """Process inter-store inventory transfers"""
        try:
            from models import InventoryTransfer, InventoryTransferItem, Item, db
            
            # Create transfer record
            transfer = InventoryTransfer(
                transfer_number=f"TRF-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                from_location_id=from_location,
                to_location_id=to_location,
                status='pending',
                initiated_by=self.user_id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(transfer)
            db.session.flush()  # Get transfer ID
            
            # Add transfer items
            for item_data in items:
                transfer_item = InventoryTransferItem(
                    transfer_id=transfer.id,
                    item_id=item_data['item_id'],
                    quantity=item_data['quantity']
                )
                db.session.add(transfer_item)
                
                # Update item quantities (if approved)
                if item_data.get('auto_approve', False):
                    item = Item.query.get(item_data['item_id'])
                    if item and item.quantity >= item_data['quantity']:
                        item.quantity -= item_data['quantity']
            
            db.session.commit()
            
            return {
                'success': True,
                'transfer_id': transfer.id,
                'transfer_number': transfer.transfer_number
            }
            
        except Exception as e:
            logger.error(f"Error processing transfer: {str(e)}")
            db.session.rollback()
            return {'error': str(e)}

    def _calculate_employee_ranking(self, employee_id, period_start, period_end):
        """Calculate employee ranking among peers"""
        try:
            from models import Sale, Employee, db
            from sqlalchemy import func
            
            # Get all employees' sales for the period
            employee_performance = db.session.query(
                Sale.employee_id,
                func.sum(Sale.total_amount).label('total_sales')
            ).filter(
                Sale.created_at >= period_start,
                Sale.created_at <= period_end
            ).group_by(Sale.employee_id).all()
            
            # Sort by total sales
            ranked_employees = sorted(employee_performance, key=lambda x: x.total_sales, reverse=True)
            
            # Find current employee's rank
            for rank, (emp_id, sales) in enumerate(ranked_employees, 1):
                if emp_id == employee_id:
                    return {
                        'rank': rank,
                        'total_employees': len(ranked_employees),
                        'percentile': round((1 - (rank - 1) / len(ranked_employees)) * 100, 1)
                    }
            
            return {'rank': None, 'total_employees': len(ranked_employees)}
            
        except Exception as e:
            logger.error(f"Error calculating ranking: {str(e)}")
            return {'rank': None}

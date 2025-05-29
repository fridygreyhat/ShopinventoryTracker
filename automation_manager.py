
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import json
from app import db
from models import Item, Sale, SaleItem, FinancialTransaction

logger = logging.getLogger(__name__)

class AutomationManager:
    """Manages automated inventory and business processes"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_auto_purchase_orders(self, user_id: int) -> Dict:
        """
        Generate automatic purchase orders based on stock levels and sales patterns
        
        Args:
            user_id (int): User ID to generate orders for
            
        Returns:
            dict: Purchase order recommendations
        """
        try:
            # Get items that need restocking
            from predictive_analytics import PredictiveStockManager
            
            predictor = PredictiveStockManager(db, Item, Sale, SaleItem)
            recommendations = predictor.get_purchase_recommendations(user_id)
            
            # Group by supplier (if supplier info is available)
            purchase_orders = {}
            
            for rec in recommendations:
                item = Item.query.get(rec['item_id'])
                if not item:
                    continue
                
                supplier = getattr(item, 'supplier', 'Default Supplier')
                
                if supplier not in purchase_orders:
                    purchase_orders[supplier] = {
                        'supplier_name': supplier,
                        'order_date': datetime.utcnow().isoformat(),
                        'items': [],
                        'total_cost': 0,
                        'status': 'draft'
                    }
                
                order_item = {
                    'item_id': item.id,
                    'item_name': item.name,
                    'sku': item.sku,
                    'current_stock': item.quantity,
                    'recommended_quantity': rec['recommended_quantity'],
                    'unit_cost': item.buying_price or 0,
                    'total_cost': (item.buying_price or 0) * rec['recommended_quantity'],
                    'urgency': rec['urgency']
                }
                
                purchase_orders[supplier]['items'].append(order_item)
                purchase_orders[supplier]['total_cost'] += order_item['total_cost']
            
            self.logger.info(f"Generated {len(purchase_orders)} purchase orders for user {user_id}")
            return {
                'success': True,
                'purchase_orders': list(purchase_orders.values()),
                'total_orders': len(purchase_orders)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating purchase orders: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def update_prices_from_suppliers(self, user_id: int) -> Dict:
        """
        Update item prices from supplier APIs (mock implementation)
        
        Args:
            user_id (int): User ID
            
        Returns:
            dict: Price update results
        """
        try:
            updated_items = []
            errors = []
            
            # Get all items for user
            items = Item.query.filter_by(user_id=user_id).all()
            
            for item in items:
                # Mock supplier API call
                try:
                    # In real implementation, this would call actual supplier APIs
                    new_price = self._mock_get_supplier_price(item.sku)
                    
                    if new_price and new_price != item.buying_price:
                        old_price = item.buying_price
                        item.buying_price = new_price
                        item.updated_at = datetime.utcnow()
                        
                        # Auto-update selling prices with margin
                        margin_percentage = 0.3  # 30% margin
                        item.selling_price_retail = new_price * (1 + margin_percentage)
                        item.selling_price_wholesale = new_price * (1 + margin_percentage * 0.8)
                        
                        updated_items.append({
                            'item_id': item.id,
                            'item_name': item.name,
                            'sku': item.sku,
                            'old_price': old_price,
                            'new_price': new_price,
                            'price_change': new_price - old_price
                        })
                        
                except Exception as e:
                    errors.append(f"Failed to update price for {item.name}: {str(e)}")
            
            if updated_items:
                db.session.commit()
                
                # Send price change notifications
                self._send_price_change_notifications(user_id, updated_items)
            
            return {
                'success': True,
                'updated_items': updated_items,
                'total_updated': len(updated_items),
                'errors': errors
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error updating prices from suppliers: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _mock_get_supplier_price(self, sku: str) -> Optional[float]:
        """Mock function to simulate getting price from supplier API"""
        # In real implementation, this would make actual API calls
        import random
        
        # Simulate price changes for some items
        if random.random() < 0.2:  # 20% chance of price change
            # Random price change between -10% to +15%
            change_factor = random.uniform(0.9, 1.15)
            base_price = random.uniform(100, 1000)
            return round(base_price * change_factor, 2)
        
        return None
    
    def _send_price_change_notifications(self, user_id: int, updated_items: List[Dict]):
        """Send notifications about price changes"""
        try:
            from notifications.email_service import send_email
            from models import User
            
            user = User.query.get(user_id)
            if not user or not user.email:
                return
            
            # Create price change summary
            total_items = len(updated_items)
            price_increases = [item for item in updated_items if item['price_change'] > 0]
            price_decreases = [item for item in updated_items if item['price_change'] < 0]
            
            # Generate email content
            html_content = f"""
            <h2>Price Update Notification</h2>
            <p>Hello {user.first_name or user.username},</p>
            <p>We've updated prices for {total_items} items in your inventory:</p>
            
            <h3>Price Changes Summary</h3>
            <ul>
                <li>Price Increases: {len(price_increases)} items</li>
                <li>Price Decreases: {len(price_decreases)} items</li>
            </ul>
            
            <h3>Updated Items</h3>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr>
                    <th>Item</th>
                    <th>SKU</th>
                    <th>Old Price</th>
                    <th>New Price</th>
                    <th>Change</th>
                </tr>
            """
            
            for item in updated_items:
                change_color = 'green' if item['price_change'] > 0 else 'red'
                change_symbol = '+' if item['price_change'] > 0 else ''
                
                html_content += f"""
                <tr>
                    <td>{item['item_name']}</td>
                    <td>{item['sku']}</td>
                    <td>TZS {item['old_price']:,.2f}</td>
                    <td>TZS {item['new_price']:,.2f}</td>
                    <td style="color: {change_color};">{change_symbol}TZS {item['price_change']:,.2f}</td>
                </tr>
                """
            
            html_content += """
            </table>
            <p>Please review these changes and update your selling prices accordingly.</p>
            <p>Best regards,<br>Your Inventory Management System</p>
            """
            
            # Send email
            send_email(
                to_email=user.email,
                from_email="noreply@inventory.com",
                subject=f"Price Update Notification - {total_items} Items Updated",
                html_content=html_content
            )
            
        except Exception as e:
            self.logger.error(f"Error sending price change notifications: {str(e)}")
    
    def generate_scheduled_reports(self, user_id: int, report_type: str = 'daily') -> Dict:
        """
        Generate and send scheduled inventory reports
        
        Args:
            user_id (int): User ID
            report_type (str): 'daily', 'weekly', or 'monthly'
            
        Returns:
            dict: Report generation results
        """
        try:
            from models import User
            
            user = User.query.get(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Determine date range based on report type
            end_date = datetime.utcnow().date()
            
            if report_type == 'daily':
                start_date = end_date
                period_name = 'Daily'
            elif report_type == 'weekly':
                start_date = end_date - timedelta(days=7)
                period_name = 'Weekly'
            elif report_type == 'monthly':
                start_date = end_date - timedelta(days=30)
                period_name = 'Monthly'
            else:
                return {'success': False, 'error': 'Invalid report type'}
            
            # Generate report data
            report_data = self._generate_comprehensive_report(user_id, start_date, end_date)
            
            # Send report via email
            self._send_scheduled_report_email(user, report_data, period_name)
            
            return {
                'success': True,
                'report_type': report_type,
                'period': f"{start_date} to {end_date}",
                'metrics': report_data['summary']
            }
            
        except Exception as e:
            self.logger.error(f"Error generating scheduled report: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _generate_comprehensive_report(self, user_id: int, start_date, end_date) -> Dict:
        """Generate comprehensive report data"""
        try:
            # Get inventory data
            items = Item.query.filter_by(user_id=user_id).all()
            
            # Get sales data for the period
            sales = Sale.query.filter(
                Sale.created_at >= datetime.combine(start_date, datetime.min.time()),
                Sale.created_at <= datetime.combine(end_date, datetime.max.time())
            ).all()
            
            # Calculate metrics
            total_items = len(items)
            total_stock = sum(item.quantity for item in items)
            low_stock_items = [item for item in items if item.quantity <= 10]
            inventory_value = sum(item.quantity * (item.selling_price_retail or 0) for item in items)
            
            total_sales = len(sales)
            total_revenue = sum(sale.total for sale in sales)
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'inventory': {
                    'total_items': total_items,
                    'total_stock': total_stock,
                    'low_stock_count': len(low_stock_items),
                    'inventory_value': inventory_value
                },
                'sales': {
                    'total_transactions': total_sales,
                    'total_revenue': total_revenue,
                    'average_transaction': total_revenue / total_sales if total_sales > 0 else 0
                },
                'summary': {
                    'period_type': f"{start_date} to {end_date}",
                    'key_metrics': {
                        'inventory_value': inventory_value,
                        'total_revenue': total_revenue,
                        'low_stock_alerts': len(low_stock_items)
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error generating report data: {str(e)}")
            return {}
    
    def _send_scheduled_report_email(self, user, report_data: Dict, period_name: str):
        """Send scheduled report via email"""
        try:
            from notifications.email_service import send_email
            
            inventory = report_data.get('inventory', {})
            sales = report_data.get('sales', {})
            
            html_content = f"""
            <h2>{period_name} Inventory Report</h2>
            <p>Hello {user.first_name or user.username},</p>
            <p>Here's your {period_name.lower()} inventory and sales summary:</p>
            
            <h3>Inventory Summary</h3>
            <ul>
                <li>Total Items: {inventory.get('total_items', 0)}</li>
                <li>Total Stock Units: {inventory.get('total_stock', 0):,}</li>
                <li>Low Stock Alerts: {inventory.get('low_stock_count', 0)}</li>
                <li>Inventory Value: TZS {inventory.get('inventory_value', 0):,.2f}</li>
            </ul>
            
            <h3>Sales Summary</h3>
            <ul>
                <li>Total Transactions: {sales.get('total_transactions', 0)}</li>
                <li>Total Revenue: TZS {sales.get('total_revenue', 0):,.2f}</li>
                <li>Average Transaction: TZS {sales.get('average_transaction', 0):,.2f}</li>
            </ul>
            
            <p>Log in to your dashboard for detailed analytics and insights.</p>
            <p>Best regards,<br>Your Inventory Management System</p>
            """
            
            send_email(
                to_email=user.email,
                from_email="reports@inventory.com",
                subject=f"{period_name} Inventory Report - {datetime.now().strftime('%Y-%m-%d')}",
                html_content=html_content
            )
            
        except Exception as e:
            self.logger.error(f"Error sending scheduled report email: {str(e)}")

"""
Smart Automation System for Inventory Management
Includes auto-purchase orders, supplier integration, and intelligent notifications
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy import func, and_, or_
from app import db
from models import Item, Sale, SaleItem, StockMovement, User, LocationStock

logger = logging.getLogger(__name__)

@dataclass
class PurchaseOrderRecommendation:
    """Data class for purchase order recommendations"""
    item_id: int
    item_name: str
    current_stock: int
    recommended_quantity: int
    urgency_level: str  # 'low', 'medium', 'high', 'critical'
    reason: str
    estimated_cost: float
    supplier_info: Optional[Dict] = None

@dataclass
class SmartNotification:
    """Data class for smart notifications"""
    notification_type: str
    title: str
    message: str
    priority: str  # 'low', 'medium', 'high', 'critical'
    action_required: bool
    related_items: List[int]
    metadata: Dict

class SmartAutomationEngine:
    """Advanced automation engine for inventory management"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.notifications = []
        
    def analyze_inventory_patterns(self) -> Dict:
        """Analyze sales patterns and inventory trends"""
        try:
            # Get sales data for the last 90 days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=90)
            
            # Calculate sales velocity for each item
            sales_data = db.session.query(
                SaleItem.item_id,
                Item.name,
                func.sum(SaleItem.quantity).label('total_sold'),
                func.count(SaleItem.id).label('sale_count'),
                func.avg(SaleItem.quantity).label('avg_quantity'),
                func.max(Sale.created_at).label('last_sale')
            ).join(Sale).join(Item).filter(
                Sale.user_id == self.user_id,
                Sale.created_at >= start_date
            ).group_by(SaleItem.item_id, Item.name).all()
            
            patterns = {}
            for item_data in sales_data:
                days_since_last_sale = (end_date - item_data.last_sale).days if item_data.last_sale else 999
                daily_velocity = item_data.total_sold / 90  # Average daily sales
                
                patterns[item_data.item_id] = {
                    'name': item_data.name,
                    'total_sold': item_data.total_sold,
                    'daily_velocity': daily_velocity,
                    'sale_frequency': item_data.sale_count,
                    'avg_quantity_per_sale': float(item_data.avg_quantity),
                    'days_since_last_sale': days_since_last_sale,
                    'trend': self._calculate_trend(item_data.item_id, start_date, end_date)
                }
                
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing inventory patterns: {str(e)}")
            return {}
    
    def _calculate_trend(self, item_id: int, start_date: datetime, end_date: datetime) -> str:
        """Calculate if item sales are trending up, down, or stable"""
        try:
            mid_date = start_date + (end_date - start_date) / 2
            
            # First half sales
            first_half = db.session.query(func.sum(SaleItem.quantity)).join(Sale).filter(
                SaleItem.item_id == item_id,
                Sale.user_id == self.user_id,
                Sale.created_at >= start_date,
                Sale.created_at < mid_date
            ).scalar() or 0
            
            # Second half sales
            second_half = db.session.query(func.sum(SaleItem.quantity)).join(Sale).filter(
                SaleItem.item_id == item_id,
                Sale.user_id == self.user_id,
                Sale.created_at >= mid_date,
                Sale.created_at <= end_date
            ).scalar() or 0
            
            if second_half > first_half * 1.2:
                return 'trending_up'
            elif second_half < first_half * 0.8:
                return 'trending_down'
            else:
                return 'stable'
                
        except Exception as e:
            logger.error(f"Error calculating trend for item {item_id}: {str(e)}")
            return 'unknown'
    
    def generate_auto_purchase_orders(self) -> List[PurchaseOrderRecommendation]:
        """Generate intelligent purchase order recommendations"""
        recommendations = []
        patterns = self.analyze_inventory_patterns()
        
        try:
            # Get current inventory levels
            items = db.session.query(Item).filter_by(user_id=self.user_id).all()
            
            for item in items:
                # Get total stock across all locations
                total_stock = db.session.query(func.sum(LocationStock.quantity)).filter(
                    LocationStock.item_id == item.id
                ).scalar() or 0
                
                # Get sales pattern for this item
                pattern = patterns.get(item.id, {})
                daily_velocity = pattern.get('daily_velocity', 0)
                trend = pattern.get('trend', 'unknown')
                
                # Calculate reorder point and quantity
                reorder_analysis = self._calculate_reorder_recommendation(
                    item, total_stock, daily_velocity, trend
                )
                
                if reorder_analysis['should_reorder']:
                    recommendation = PurchaseOrderRecommendation(
                        item_id=item.id,
                        item_name=item.name,
                        current_stock=total_stock,
                        recommended_quantity=reorder_analysis['quantity'],
                        urgency_level=reorder_analysis['urgency'],
                        reason=reorder_analysis['reason'],
                        estimated_cost=reorder_analysis['quantity'] * (getattr(item, 'cost_price', None) or 0),
                        supplier_info=self._get_supplier_info(item)
                    )
                    recommendations.append(recommendation)
                    
        except Exception as e:
            logger.error(f"Error generating purchase orders: {str(e)}")
            
        return recommendations
    
    def _calculate_reorder_recommendation(self, item: Item, current_stock: int, 
                                        daily_velocity: float, trend: str) -> Dict:
        """Calculate if item should be reordered and how much"""
        
        # Base reorder point (7 days of sales)
        base_reorder_point = daily_velocity * 7
        
        # Adjust based on trend
        trend_multiplier = {
            'trending_up': 1.5,
            'stable': 1.0,
            'trending_down': 0.7,
            'unknown': 1.0
        }.get(trend, 1.0)
        
        adjusted_reorder_point = base_reorder_point * trend_multiplier
        
        # Minimum stock level (item.minimum_stock or 5)
        min_stock = max(item.minimum_stock or 5, adjusted_reorder_point)
        
        # Calculate urgency
        if current_stock <= 0:
            urgency = 'critical'
            reason = 'Out of stock - immediate reorder required'
        elif current_stock <= min_stock * 0.5:
            urgency = 'high'
            reason = f'Stock critically low ({current_stock} units remaining)'
        elif current_stock <= min_stock:
            urgency = 'medium'
            reason = f'Stock below reorder point ({current_stock}/{int(min_stock)} units)'
        elif trend == 'trending_up' and current_stock <= min_stock * 1.5:
            urgency = 'low'
            reason = f'Trending item with moderate stock ({current_stock} units)'
        else:
            return {'should_reorder': False}
        
        # Calculate recommended quantity
        # Base: 30 days of sales, adjusted for trend
        base_quantity = max(10, daily_velocity * 30 * trend_multiplier)
        
        # Ensure we have at least minimum quantity
        recommended_quantity = max(base_quantity, min_stock * 2)
        
        return {
            'should_reorder': True,
            'quantity': int(recommended_quantity),
            'urgency': urgency,
            'reason': reason
        }
    
    def _get_supplier_info(self, item: Item) -> Dict:
        """Get supplier information for item (placeholder for real integration)"""
        # In a real implementation, this would connect to supplier APIs
        return {
            'supplier_name': f'Supplier for {item.category_id or "General"}',
            'lead_time_days': 7,
            'minimum_order_quantity': 10,
            'bulk_discount_available': True,
            'last_price_update': datetime.utcnow().isoformat()
        }
    
    def generate_smart_notifications(self) -> List[SmartNotification]:
        """Generate context-aware smart notifications"""
        notifications = []
        
        try:
            # Check for trending items with low stock
            trending_low_stock = self._check_trending_items_low_stock()
            notifications.extend(trending_low_stock)
            
            # Check for stagnant inventory
            stagnant_items = self._check_stagnant_inventory()
            notifications.extend(stagnant_items)
            
            # Check for pricing opportunities
            pricing_alerts = self._check_pricing_opportunities()
            notifications.extend(pricing_alerts)
            
            # Check for seasonal patterns
            seasonal_alerts = self._check_seasonal_patterns()
            notifications.extend(seasonal_alerts)
            
        except Exception as e:
            logger.error(f"Error generating smart notifications: {str(e)}")
            
        return notifications
    
    def _check_trending_items_low_stock(self) -> List[SmartNotification]:
        """Check for trending items that are running low on stock"""
        notifications = []
        patterns = self.analyze_inventory_patterns()
        
        for item_id, pattern in patterns.items():
            if pattern['trend'] == 'trending_up':
                item = Item.query.get(item_id)
                if item:
                    total_stock = db.session.query(func.sum(LocationStock.quantity)).filter(
                        LocationStock.item_id == item_id
                    ).scalar() or 0
                    
                    days_of_stock = total_stock / pattern['daily_velocity'] if pattern['daily_velocity'] > 0 else 999
                    
                    if days_of_stock < 14:  # Less than 2 weeks of stock
                        notifications.append(SmartNotification(
                            notification_type='trending_low_stock',
                            title='Trending Item Running Low',
                            message=f'{item.name} is trending up but only has {days_of_stock:.1f} days of stock remaining',
                            priority='high',
                            action_required=True,
                            related_items=[item_id],
                            metadata={
                                'current_stock': total_stock,
                                'daily_velocity': pattern['daily_velocity'],
                                'days_of_stock': days_of_stock
                            }
                        ))
        
        return notifications
    
    def _check_stagnant_inventory(self) -> List[SmartNotification]:
        """Check for items that haven't sold in a while"""
        notifications = []
        
        try:
            # Find items with no sales in the last 60 days
            cutoff_date = datetime.utcnow() - timedelta(days=60)
            
            stagnant_items = db.session.query(Item).filter(
                Item.user_id == self.user_id
            ).filter(
                ~Item.id.in_(
                    db.session.query(SaleItem.item_id).join(Sale).filter(
                        Sale.created_at >= cutoff_date,
                        Sale.user_id == self.user_id
                    )
                )
            ).limit(10).all()
            
            if stagnant_items:
                item_names = [item.name for item in stagnant_items[:5]]
                notifications.append(SmartNotification(
                    notification_type='stagnant_inventory',
                    title='Stagnant Inventory Alert',
                    message=f'{len(stagnant_items)} items have no sales in 60+ days: {", ".join(item_names)}{"..." if len(stagnant_items) > 5 else ""}',
                    priority='medium',
                    action_required=True,
                    related_items=[item.id for item in stagnant_items],
                    metadata={'days_without_sales': 60, 'total_items': len(stagnant_items)}
                ))
                
        except Exception as e:
            logger.error(f"Error checking stagnant inventory: {str(e)}")
            
        return notifications
    
    def _check_pricing_opportunities(self) -> List[SmartNotification]:
        """Check for pricing optimization opportunities"""
        notifications = []
        
        try:
            # Find high-velocity items with low margins
            patterns = self.analyze_inventory_patterns()
            
            for item_id, pattern in patterns.items():
                if pattern['daily_velocity'] > 1:  # Selling more than 1 per day
                    item = Item.query.get(item_id)
                    if item and item.cost_price and item.selling_price:
                        margin = (item.selling_price - item.cost_price) / item.selling_price
                        
                        if margin < 0.2:  # Less than 20% margin
                            notifications.append(SmartNotification(
                                notification_type='pricing_opportunity',
                                title='Low Margin High-Velocity Item',
                                message=f'{item.name} sells well but has only {margin:.1%} margin',
                                priority='medium',
                                action_required=False,
                                related_items=[item_id],
                                metadata={
                                    'current_margin': margin,
                                    'daily_velocity': pattern['daily_velocity'],
                                    'suggested_action': 'Consider price increase or cost reduction'
                                }
                            ))
                            
        except Exception as e:
            logger.error(f"Error checking pricing opportunities: {str(e)}")
            
        return notifications
    
    def _check_seasonal_patterns(self) -> List[SmartNotification]:
        """Check for seasonal patterns and prepare recommendations"""
        notifications = []
        
        try:
            current_month = datetime.utcnow().month
            
            # Simple seasonal logic (can be enhanced with ML)
            seasonal_items = {
                12: ['winter', 'holiday', 'christmas'],  # December
                1: ['winter', 'new year'],   # January
                2: ['valentine'],            # February
                3: ['spring'],               # March
                6: ['summer'],               # June
                10: ['halloween', 'fall'],   # October
                11: ['thanksgiving']         # November
            }
            
            if current_month in seasonal_items:
                keywords = seasonal_items[current_month]
                
                # Find items that might be seasonal
                seasonal_candidates = db.session.query(Item).filter(
                    Item.user_id == self.user_id,
                    or_(*[Item.name.ilike(f'%{keyword}%') for keyword in keywords])
                ).limit(5).all()
                
                if seasonal_candidates:
                    item_names = [item.name for item in seasonal_candidates]
                    notifications.append(SmartNotification(
                        notification_type='seasonal_reminder',
                        title='Seasonal Items Detected',
                        message=f'Consider promoting seasonal items: {", ".join(item_names)}',
                        priority='low',
                        action_required=False,
                        related_items=[item.id for item in seasonal_candidates],
                        metadata={'season': keywords[0], 'month': current_month}
                    ))
                    
        except Exception as e:
            logger.error(f"Error checking seasonal patterns: {str(e)}")
            
        return notifications
    
    def execute_automation_cycle(self) -> Dict:
        """Execute a complete automation cycle"""
        try:
            results = {
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': self.user_id,
                'purchase_orders': [],
                'notifications': [],
                'patterns_analyzed': 0,
                'errors': []
            }
            
            # Generate purchase order recommendations
            purchase_orders = self.generate_auto_purchase_orders()
            results['purchase_orders'] = [
                {
                    'item_name': po.item_name,
                    'current_stock': po.current_stock,
                    'recommended_quantity': po.recommended_quantity,
                    'urgency': po.urgency_level,
                    'reason': po.reason,
                    'estimated_cost': po.estimated_cost
                }
                for po in purchase_orders
            ]
            
            # Generate smart notifications
            notifications = self.generate_smart_notifications()
            results['notifications'] = [
                {
                    'type': notif.notification_type,
                    'title': notif.title,
                    'message': notif.message,
                    'priority': notif.priority,
                    'action_required': notif.action_required
                }
                for notif in notifications
            ]
            
            # Get pattern analysis count
            patterns = self.analyze_inventory_patterns()
            results['patterns_analyzed'] = len(patterns)
            
            logger.info(f"Automation cycle completed for user {self.user_id}: "
                       f"{len(purchase_orders)} purchase orders, "
                       f"{len(notifications)} notifications")
            
            return results
            
        except Exception as e:
            error_msg = f"Error in automation cycle: {str(e)}"
            logger.error(error_msg)
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': self.user_id,
                'error': error_msg,
                'purchase_orders': [],
                'notifications': []
            }

def run_automation_for_user(user_id: int) -> Dict:
    """Run automation cycle for a specific user"""
    engine = SmartAutomationEngine(user_id)
    return engine.execute_automation_cycle()

def run_automation_for_all_users() -> List[Dict]:
    """Run automation cycle for all users"""
    results = []
    
    try:
        users = User.query.all()
        for user in users:
            result = run_automation_for_user(user.id)
            results.append(result)
            
    except Exception as e:
        logger.error(f"Error running automation for all users: {str(e)}")
        
    return results
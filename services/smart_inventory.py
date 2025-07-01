
from datetime import datetime, timedelta
from models import db, Item, Sale, SaleItem
from services.predictive_analytics import PredictiveAnalyticsService
import logging

logger = logging.getLogger(__name__)

class SmartInventoryService:
    """Smart inventory management with AI-powered features"""
    
    def __init__(self, user_id=None):
        self.user_id = user_id
        self.analytics = PredictiveAnalyticsService(user_id)
    
    def auto_reorder_system(self, supplier_integration=False):
        """Automated reorder system with supplier integration"""
        try:
            # Get reorder suggestions from analytics
            suggestions_result = self.analytics.auto_reorder_suggestions()
            
            if not suggestions_result.get('success'):
                return suggestions_result
            
            suggestions = suggestions_result['reorder_suggestions']
            
            # Process high priority items for auto-ordering
            auto_orders = []
            manual_reviews = []
            
            for suggestion in suggestions:
                if suggestion['urgency_level'] in ['critical', 'high']:
                    if supplier_integration:
                        # Create automatic purchase order
                        auto_order = self._create_auto_purchase_order(suggestion)
                        auto_orders.append(auto_order)
                    else:
                        # Flag for manual review
                        manual_reviews.append(suggestion)
                else:
                    manual_reviews.append(suggestion)
            
            return {
                "success": True,
                "auto_orders_created": len(auto_orders),
                "manual_reviews_needed": len(manual_reviews),
                "auto_orders": auto_orders,
                "manual_reviews": manual_reviews,
                "total_estimated_cost": sum(order.get('total_cost', 0) for order in auto_orders)
            }
            
        except Exception as e:
            logger.error(f"Error in auto reorder system: {str(e)}")
            return {"error": str(e)}
    
    def dynamic_pricing_engine(self, market_data=None):
        """Dynamic pricing based on demand, supply, and market conditions"""
        try:
            items = Item.query.filter_by(is_active=True)
            
            if self.user_id:
                items = items.filter_by(user_id=self.user_id)
            
            items = items.all()
            pricing_updates = []
            
            for item in items:
                # Calculate dynamic pricing
                new_pricing = self._calculate_dynamic_pricing(item, market_data)
                
                if new_pricing['should_update']:
                    pricing_updates.append(new_pricing)
            
            return {
                "success": True,
                "pricing_updates": pricing_updates,
                "items_analyzed": len(items),
                "updates_recommended": len(pricing_updates)
            }
            
        except Exception as e:
            logger.error(f"Error in dynamic pricing: {str(e)}")
            return {"error": str(e)}
    
    def expiry_date_tracking(self):
        """Track expiry dates for perishable goods"""
        try:
            # Get items that might have expiry concerns
            items = Item.query.filter_by(is_active=True)
            
            if self.user_id:
                items = items.filter_by(user_id=self.user_id)
            
            # Filter for perishable categories
            perishable_categories = ['Grocery', 'Food', 'Dairy', 'Meat', 'Vegetables', 'Fruits']
            items = items.filter(Item.category.in_(perishable_categories)).all()
            
            expiry_alerts = []
            
            for item in items:
                # Calculate estimated shelf life based on category
                shelf_life_days = self._get_estimated_shelf_life(item.category)
                
                # Get purchase/restock dates (simplified - using creation date)
                estimated_expiry = item.created_at + timedelta(days=shelf_life_days)
                days_until_expiry = (estimated_expiry - datetime.utcnow()).days
                
                # Create alerts for items nearing expiry
                if days_until_expiry <= 7:
                    urgency = 'critical' if days_until_expiry <= 2 else 'high'
                    
                    expiry_alerts.append({
                        'item_id': item.id,
                        'name': item.name,
                        'category': item.category,
                        'current_stock': item.quantity,
                        'estimated_expiry_date': estimated_expiry.isoformat(),
                        'days_until_expiry': days_until_expiry,
                        'urgency': urgency,
                        'recommended_action': self._get_expiry_recommendation(item, days_until_expiry)
                    })
            
            return {
                "success": True,
                "expiry_alerts": expiry_alerts,
                "perishable_items_tracked": len(items),
                "critical_alerts": len([alert for alert in expiry_alerts if alert['urgency'] == 'critical'])
            }
            
        except Exception as e:
            logger.error(f"Error in expiry date tracking: {str(e)}")
            return {"error": str(e)}
    
    def abc_analysis(self):
        """ABC analysis for inventory categorization"""
        try:
            # Get sales data for the past 6 months
            six_months_ago = datetime.utcnow() - timedelta(days=180)
            
            # Calculate revenue contribution for each item
            revenue_analysis = db.session.query(
                Item.id,
                Item.name,
                Item.category,
                Item.quantity,
                Item.buying_price,
                func.sum(SaleItem.quantity * SaleItem.price).label('total_revenue'),
                func.sum(SaleItem.quantity).label('total_quantity_sold')
            ).outerjoin(SaleItem).outerjoin(Sale).filter(
                Item.is_active == True
            )
            
            if self.user_id:
                revenue_analysis = revenue_analysis.filter(Item.user_id == self.user_id)
            
            revenue_analysis = revenue_analysis.filter(
                db.or_(Sale.created_at >= six_months_ago, Sale.created_at.is_(None))
            ).group_by(Item.id, Item.name, Item.category, Item.quantity, Item.buying_price).all()
            
            # Calculate ABC classification
            abc_analysis = self._classify_abc_items(revenue_analysis)
            
            return {
                "success": True,
                "abc_analysis": abc_analysis,
                "total_items_analyzed": len(revenue_analysis),
                "analysis_period": "Last 6 months"
            }
            
        except Exception as e:
            logger.error(f"Error in ABC analysis: {str(e)}")
            return {"error": str(e)}
    
    def inventory_health_score(self):
        """Calculate overall inventory health score"""
        try:
            items = Item.query.filter_by(is_active=True)
            
            if self.user_id:
                items = items.filter_by(user_id=self.user_id)
            
            items = items.all()
            
            if not items:
                return {"error": "No items found for analysis"}
            
            health_metrics = {
                'total_items': len(items),
                'out_of_stock': 0,
                'low_stock': 0,
                'optimal_stock': 0,
                'overstock': 0,
                'total_value': 0,
                'slow_moving': 0,
                'fast_moving': 0
            }
            
            for item in items:
                # Stock level analysis
                if item.quantity <= 0:
                    health_metrics['out_of_stock'] += 1
                elif item.quantity <= (item.minimum_stock or 5):
                    health_metrics['low_stock'] += 1
                elif item.quantity <= (item.minimum_stock or 5) * 3:
                    health_metrics['optimal_stock'] += 1
                else:
                    health_metrics['overstock'] += 1
                
                # Value calculation
                health_metrics['total_value'] += (item.buying_price or 0) * item.quantity
                
                # Movement analysis (simplified)
                sales_velocity = self._calculate_sales_velocity(item.id)
                if sales_velocity < 0.1:  # Less than 0.1 units per day
                    health_metrics['slow_moving'] += 1
                elif sales_velocity > 1:  # More than 1 unit per day
                    health_metrics['fast_moving'] += 1
            
            # Calculate overall health score (0-100)
            health_score = self._calculate_health_score(health_metrics)
            
            return {
                "success": True,
                "health_score": health_score,
                "health_metrics": health_metrics,
                "recommendations": self._generate_health_recommendations(health_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error calculating inventory health score: {str(e)}")
            return {"error": str(e)}
    
    def _create_auto_purchase_order(self, suggestion):
        """Create automatic purchase order for critical items"""
        return {
            'item_id': suggestion['item_id'],
            'item_name': suggestion['name'],
            'suggested_quantity': suggestion['suggested_quantity'],
            'estimated_cost': suggestion['estimated_cost'],
            'urgency_level': suggestion['urgency_level'],
            'order_type': 'auto_generated',
            'created_at': datetime.utcnow().isoformat(),
            'status': 'pending_supplier_confirmation'
        }
    
    def _calculate_dynamic_pricing(self, item, market_data=None):
        """Calculate dynamic pricing for an item"""
        current_retail = item.selling_price_retail or 0
        current_wholesale = item.selling_price_wholesale or 0
        buying_price = item.buying_price or 0
        
        # Get sales velocity
        sales_velocity = self._calculate_sales_velocity(item.id)
        
        # Calculate demand factor
        if sales_velocity > 2:  # High demand
            demand_factor = 1.1
        elif sales_velocity > 1:  # Medium demand
            demand_factor = 1.05
        elif sales_velocity < 0.5:  # Low demand
            demand_factor = 0.95
        else:  # Normal demand
            demand_factor = 1.0
        
        # Calculate stock factor
        if item.quantity <= 5:  # Low stock
            stock_factor = 1.05
        elif item.quantity > 50:  # High stock
            stock_factor = 0.98
        else:  # Normal stock
            stock_factor = 1.0
        
        # Calculate new prices
        price_multiplier = demand_factor * stock_factor
        new_retail_price = current_retail * price_multiplier
        new_wholesale_price = current_wholesale * price_multiplier
        
        # Ensure minimum margin
        min_margin = 0.15  # 15% minimum margin
        min_retail_price = buying_price / (1 - min_margin)
        min_wholesale_price = buying_price / (1 - min_margin * 0.8)
        
        new_retail_price = max(new_retail_price, min_retail_price)
        new_wholesale_price = max(new_wholesale_price, min_wholesale_price)
        
        # Check if update is significant (more than 2% change)
        retail_change_percent = abs(new_retail_price - current_retail) / current_retail * 100 if current_retail > 0 else 0
        wholesale_change_percent = abs(new_wholesale_price - current_wholesale) / current_wholesale * 100 if current_wholesale > 0 else 0
        
        should_update = retail_change_percent > 2 or wholesale_change_percent > 2
        
        return {
            'item_id': item.id,
            'name': item.name,
            'current_retail_price': current_retail,
            'current_wholesale_price': current_wholesale,
            'new_retail_price': round(new_retail_price, 2),
            'new_wholesale_price': round(new_wholesale_price, 2),
            'sales_velocity': round(sales_velocity, 2),
            'demand_factor': demand_factor,
            'stock_factor': stock_factor,
            'should_update': should_update,
            'change_reason': self._get_price_change_reason(demand_factor, stock_factor, should_update)
        }
    
    def _calculate_sales_velocity(self, item_id):
        """Calculate sales velocity (units per day) for an item"""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        total_sold = db.session.query(
            func.sum(SaleItem.quantity)
        ).join(Sale).filter(
            SaleItem.item_id == item_id,
            Sale.created_at >= thirty_days_ago
        ).scalar() or 0
        
        return total_sold / 30
    
    def _get_estimated_shelf_life(self, category):
        """Get estimated shelf life in days based on category"""
        shelf_life_map = {
            'Dairy': 7,
            'Meat': 5,
            'Vegetables': 10,
            'Fruits': 7,
            'Bread': 3,
            'Grocery': 30,
            'Food': 14
        }
        return shelf_life_map.get(category, 30)  # Default 30 days
    
    def _get_expiry_recommendation(self, item, days_until_expiry):
        """Get recommendation for items nearing expiry"""
        if days_until_expiry <= 1:
            return "Immediate clearance sale or donation required"
        elif days_until_expiry <= 3:
            return "Apply 30-50% discount for quick sale"
        elif days_until_expiry <= 7:
            return "Apply 15-25% discount to increase sales velocity"
        else:
            return "Monitor closely and consider promotional activities"
    
    def _classify_abc_items(self, revenue_data):
        """Classify items using ABC analysis"""
        # Calculate total revenue
        total_revenue = sum(item.total_revenue or 0 for item in revenue_data)
        
        # Sort by revenue contribution
        sorted_items = sorted(revenue_data, key=lambda x: x.total_revenue or 0, reverse=True)
        
        abc_analysis = []
        cumulative_revenue = 0
        
        for i, item in enumerate(sorted_items):
            item_revenue = item.total_revenue or 0
            cumulative_revenue += item_revenue
            cumulative_percentage = (cumulative_revenue / total_revenue * 100) if total_revenue > 0 else 0
            
            # ABC Classification
            if cumulative_percentage <= 80:
                classification = 'A'
                priority = 'High'
            elif cumulative_percentage <= 95:
                classification = 'B'
                priority = 'Medium'
            else:
                classification = 'C'
                priority = 'Low'
            
            abc_analysis.append({
                'item_id': item.id,
                'name': item.name,
                'category': item.category,
                'current_stock': item.quantity,
                'buying_price': item.buying_price or 0,
                'total_revenue': item_revenue,
                'total_quantity_sold': item.total_quantity_sold or 0,
                'revenue_percentage': round((item_revenue / total_revenue * 100) if total_revenue > 0 else 0, 2),
                'cumulative_percentage': round(cumulative_percentage, 2),
                'abc_classification': classification,
                'priority': priority,
                'management_focus': self._get_abc_management_focus(classification)
            })
        
        return abc_analysis
    
    def _get_abc_management_focus(self, classification):
        """Get management focus recommendations based on ABC classification"""
        focus_map = {
            'A': 'Tight inventory control, frequent review, accurate demand forecasting',
            'B': 'Regular monitoring, periodic review, standard control procedures',
            'C': 'Simple control systems, bulk ordering, minimal monitoring'
        }
        return focus_map.get(classification, 'Standard management')
    
    def _calculate_health_score(self, metrics):
        """Calculate overall inventory health score"""
        total_items = metrics['total_items']
        
        if total_items == 0:
            return 0
        
        # Scoring factors
        stock_score = ((metrics['optimal_stock'] / total_items) * 40 + 
                      (1 - metrics['out_of_stock'] / total_items) * 30 +
                      (1 - metrics['overstock'] / total_items) * 10)
        
        movement_score = ((metrics['fast_moving'] / total_items) * 15 +
                         (1 - metrics['slow_moving'] / total_items) * 5)
        
        total_score = min(100, max(0, stock_score + movement_score))
        return round(total_score, 1)
    
    def _generate_health_recommendations(self, metrics):
        """Generate recommendations based on health metrics"""
        recommendations = []
        
        if metrics['out_of_stock'] > 0:
            recommendations.append(f"Urgent: {metrics['out_of_stock']} items are out of stock. Reorder immediately.")
        
        if metrics['low_stock'] > 0:
            recommendations.append(f"Warning: {metrics['low_stock']} items are low on stock. Consider reordering.")
        
        if metrics['overstock'] > 0:
            recommendations.append(f"Note: {metrics['overstock']} items may be overstocked. Consider promotional activities.")
        
        if metrics['slow_moving'] > 0:
            recommendations.append(f"Review: {metrics['slow_moving']} items are slow-moving. Consider discounts or discontinuation.")
        
        return recommendations
    
    def _get_price_change_reason(self, demand_factor, stock_factor, should_update):
        """Get reason for price change"""
        if not should_update:
            return "No significant change needed"
        
        reasons = []
        
        if demand_factor > 1.05:
            reasons.append("High demand detected")
        elif demand_factor < 0.95:
            reasons.append("Low demand, price reduction recommended")
        
        if stock_factor > 1.02:
            reasons.append("Low stock levels")
        elif stock_factor < 0.99:
            reasons.append("High stock levels")
        
        return "; ".join(reasons) if reasons else "Market optimization"

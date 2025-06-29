
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from models import db, Item, Sale, SaleItem, FinancialTransaction
import logging

logger = logging.getLogger(__name__)

class PredictiveAnalyticsService:
    """AI-powered predictive analytics for inventory management"""
    
    def __init__(self, user_id=None):
        self.user_id = user_id
        
    def demand_forecasting(self, item_id=None, days_ahead=30):
        """Generate demand forecast for items using historical sales data"""
        try:
            # Get historical sales data
            sales_data = self._get_historical_sales_data(item_id, days_back=90)
            
            if not sales_data:
                return {"error": "Insufficient historical data for forecasting"}
            
            forecasts = []
            
            for item_data in sales_data:
                # Simple moving average with trend analysis
                forecast = self._calculate_demand_forecast(item_data, days_ahead)
                forecasts.append(forecast)
            
            return {
                "success": True,
                "forecasts": forecasts,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in demand forecasting: {str(e)}")
            return {"error": str(e)}
    
    def seasonal_trend_analysis(self, item_id=None):
        """Analyze seasonal trends in sales data"""
        try:
            # Get sales data for the past year
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=365)
            
            query = db.session.query(
                SaleItem.item_id,
                Item.name,
                func.extract('month', Sale.created_at).label('month'),
                func.sum(SaleItem.quantity).label('total_quantity'),
                func.count(SaleItem.id).label('transaction_count')
            ).join(Sale).join(Item).filter(
                Sale.created_at >= start_date,
                Sale.created_at <= end_date
            )
            
            if item_id:
                query = query.filter(SaleItem.item_id == item_id)
            
            if self.user_id:
                query = query.filter(Sale.user_id == self.user_id)
            
            results = query.group_by(
                SaleItem.item_id, Item.name, func.extract('month', Sale.created_at)
            ).all()
            
            # Process seasonal patterns
            seasonal_analysis = self._process_seasonal_data(results)
            
            return {
                "success": True,
                "seasonal_patterns": seasonal_analysis,
                "analysis_period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            }
            
        except Exception as e:
            logger.error(f"Error in seasonal trend analysis: {str(e)}")
            return {"error": str(e)}
    
    def price_optimization_recommendations(self, item_id=None):
        """Generate price optimization recommendations"""
        try:
            # Get current pricing and sales data
            items_query = Item.query.filter_by(is_active=True)
            
            if item_id:
                items_query = items_query.filter_by(id=item_id)
            
            if self.user_id:
                items_query = items_query.filter_by(user_id=self.user_id)
            
            items = items_query.all()
            recommendations = []
            
            for item in items:
                # Calculate current metrics
                current_metrics = self._calculate_item_metrics(item)
                
                # Generate price recommendations
                price_rec = self._generate_price_recommendations(item, current_metrics)
                recommendations.append(price_rec)
            
            return {
                "success": True,
                "recommendations": recommendations,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in price optimization: {str(e)}")
            return {"error": str(e)}
    
    def customer_behavior_analytics(self):
        """Analyze customer purchasing patterns"""
        try:
            # Get customer purchase data
            customer_data = db.session.query(
                Sale.customer_name,
                Sale.customer_phone,
                func.count(Sale.id).label('purchase_count'),
                func.sum(Sale.total_amount).label('total_spent'),
                func.avg(Sale.total_amount).label('avg_order_value'),
                func.max(Sale.created_at).label('last_purchase'),
                func.min(Sale.created_at).label('first_purchase')
            ).filter(Sale.customer_name.isnot(None))
            
            if self.user_id:
                customer_data = customer_data.filter(Sale.user_id == self.user_id)
            
            results = customer_data.group_by(
                Sale.customer_name, Sale.customer_phone
            ).having(func.count(Sale.id) > 1).all()
            
            # Analyze customer segments
            segments = self._analyze_customer_segments(results)
            
            return {
                "success": True,
                "customer_segments": segments,
                "total_customers_analyzed": len(results)
            }
            
        except Exception as e:
            logger.error(f"Error in customer behavior analytics: {str(e)}")
            return {"error": str(e)}
    
    def auto_reorder_suggestions(self):
        """Generate automatic reorder suggestions"""
        try:
            items = Item.query.filter_by(is_active=True)
            
            if self.user_id:
                items = items.filter_by(user_id=self.user_id)
            
            items = items.all()
            suggestions = []
            
            for item in items:
                # Calculate reorder metrics
                suggestion = self._calculate_reorder_suggestion(item)
                if suggestion:
                    suggestions.append(suggestion)
            
            # Sort by urgency
            suggestions.sort(key=lambda x: x['urgency_score'], reverse=True)
            
            return {
                "success": True,
                "reorder_suggestions": suggestions,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating reorder suggestions: {str(e)}")
            return {"error": str(e)}
    
    def _get_historical_sales_data(self, item_id=None, days_back=90):
        """Get historical sales data for analysis"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        query = db.session.query(
            SaleItem.item_id,
            Item.name,
            func.date(Sale.created_at).label('sale_date'),
            func.sum(SaleItem.quantity).label('daily_quantity')
        ).join(Sale).join(Item).filter(
            Sale.created_at >= start_date,
            Sale.created_at <= end_date
        )
        
        if item_id:
            query = query.filter(SaleItem.item_id == item_id)
        
        if self.user_id:
            query = query.filter(Sale.user_id == self.user_id)
        
        results = query.group_by(
            SaleItem.item_id, Item.name, func.date(Sale.created_at)
        ).all()
        
        # Group by item
        items_data = {}
        for result in results:
            if result.item_id not in items_data:
                items_data[result.item_id] = {
                    'item_id': result.item_id,
                    'name': result.name,
                    'daily_sales': []
                }
            items_data[result.item_id]['daily_sales'].append({
                'date': result.sale_date.isoformat(),
                'quantity': result.daily_quantity
            })
        
        return list(items_data.values())
    
    def _calculate_demand_forecast(self, item_data, days_ahead):
        """Calculate demand forecast using moving average and trend"""
        daily_sales = item_data['daily_sales']
        
        if len(daily_sales) < 7:
            return {
                'item_id': item_data['item_id'],
                'name': item_data['name'],
                'forecast': 0,
                'confidence': 'low',
                'method': 'insufficient_data'
            }
        
        # Calculate moving averages
        quantities = [sale['quantity'] for sale in daily_sales]
        recent_avg = np.mean(quantities[-7:])  # Last 7 days
        overall_avg = np.mean(quantities)
        
        # Simple trend calculation
        if len(quantities) >= 14:
            first_half_avg = np.mean(quantities[:len(quantities)//2])
            second_half_avg = np.mean(quantities[len(quantities)//2:])
            trend_factor = second_half_avg / first_half_avg if first_half_avg > 0 else 1
        else:
            trend_factor = 1
        
        # Forecast calculation
        base_forecast = recent_avg * days_ahead
        trending_forecast = base_forecast * trend_factor
        
        # Confidence calculation
        variance = np.var(quantities)
        confidence = 'high' if variance < recent_avg else 'medium' if variance < recent_avg * 2 else 'low'
        
        return {
            'item_id': item_data['item_id'],
            'name': item_data['name'],
            'forecast': max(0, int(trending_forecast)),
            'daily_average': round(recent_avg, 2),
            'trend_factor': round(trend_factor, 2),
            'confidence': confidence,
            'method': 'moving_average_with_trend'
        }
    
    def _process_seasonal_data(self, results):
        """Process seasonal trend data"""
        seasonal_patterns = {}
        
        for result in results:
            item_id = result.item_id
            if item_id not in seasonal_patterns:
                seasonal_patterns[item_id] = {
                    'item_id': item_id,
                    'name': result.name,
                    'monthly_data': {},
                    'peak_months': [],
                    'low_months': []
                }
            
            month = int(result.month)
            seasonal_patterns[item_id]['monthly_data'][month] = {
                'total_quantity': result.total_quantity,
                'transaction_count': result.transaction_count
            }
        
        # Identify peak and low months for each item
        for item_id, data in seasonal_patterns.items():
            monthly_quantities = [(month, data['total_quantity']) 
                                for month, data in data['monthly_data'].items()]
            
            if monthly_quantities:
                monthly_quantities.sort(key=lambda x: x[1], reverse=True)
                data['peak_months'] = [month for month, _ in monthly_quantities[:3]]
                data['low_months'] = [month for month, _ in monthly_quantities[-3:]]
        
        return list(seasonal_patterns.values())
    
    def _calculate_item_metrics(self, item):
        """Calculate current metrics for an item"""
        # Get sales data for the item
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        sales_data = db.session.query(
            func.sum(SaleItem.quantity).label('total_sold'),
            func.count(SaleItem.id).label('transaction_count'),
            func.avg(SaleItem.price).label('avg_selling_price')
        ).join(Sale).filter(
            SaleItem.item_id == item.id,
            Sale.created_at >= thirty_days_ago
        ).first()
        
        return {
            'current_stock': item.quantity,
            'buying_price': item.buying_price or 0,
            'retail_price': item.selling_price_retail or 0,
            'wholesale_price': item.selling_price_wholesale or 0,
            'total_sold_30d': sales_data.total_sold or 0,
            'transaction_count_30d': sales_data.transaction_count or 0,
            'avg_selling_price_30d': sales_data.avg_selling_price or 0
        }
    
    def _generate_price_recommendations(self, item, metrics):
        """Generate price optimization recommendations"""
        current_margin = ((metrics['retail_price'] - metrics['buying_price']) / 
                         metrics['retail_price'] * 100) if metrics['retail_price'] > 0 else 0
        
        # Simple recommendations based on sales velocity and margin
        recommendations = []
        
        # Low sales, high margin - consider price reduction
        if metrics['total_sold_30d'] < 5 and current_margin > 40:
            recommended_price = metrics['retail_price'] * 0.9
            recommendations.append({
                'type': 'price_reduction',
                'current_price': metrics['retail_price'],
                'recommended_price': round(recommended_price, 2),
                'reason': 'Low sales volume with high margin - consider price reduction to increase sales',
                'expected_impact': 'Increased sales volume'
            })
        
        # High sales, low margin - consider price increase
        elif metrics['total_sold_30d'] > 15 and current_margin < 20:
            recommended_price = metrics['retail_price'] * 1.1
            recommendations.append({
                'type': 'price_increase',
                'current_price': metrics['retail_price'],
                'recommended_price': round(recommended_price, 2),
                'reason': 'High sales volume with low margin - consider price increase',
                'expected_impact': 'Improved profit margins'
            })
        
        return {
            'item_id': item.id,
            'name': item.name,
            'current_metrics': metrics,
            'current_margin': round(current_margin, 2),
            'recommendations': recommendations
        }
    
    def _analyze_customer_segments(self, customer_data):
        """Analyze and segment customers"""
        if not customer_data:
            return []
        
        # Calculate quartiles for segmentation
        total_spent_values = [customer.total_spent for customer in customer_data]
        purchase_count_values = [customer.purchase_count for customer in customer_data]
        
        spent_q1 = np.percentile(total_spent_values, 25)
        spent_q3 = np.percentile(total_spent_values, 75)
        count_q1 = np.percentile(purchase_count_values, 25)
        count_q3 = np.percentile(purchase_count_values, 75)
        
        segments = {
            'high_value': [],
            'frequent_buyers': [],
            'new_customers': [],
            'at_risk': []
        }
        
        for customer in customer_data:
            # Calculate days since last purchase
            days_since_last = (datetime.utcnow() - customer.last_purchase).days
            
            # Segment classification
            if customer.total_spent >= spent_q3 and customer.purchase_count >= count_q3:
                segments['high_value'].append({
                    'name': customer.customer_name,
                    'phone': customer.customer_phone,
                    'total_spent': customer.total_spent,
                    'purchase_count': customer.purchase_count,
                    'avg_order_value': customer.avg_order_value,
                    'days_since_last_purchase': days_since_last
                })
            elif customer.purchase_count >= count_q3:
                segments['frequent_buyers'].append({
                    'name': customer.customer_name,
                    'phone': customer.customer_phone,
                    'total_spent': customer.total_spent,
                    'purchase_count': customer.purchase_count,
                    'avg_order_value': customer.avg_order_value,
                    'days_since_last_purchase': days_since_last
                })
            elif days_since_last <= 30:
                segments['new_customers'].append({
                    'name': customer.customer_name,
                    'phone': customer.customer_phone,
                    'total_spent': customer.total_spent,
                    'purchase_count': customer.purchase_count,
                    'avg_order_value': customer.avg_order_value,
                    'days_since_last_purchase': days_since_last
                })
            elif days_since_last > 60:
                segments['at_risk'].append({
                    'name': customer.customer_name,
                    'phone': customer.customer_phone,
                    'total_spent': customer.total_spent,
                    'purchase_count': customer.purchase_count,
                    'avg_order_value': customer.avg_order_value,
                    'days_since_last_purchase': days_since_last
                })
        
        return segments
    
    def _calculate_reorder_suggestion(self, item):
        """Calculate reorder suggestion for an item"""
        # Get sales velocity (average daily sales)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        sales_data = db.session.query(
            func.sum(SaleItem.quantity).label('total_sold')
        ).join(Sale).filter(
            SaleItem.item_id == item.id,
            Sale.created_at >= thirty_days_ago
        ).first()
        
        total_sold = sales_data.total_sold or 0
        daily_sales_rate = total_sold / 30 if total_sold > 0 else 0
        
        current_stock = item.quantity
        minimum_stock = item.minimum_stock or 5
        
        # Calculate days until stockout
        days_until_stockout = (current_stock / daily_sales_rate) if daily_sales_rate > 0 else float('inf')
        
        # Determine urgency
        urgency_score = 0
        urgency_level = 'low'
        
        if current_stock <= minimum_stock:
            urgency_score = 100
            urgency_level = 'critical'
        elif days_until_stockout <= 7:
            urgency_score = 80
            urgency_level = 'high'
        elif days_until_stockout <= 14:
            urgency_score = 60
            urgency_level = 'medium'
        elif days_until_stockout <= 30:
            urgency_score = 40
            urgency_level = 'low'
        
        # Only suggest reorder if urgency is medium or higher
        if urgency_score >= 40:
            # Calculate suggested order quantity (30 days supply + buffer)
            suggested_quantity = int(daily_sales_rate * 30 * 1.2) if daily_sales_rate > 0 else minimum_stock * 2
            
            return {
                'item_id': item.id,
                'name': item.name,
                'current_stock': current_stock,
                'minimum_stock': minimum_stock,
                'daily_sales_rate': round(daily_sales_rate, 2),
                'days_until_stockout': round(days_until_stockout, 1) if days_until_stockout != float('inf') else None,
                'suggested_quantity': suggested_quantity,
                'urgency_level': urgency_level,
                'urgency_score': urgency_score,
                'estimated_cost': suggested_quantity * (item.buying_price or 0)
            }
        
        return None

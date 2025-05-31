
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import func
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class PredictiveStockManager:
    """AI-powered demand forecasting and stock management"""
    
    def __init__(self, db, Item, Sale, SaleItem):
        self.db = db
        self.Item = Item
        self.Sale = Sale
        self.SaleItem = SaleItem
    
    def get_sales_history(self, item_id: int, days: int = 365) -> pd.DataFrame:
        """Get sales history for an item"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        sales_data = self.db.session.query(
            self.Sale.created_at,
            self.SaleItem.quantity,
            self.SaleItem.total
        ).join(
            self.SaleItem
        ).filter(
            self.SaleItem.item_id == item_id,
            self.Sale.created_at >= cutoff_date
        ).all()
        
        if not sales_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(sales_data, columns=['date', 'quantity', 'total'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        # Resample to daily data
        daily_sales = df.resample('D').agg({
            'quantity': 'sum',
            'total': 'sum'
        }).fillna(0)
        
        return daily_sales
    
    def calculate_moving_averages(self, sales_data: pd.DataFrame, windows: List[int] = [7, 14, 30]) -> Dict:
        """Calculate moving averages for demand forecasting"""
        if sales_data.empty:
            return {f'ma_{w}': 0 for w in windows}
        
        moving_averages = {}
        for window in windows:
            if len(sales_data) >= window:
                moving_averages[f'ma_{window}'] = sales_data['quantity'].rolling(window=window).mean().iloc[-1]
            else:
                moving_averages[f'ma_{window}'] = sales_data['quantity'].mean()
        
        return moving_averages
    
    def detect_seasonal_trends(self, sales_data: pd.DataFrame) -> Dict:
        """Detect seasonal patterns in sales data"""
        if sales_data.empty or len(sales_data) < 30:
            return {'seasonal_factor': 1.0, 'trend': 'insufficient_data'}
        
        # Group by day of week and month
        sales_data['day_of_week'] = sales_data.index.dayofweek
        sales_data['month'] = sales_data.index.month
        
        # Calculate average sales by day of week and month
        weekly_pattern = sales_data.groupby('day_of_week')['quantity'].mean()
        monthly_pattern = sales_data.groupby('month')['quantity'].mean()
        
        # Calculate current seasonal factors
        current_day = datetime.now().weekday()
        current_month = datetime.now().month
        
        weekly_factor = weekly_pattern.get(current_day, 1.0) / weekly_pattern.mean() if weekly_pattern.mean() > 0 else 1.0
        monthly_factor = monthly_pattern.get(current_month, 1.0) / monthly_pattern.mean() if monthly_pattern.mean() > 0 else 1.0
        
        # Determine trend
        recent_avg = sales_data['quantity'].tail(30).mean()
        older_avg = sales_data['quantity'].head(30).mean()
        
        if recent_avg > older_avg * 1.1:
            trend = 'increasing'
        elif recent_avg < older_avg * 0.9:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'seasonal_factor': (weekly_factor + monthly_factor) / 2,
            'trend': trend,
            'weekly_factor': weekly_factor,
            'monthly_factor': monthly_factor
        }
    
    def forecast_demand(self, item_id: int, forecast_days: int = 30) -> Dict:
        """Forecast demand for an item"""
        try:
            item = self.Item.query.get(item_id)
            if not item:
                return {'error': 'Item not found'}
            
            sales_history = self.get_sales_history(item_id)
            
            if sales_history.empty:
                return {
                    'item_id': item_id,
                    'item_name': item.name,
                    'forecast_method': 'no_history',
                    'daily_forecast': 0,
                    'period_forecast': 0,
                    'confidence': 'low'
                }
            
            # Calculate moving averages
            moving_averages = self.calculate_moving_averages(sales_history)
            
            # Detect seasonal trends
            seasonal_data = self.detect_seasonal_trends(sales_history)
            
            # Simple forecasting using weighted moving average
            if moving_averages['ma_7'] > 0:
                base_forecast = (
                    moving_averages['ma_7'] * 0.5 +
                    moving_averages['ma_14'] * 0.3 +
                    moving_averages['ma_30'] * 0.2
                )
            else:
                base_forecast = sales_history['quantity'].mean()
            
            # Apply seasonal adjustment
            adjusted_forecast = base_forecast * seasonal_data['seasonal_factor']
            
            # Apply trend adjustment
            if seasonal_data['trend'] == 'increasing':
                adjusted_forecast *= 1.1
            elif seasonal_data['trend'] == 'decreasing':
                adjusted_forecast *= 0.9
            
            period_forecast = adjusted_forecast * forecast_days
            
            # Determine confidence level
            variance = sales_history['quantity'].var()
            if variance < base_forecast * 0.5:
                confidence = 'high'
            elif variance < base_forecast * 1.5:
                confidence = 'medium'
            else:
                confidence = 'low'
            
            return {
                'item_id': item_id,
                'item_name': item.name,
                'current_stock': item.quantity,
                'daily_forecast': round(adjusted_forecast, 2),
                'period_forecast': round(period_forecast, 2),
                'confidence': confidence,
                'seasonal_data': seasonal_data,
                'moving_averages': moving_averages,
                'forecast_method': 'weighted_moving_average'
            }
            
        except Exception as e:
            logger.error(f"Error forecasting demand for item {item_id}: {str(e)}")
            return {'error': str(e)}
    
    def calculate_reorder_point(self, item_id: int, lead_time_days: int = 7, service_level: float = 0.95) -> Dict:
        """Calculate optimal reorder point"""
        try:
            forecast_data = self.forecast_demand(item_id, lead_time_days * 2)
            
            if 'error' in forecast_data:
                return forecast_data
            
            # Basic reorder point calculation
            average_demand = forecast_data['daily_forecast']
            lead_time_demand = average_demand * lead_time_days
            
            # Safety stock calculation (simplified)
            sales_history = self.get_sales_history(item_id, 90)
            
            if not sales_history.empty:
                demand_std = sales_history['quantity'].std()
                # Z-score for 95% service level ≈ 1.65
                z_score = 1.65 if service_level >= 0.95 else 1.28
                safety_stock = z_score * demand_std * np.sqrt(lead_time_days)
            else:
                safety_stock = lead_time_demand * 0.3  # 30% safety buffer
            
            reorder_point = lead_time_demand + safety_stock
            
            return {
                'item_id': item_id,
                'item_name': forecast_data['item_name'],
                'current_stock': forecast_data['current_stock'],
                'reorder_point': round(reorder_point, 0),
                'lead_time_demand': round(lead_time_demand, 2),
                'safety_stock': round(safety_stock, 2),
                'recommendation': 'reorder_now' if forecast_data['current_stock'] <= reorder_point else 'stock_ok'
            }
            
        except Exception as e:
            logger.error(f"Error calculating reorder point for item {item_id}: {str(e)}")
            return {'error': str(e)}
    
    def get_purchase_recommendations(self, user_id: int) -> List[Dict]:
        """Get smart purchase recommendations for all items"""
        try:
            items = self.Item.query.filter_by(user_id=user_id).all()
            recommendations = []
            
            for item in items:
                reorder_data = self.calculate_reorder_point(item.id)
                
                if 'error' not in reorder_data:
                    if reorder_data['recommendation'] == 'reorder_now':
                        # Calculate suggested order quantity (Economic Order Quantity simplified)
                        forecast_data = self.forecast_demand(item.id, 30)
                        monthly_demand = forecast_data.get('period_forecast', 0)
                        
                        # Simple EOQ: order for 1-2 months of demand
                        suggested_quantity = max(monthly_demand, reorder_data['reorder_point'] * 2)
                        
                        recommendations.append({
                            'item_id': item.id,
                            'item_name': item.name,
                            'current_stock': item.quantity,
                            'reorder_point': reorder_data['reorder_point'],
                            'suggested_quantity': round(suggested_quantity, 0),
                            'estimated_cost': suggested_quantity * (item.buying_price or 0),
                            'priority': 'high' if item.quantity == 0 else 'medium',
                            'forecast_confidence': forecast_data.get('confidence', 'unknown')
                        })
            
            # Sort by priority and current stock level
            recommendations.sort(key=lambda x: (x['priority'] == 'high', -x['current_stock']))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting purchase recommendations: {str(e)}")
            return []

def analyze_abc_classification(db, Item, Sale, SaleItem, user_id: int) -> Dict:
    """Perform ABC analysis on inventory items"""
    try:
        # Get items with sales data for the last 12 months
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        
        item_sales = db.session.query(
            Item.id,
            Item.name,
            Item.quantity,
            Item.selling_price_retail,
            func.sum(SaleItem.quantity).label('total_sold'),
            func.sum(SaleItem.total).label('total_revenue')
        ).outerjoin(
            SaleItem, Item.id == SaleItem.item_id
        ).outerjoin(
            Sale, SaleItem.sale_id == Sale.id
        ).filter(
            Item.user_id == user_id,
            Sale.created_at >= cutoff_date
        ).group_by(Item.id).all()
        
        if not item_sales:
            return {'error': 'No sales data found'}
        
        # Calculate annual revenue for each item
        items_data = []
        total_revenue = 0
        
        for item in item_sales:
            revenue = item.total_revenue or 0
            total_revenue += revenue
            
            items_data.append({
                'id': item.id,
                'name': item.name,
                'quantity': item.quantity,
                'price': item.selling_price_retail or 0,
                'units_sold': item.total_sold or 0,
                'revenue': revenue
            })
        
        # Sort by revenue (descending)
        items_data.sort(key=lambda x: x['revenue'], reverse=True)
        
        # Calculate cumulative percentages and assign ABC classification
        cumulative_revenue = 0
        for i, item in enumerate(items_data):
            cumulative_revenue += item['revenue']
            cumulative_percentage = (cumulative_revenue / total_revenue) * 100 if total_revenue > 0 else 0
            
            # ABC Classification
            if cumulative_percentage <= 80:
                classification = 'A'
            elif cumulative_percentage <= 95:
                classification = 'B'
            else:
                classification = 'C'
            
            item['classification'] = classification
            item['cumulative_percentage'] = round(cumulative_percentage, 2)
        
        # Group by classification
        abc_summary = {'A': [], 'B': [], 'C': []}
        for item in items_data:
            abc_summary[item['classification']].append(item)
        
        return {
            'total_items': len(items_data),
            'total_revenue': total_revenue,
            'classifications': abc_summary,
            'summary': {
                'A_count': len(abc_summary['A']),
                'B_count': len(abc_summary['B']),
                'C_count': len(abc_summary['C'])
            }
        }
        
    except Exception as e:
        logger.error(f"Error performing ABC analysis: {str(e)}")
        return {'error': str(e)}

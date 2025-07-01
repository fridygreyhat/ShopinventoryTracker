
from datetime import datetime, timedelta
from models import db, Customer, Sale, User
import logging

logger = logging.getLogger(__name__)

class CustomerLoyaltyService:
    """Customer loyalty program with points system"""
    
    def __init__(self, user_id=None):
        self.user_id = user_id
        self.points_per_currency = 1  # 1 point per TZS spent
        self.redemption_rate = 100  # 100 points = 1 TZS discount
    
    def calculate_customer_points(self, customer_id):
        """Calculate total points for a customer"""
        try:
            # Get all sales for this customer
            sales = Sale.query.filter_by(customer_id=customer_id)
            
            if self.user_id:
                sales = sales.filter_by(user_id=self.user_id)
            
            sales = sales.all()
            
            total_spent = sum(sale.total_amount for sale in sales)
            total_points = int(total_spent * self.points_per_currency)
            
            # Calculate redeemed points (if tracking redemptions)
            # For now, assume no redemptions
            available_points = total_points
            
            return {
                "customer_id": customer_id,
                "total_points": total_points,
                "available_points": available_points,
                "total_spent": total_spent,
                "total_purchases": len(sales),
                "loyalty_tier": self._calculate_loyalty_tier(total_spent, len(sales))
            }
            
        except Exception as e:
            logger.error(f"Error calculating customer points: {str(e)}")
            return {"error": str(e)}
    
    def get_loyalty_dashboard(self):
        """Get loyalty program dashboard data"""
        try:
            # Get all customers with purchase history
            customers_query = db.session.query(
                Sale.customer_name,
                Sale.customer_phone,
                func.sum(Sale.total_amount).label('total_spent'),
                func.count(Sale.id).label('purchase_count'),
                func.max(Sale.created_at).label('last_purchase')
            ).filter(Sale.customer_name.isnot(None))
            
            if self.user_id:
                customers_query = customers_query.filter(Sale.user_id == self.user_id)
            
            customers = customers_query.group_by(
                Sale.customer_name, Sale.customer_phone
            ).all()
            
            loyalty_data = []
            
            for customer in customers:
                points_data = {
                    "name": customer.customer_name,
                    "phone": customer.customer_phone,
                    "total_spent": customer.total_spent,
                    "purchase_count": customer.purchase_count,
                    "last_purchase": customer.last_purchase,
                    "total_points": int(customer.total_spent * self.points_per_currency),
                    "available_points": int(customer.total_spent * self.points_per_currency),
                    "loyalty_tier": self._calculate_loyalty_tier(customer.total_spent, customer.purchase_count),
                    "next_tier_requirement": self._get_next_tier_requirement(customer.total_spent, customer.purchase_count)
                }
                loyalty_data.append(points_data)
            
            # Sort by total points
            loyalty_data.sort(key=lambda x: x['total_points'], reverse=True)
            
            return {
                "success": True,
                "customers": loyalty_data,
                "total_customers": len(loyalty_data),
                "program_stats": self._calculate_program_stats(loyalty_data)
            }
            
        except Exception as e:
            logger.error(f"Error getting loyalty dashboard: {str(e)}")
            return {"error": str(e)}
    
    def credit_scoring(self, customer_id):
        """Calculate credit score for installment customers"""
        try:
            # Get customer purchase history
            sales = Sale.query.filter_by(customer_id=customer_id)
            
            if self.user_id:
                sales = sales.filter_by(user_id=self.user_id)
            
            sales = sales.all()
            
            if not sales:
                return {
                    "customer_id": customer_id,
                    "credit_score": 0,
                    "risk_level": "unknown",
                    "recommended_credit_limit": 0
                }
            
            # Calculate credit score factors
            total_spent = sum(sale.total_amount for sale in sales)
            purchase_count = len(sales)
            avg_order_value = total_spent / purchase_count
            
            # Purchase consistency (lower variance = higher score)
            order_values = [sale.total_amount for sale in sales]
            purchase_variance = np.var(order_values) if len(order_values) > 1 else 0
            
            # Recency factor
            last_purchase = max(sale.created_at for sale in sales)
            days_since_last = (datetime.utcnow() - last_purchase).days
            recency_score = max(0, 100 - days_since_last)
            
            # Calculate base score
            spending_score = min(40, total_spent / 10000)  # Max 40 points for 100k+ spending
            frequency_score = min(30, purchase_count * 2)  # Max 30 points for 15+ purchases
            consistency_score = max(0, 20 - (purchase_variance / 10000))  # Lower variance = higher score
            recency_factor = min(10, recency_score / 10)
            
            credit_score = int(spending_score + frequency_score + consistency_score + recency_factor)
            
            # Determine risk level and credit limit
            if credit_score >= 80:
                risk_level = "low"
                credit_limit = min(total_spent * 2, 500000)  # Max 500k
            elif credit_score >= 60:
                risk_level = "medium"
                credit_limit = min(total_spent, 200000)  # Max 200k
            elif credit_score >= 40:
                risk_level = "high"
                credit_limit = min(total_spent * 0.5, 50000)  # Max 50k
            else:
                risk_level = "very_high"
                credit_limit = 0
            
            return {
                "customer_id": customer_id,
                "credit_score": credit_score,
                "risk_level": risk_level,
                "recommended_credit_limit": int(credit_limit),
                "factors": {
                    "total_spent": total_spent,
                    "purchase_count": purchase_count,
                    "avg_order_value": avg_order_value,
                    "days_since_last_purchase": days_since_last
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating credit score: {str(e)}")
            return {"error": str(e)}
    
    def generate_targeted_promotions(self):
        """Generate targeted promotions based on customer segments"""
        try:
            loyalty_data = self.get_loyalty_dashboard()
            
            if not loyalty_data.get('success'):
                return loyalty_data
            
            customers = loyalty_data['customers']
            promotions = []
            
            for customer in customers:
                promotion = self._generate_customer_promotion(customer)
                if promotion:
                    promotions.append(promotion)
            
            return {
                "success": True,
                "promotions": promotions,
                "total_promotions": len(promotions)
            }
            
        except Exception as e:
            logger.error(f"Error generating promotions: {str(e)}")
            return {"error": str(e)}
    
    def birthday_anniversary_alerts(self):
        """Generate birthday and anniversary notifications"""
        try:
            # This would require birthday/anniversary data in customer records
            # For now, return placeholder structure
            alerts = []
            
            # Get customers with recent activity
            recent_customers = Sale.query.filter(
                Sale.created_at >= datetime.utcnow() - timedelta(days=365),
                Sale.customer_name.isnot(None)
            )
            
            if self.user_id:
                recent_customers = recent_customers.filter_by(user_id=self.user_id)
            
            customers = recent_customers.group_by(Sale.customer_name).all()
            
            for customer in customers:
                # Generate mock anniversary alert (first purchase anniversary)
                first_purchase = Sale.query.filter_by(
                    customer_name=customer.customer_name
                ).order_by(Sale.created_at.asc()).first()
                
                if first_purchase:
                    anniversary_date = first_purchase.created_at.replace(year=datetime.utcnow().year)
                    days_until = (anniversary_date - datetime.utcnow()).days
                    
                    if -7 <= days_until <= 7:  # Within a week of anniversary
                        alerts.append({
                            "customer_name": customer.customer_name,
                            "customer_phone": customer.customer_phone,
                            "alert_type": "anniversary",
                            "days_until": days_until,
                            "anniversary_date": anniversary_date.isoformat(),
                            "suggested_promotion": "10% discount on next purchase",
                            "message_template": f"Happy anniversary {customer.customer_name}! It's been a year since your first purchase with us. Enjoy 10% off your next order!"
                        })
            
            return {
                "success": True,
                "alerts": alerts,
                "total_alerts": len(alerts)
            }
            
        except Exception as e:
            logger.error(f"Error generating birthday/anniversary alerts: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_loyalty_tier(self, total_spent, purchase_count):
        """Calculate customer loyalty tier"""
        if total_spent >= 500000 and purchase_count >= 20:
            return "Platinum"
        elif total_spent >= 200000 and purchase_count >= 10:
            return "Gold"
        elif total_spent >= 50000 and purchase_count >= 5:
            return "Silver"
        else:
            return "Bronze"
    
    def _get_next_tier_requirement(self, total_spent, purchase_count):
        """Get requirements for next loyalty tier"""
        current_tier = self._calculate_loyalty_tier(total_spent, purchase_count)
        
        if current_tier == "Bronze":
            return {"next_tier": "Silver", "spending_needed": max(0, 50000 - total_spent), "purchases_needed": max(0, 5 - purchase_count)}
        elif current_tier == "Silver":
            return {"next_tier": "Gold", "spending_needed": max(0, 200000 - total_spent), "purchases_needed": max(0, 10 - purchase_count)}
        elif current_tier == "Gold":
            return {"next_tier": "Platinum", "spending_needed": max(0, 500000 - total_spent), "purchases_needed": max(0, 20 - purchase_count)}
        else:
            return {"next_tier": "Platinum", "spending_needed": 0, "purchases_needed": 0}
    
    def _calculate_program_stats(self, loyalty_data):
        """Calculate loyalty program statistics"""
        if not loyalty_data:
            return {}
        
        tier_counts = {}
        total_points = 0
        
        for customer in loyalty_data:
            tier = customer['loyalty_tier']
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
            total_points += customer['total_points']
        
        return {
            "tier_distribution": tier_counts,
            "total_points_issued": total_points,
            "average_points_per_customer": total_points / len(loyalty_data) if loyalty_data else 0,
            "top_customers": loyalty_data[:5]  # Top 5 customers
        }
    
    def _generate_customer_promotion(self, customer):
        """Generate targeted promotion for a customer"""
        tier = customer['loyalty_tier']
        days_since_last = (datetime.utcnow() - customer['last_purchase']).days
        
        # Win-back promotion for inactive customers
        if days_since_last > 30:
            return {
                "customer_name": customer['name'],
                "customer_phone": customer['phone'],
                "promotion_type": "win_back",
                "discount_percentage": 15,
                "message": f"We miss you! Come back and enjoy 15% off your next purchase.",
                "validity_days": 14
            }
        
        # Tier-based promotions
        tier_promotions = {
            "Platinum": {"discount": 20, "message": "Exclusive Platinum member offer: 20% off premium items"},
            "Gold": {"discount": 15, "message": "Gold member special: 15% off your next purchase"},
            "Silver": {"discount": 10, "message": "Silver member discount: 10% off selected items"},
            "Bronze": {"discount": 5, "message": "Welcome offer: 5% off your next purchase"}
        }
        
        if tier in tier_promotions:
            promo = tier_promotions[tier]
            return {
                "customer_name": customer['name'],
                "customer_phone": customer['phone'],
                "promotion_type": "tier_based",
                "discount_percentage": promo['discount'],
                "message": promo['message'],
                "validity_days": 30
            }
        
        return None

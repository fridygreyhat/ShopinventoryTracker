
from datetime import datetime, timedelta
from flask import current_app
from models import db
import uuid

class SupplyChainService:
    def __init__(self, user_id):
        self.user_id = user_id
    
    def create_supplier(self, supplier_data):
        """Create a new supplier"""
        from models import Supplier
        
        supplier = Supplier(
            name=supplier_data['name'],
            contact_person=supplier_data.get('contact_person', ''),
            email=supplier_data.get('email', ''),
            phone=supplier_data.get('phone', ''),
            address=supplier_data.get('address', ''),
            tax_id=supplier_data.get('tax_id', ''),
            payment_terms=supplier_data.get('payment_terms', 30),
            rating=supplier_data.get('rating', 0),
            is_active=True,
            user_id=self.user_id
        )
        
        db.session.add(supplier)
        db.session.commit()
        
        return supplier.to_dict()
    
    def create_purchase_order(self, po_data):
        """Create a purchase order"""
        from models import PurchaseOrder, PurchaseOrderItem
        
        # Generate PO number
        po_number = f"PO-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        po = PurchaseOrder(
            po_number=po_number,
            supplier_id=po_data['supplier_id'],
            expected_delivery_date=datetime.strptime(po_data['expected_delivery_date'], '%Y-%m-%d').date(),
            status='pending',
            total_amount=0,
            notes=po_data.get('notes', ''),
            user_id=self.user_id
        )
        
        db.session.add(po)
        db.session.flush()
        
        total_amount = 0
        for item_data in po_data['items']:
            po_item = PurchaseOrderItem(
                purchase_order_id=po.id,
                item_id=item_data['item_id'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                total_price=item_data['quantity'] * item_data['unit_price']
            )
            
            total_amount += po_item.total_price
            db.session.add(po_item)
        
        po.total_amount = total_amount
        db.session.commit()
        
        return po.to_dict()
    
    def update_delivery_status(self, po_id, status, tracking_info=None):
        """Update delivery status of purchase order"""
        from models import PurchaseOrder, DeliveryTracking
        
        po = PurchaseOrder.query.get(po_id)
        if not po or po.user_id != self.user_id:
            return {"success": False, "error": "Purchase order not found"}
        
        po.status = status
        po.updated_at = datetime.utcnow()
        
        # Add tracking information
        if tracking_info:
            tracking = DeliveryTracking(
                purchase_order_id=po_id,
                status=status,
                location=tracking_info.get('location', ''),
                notes=tracking_info.get('notes', ''),
                timestamp=datetime.utcnow()
            )
            db.session.add(tracking)
        
        db.session.commit()
        
        return {"success": True, "message": "Delivery status updated"}
    
    def create_quality_checklist(self, po_id, checklist_data):
        """Create quality control checklist for received goods"""
        from models import QualityChecklist, QualityCheckItem
        
        checklist = QualityChecklist(
            purchase_order_id=po_id,
            inspector_name=checklist_data['inspector_name'],
            inspection_date=datetime.utcnow().date(),
            overall_status='pending',
            notes=checklist_data.get('notes', ''),
            user_id=self.user_id
        )
        
        db.session.add(checklist)
        db.session.flush()
        
        passed_items = 0
        total_items = len(checklist_data['items'])
        
        for item_data in checklist_data['items']:
            check_item = QualityCheckItem(
                quality_checklist_id=checklist.id,
                item_id=item_data['item_id'],
                check_description=item_data['check_description'],
                status=item_data['status'],
                notes=item_data.get('notes', '')
            )
            
            if item_data['status'] == 'passed':
                passed_items += 1
            
            db.session.add(check_item)
        
        # Determine overall status
        if passed_items == total_items:
            checklist.overall_status = 'passed'
        elif passed_items == 0:
            checklist.overall_status = 'failed'
        else:
            checklist.overall_status = 'partial'
        
        db.session.commit()
        
        return checklist.to_dict()
    
    def get_supplier_performance(self, supplier_id):
        """Get supplier performance metrics"""
        from models import PurchaseOrder, QualityChecklist
        from sqlalchemy import func
        
        # Get delivery performance
        total_orders = PurchaseOrder.query.filter_by(
            supplier_id=supplier_id,
            user_id=self.user_id
        ).count()
        
        on_time_deliveries = PurchaseOrder.query.filter_by(
            supplier_id=supplier_id,
            user_id=self.user_id,
            status='delivered'
        ).filter(
            PurchaseOrder.delivered_date <= PurchaseOrder.expected_delivery_date
        ).count()
        
        # Get quality performance
        quality_checks = db.session.query(QualityChecklist).join(PurchaseOrder).filter(
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrder.user_id == self.user_id
        ).all()
        
        passed_quality = sum(1 for check in quality_checks if check.overall_status == 'passed')
        total_quality_checks = len(quality_checks)
        
        # Calculate averages
        avg_delivery_time = db.session.query(
            func.avg(func.julianday(PurchaseOrder.delivered_date) - func.julianday(PurchaseOrder.created_at))
        ).filter_by(supplier_id=supplier_id, user_id=self.user_id).scalar() or 0
        
        return {
            "total_orders": total_orders,
            "on_time_delivery_rate": (on_time_deliveries / total_orders * 100) if total_orders > 0 else 0,
            "quality_pass_rate": (passed_quality / total_quality_checks * 100) if total_quality_checks > 0 else 0,
            "average_delivery_time_days": round(avg_delivery_time, 1),
            "total_quality_checks": total_quality_checks
        }
    
    def automated_reorder_suggestions(self):
        """Generate automated reorder suggestions based on stock levels"""
        from models import Item, PurchaseOrder, Supplier
        
        # Get items below minimum stock level
        low_stock_items = Item.query.filter(
            Item.user_id == self.user_id,
            Item.is_active == True,
            Item.stock_quantity <= Item.minimum_stock
        ).all()
        
        suggestions = []
        for item in low_stock_items:
            # Find preferred supplier (most recent orders or highest rating)
            preferred_supplier = db.session.query(Supplier).join(PurchaseOrder).join(
                PurchaseOrder.items
            ).filter(
                PurchaseOrder.user_id == self.user_id,
                PurchaseOrderItem.item_id == item.id
            ).order_by(
                Supplier.rating.desc(),
                PurchaseOrder.created_at.desc()
            ).first()
            
            if preferred_supplier:
                # Calculate suggested quantity (enough for next 30 days based on average usage)
                avg_daily_usage = self._calculate_average_daily_usage(item.id)
                suggested_quantity = max(
                    item.minimum_stock * 2,  # At least double minimum stock
                    int(avg_daily_usage * 30)  # Or 30 days worth of usage
                )
                
                suggestions.append({
                    "item": item.to_dict(),
                    "supplier": preferred_supplier.to_dict(),
                    "suggested_quantity": suggested_quantity,
                    "current_stock": item.stock_quantity,
                    "minimum_stock": item.minimum_stock,
                    "urgency": "high" if item.stock_quantity == 0 else "medium"
                })
        
        return suggestions
    
    def _calculate_average_daily_usage(self, item_id):
        """Calculate average daily usage for an item"""
        from models import SaleItem, Sale
        
        # Get sales data for last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        total_sold = db.session.query(func.sum(SaleItem.quantity)).join(Sale).filter(
            SaleItem.item_id == item_id,
            Sale.user_id == self.user_id,
            Sale.created_at >= thirty_days_ago
        ).scalar() or 0
        
        return total_sold / 30  # Average per day

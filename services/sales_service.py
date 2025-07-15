
from models import db, Sale, SaleItem, Item, Customer, StockMovement
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SalesService:
    def __init__(self, user_id):
        self.user_id = user_id

    def process_sale(self, sale_data):
        """Process a complete sale transaction"""
        try:
            # Start transaction
            db.session.begin()

            # Create customer if needed
            customer = None
            if sale_data.get('customer') and sale_data['customer'].get('name') != 'Walk-in Customer':
                customer = self._get_or_create_customer(sale_data['customer'])

            # Generate sale number
            sale_number = self._generate_sale_number()

            # Create sale record
            sale = Sale(
                sale_number=sale_number,
                customer_id=customer.id if customer else None,
                user_id=self.user_id,
                total_amount=sale_data['total'],
                payment_method=sale_data['payment']['method'],
                sale_type=sale_data.get('sale_type', 'retail'),
                notes=sale_data.get('notes', ''),
                created_at=datetime.utcnow()
            )

            db.session.add(sale)
            db.session.flush()  # Get sale ID

            # Process sale items
            for item_data in sale_data['items']:
                success, message = self._process_sale_item(sale.id, item_data)
                if not success:
                    raise Exception(message)

            # Commit transaction
            db.session.commit()

            return {
                'success': True,
                'sale_id': sale.id,
                'sale_number': sale_number,
                'message': 'Sale processed successfully'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing sale: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _process_sale_item(self, sale_id, item_data):
        """Process individual sale item"""
        try:
            # Get item
            item = Item.query.filter_by(
                id=item_data['id'],
                user_id=self.user_id
            ).first()

            if not item:
                return False, f"Item not found: {item_data['name']}"

            # Check stock availability
            if item.stock_quantity < item_data['quantity']:
                return False, f"Insufficient stock for {item.name}. Available: {item.stock_quantity}"

            # Create sale item
            sale_item = SaleItem(
                sale_id=sale_id,
                item_id=item.id,
                quantity=item_data['quantity'],
                price=item_data['price']
            )

            # Update stock
            item.stock_quantity -= item_data['quantity']

            # Create stock movement record
            stock_movement = StockMovement(
                movement_type='out',
                quantity=item_data['quantity'],
                reason='Sale',
                item_id=item.id,
                user_id=self.user_id,
                created_at=datetime.utcnow()
            )

            db.session.add(sale_item)
            db.session.add(stock_movement)

            return True, "Success"

        except Exception as e:
            return False, str(e)

    def _get_or_create_customer(self, customer_data):
        """Get existing customer or create new one"""
        # Check if customer exists
        customer = Customer.query.filter_by(
            phone=customer_data['phone'],
            user_id=self.user_id
        ).first()

        if customer:
            return customer

        # Create new customer
        customer = Customer(
            name=customer_data['name'],
            phone=customer_data['phone'],
            address=customer_data.get('address', ''),
            user_id=self.user_id,
            created_at=datetime.utcnow()
        )

        db.session.add(customer)
        return customer

    def _generate_sale_number(self):
        """Generate unique sale number"""
        now = datetime.utcnow()
        date_str = now.strftime('%Y%m%d%H%M%S')
        return f"SALE-{date_str}"

    def get_sale_details(self, sale_id):
        """Get detailed sale information"""
        try:
            sale = Sale.query.filter_by(
                id=sale_id,
                user_id=self.user_id
            ).first()

            if not sale:
                return {'success': False, 'error': 'Sale not found'}

            sale_items = []
            for item in sale.sale_items:
                sale_items.append({
                    'item_name': item.item.name,
                    'quantity': item.quantity,
                    'price': float(item.price),
                    'total': float(item.quantity * item.price)
                })

            return {
                'success': True,
                'sale': {
                    'id': sale.id,
                    'sale_number': sale.sale_number,
                    'date': sale.created_at.strftime('%Y-%m-%d %H:%M'),
                    'customer': sale.customer.name if sale.customer else 'Walk-in Customer',
                    'total_amount': float(sale.total_amount),
                    'payment_method': sale.payment_method,
                    'items': sale_items
                }
            }

        except Exception as e:
            logger.error(f"Error getting sale details: {str(e)}")
            return {'success': False, 'error': str(e)}

    def void_sale(self, sale_id, reason):
        """Void a sale and restore inventory"""
        try:
            sale = Sale.query.filter_by(
                id=sale_id,
                user_id=self.user_id
            ).first()

            if not sale:
                return {'success': False, 'error': 'Sale not found'}

            # Restore inventory for each item
            for sale_item in sale.sale_items:
                item = sale_item.item
                item.stock_quantity += sale_item.quantity

                # Create stock movement record
                stock_movement = StockMovement(
                    movement_type='in',
                    quantity=sale_item.quantity,
                    reason=f'Sale void: {reason}',
                    item_id=item.id,
                    user_id=self.user_id,
                    created_at=datetime.utcnow()
                )
                db.session.add(stock_movement)

            # Mark sale as voided
            sale.status = 'voided'
            sale.notes = f"VOIDED: {reason}"

            db.session.commit()

            return {
                'success': True,
                'message': f'Sale {sale.sale_number} voided successfully'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error voiding sale: {str(e)}")
            return {'success': False, 'error': str(e)}

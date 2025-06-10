"""
Database models package
"""
from app.models.user import User
from app.models.inventory import Item, Category, LocationStock, StockMovement, StockTransfer, StockTransferItem
from app.models.sales import Sale, SaleItem, InstallmentPlan, InstallmentPayment
from app.models.financial import FinancialTransaction, BankAccount
from app.models.location import Location
from app.models.customer import Customer
from app.models.automation import OnDemandProduct, OnDemandOrder

__all__ = [
    'User',
    'Item', 'Category', 'LocationStock', 'StockMovement', 'StockTransfer', 'StockTransferItem',
    'Sale', 'SaleItem', 'InstallmentPlan', 'InstallmentPayment',
    'FinancialTransaction', 'BankAccount',
    'Location',
    'Customer',
    'OnDemandProduct', 'OnDemandOrder'
]
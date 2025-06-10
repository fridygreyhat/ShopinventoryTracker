#!/bin/bash

# MauzoTZ Codebase Cleanup Script
# Removes development files and prepares for production deployment

set -e

echo "🧹 Cleaning up codebase for production deployment..."

# Remove development files
rm -rf __pycache__/
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name ".pytest_cache" -type d -exec rm -rf {} +

# Remove SQLite development databases
rm -f instance/inventory.db
rm -f *.db

# Remove backup files
rm -f sqlite_backup_*.json
rm -f user_reset_backup_*.json

# Remove unnecessary migration scripts
rm -f migrate_*.py
rm -f complete_data_migration.py
rm -f database_inspector.py
rm -f database_admin.py
rm -f reset_users.py
rm -f list_users.py

# Remove development-specific admin creation scripts
rm -f create_admin.py
rm -f create_specific_admin.py

# Clean up asset files
rm -rf attached_assets/

# Remove virtual environment if present
rm -rf venv/

# Clean up log files
mkdir -p logs
rm -f logs/*.log

# Create necessary directories
mkdir -p static/uploads
mkdir -p logs
mkdir -p instance

# Set proper permissions for directories
chmod 755 static/uploads
chmod 755 logs
chmod 755 instance

# Remove duplicate or redundant files
rm -f admin_routes.py  # Consolidated into admin_portal.py
rm -f customer_management.py  # Functionality moved to routes.py
rm -f inventory_service.py  # Consolidated into routes.py

# Clean up email and notification duplicates
rm -rf notifications/  # Consolidated services

# Remove language files that are not needed
rm -f translations.py  # Using language_utils.py

# Create production-ready file structure summary
echo "📁 Production file structure:"
echo "├── app.py (Main application)"
echo "├── wsgi.py (WSGI entry point)"
echo "├── config.py (Configuration management)"
echo "├── models.py (Database models)"
echo "├── routes.py (Main application routes)"
echo "├── routes_sms.py (SMS management routes)"
echo "├── auth.py (Authentication routes)"
echo "├── admin_portal.py (Admin interface)"
echo "├── sms_service.py (SMS functionality)"
echo "├── sms_scheduler.py (Automated SMS)"
echo "├── language_routes.py (Language switching)"
echo "├── language_utils.py (Translation utilities)"
echo "├── currency_utils.py (Currency formatting)"
echo "├── predictive_analytics.py (Analytics engine)"
echo "├── smart_automation.py (Automation features)"
echo "├── automation_manager.py (Automation management)"
echo "├── notification_service.py (Notification system)"
echo "├── email_service.py (Email functionality)"
echo "├── enhanced_financial_service.py (Financial analytics)"
echo "├── financial_service.py (Financial operations)"
echo "├── permission_decorators.py (Access control)"
echo "├── auth_service.py (Authentication services)"
echo "├── templates/ (Frontend templates)"
echo "├── static/ (Static assets)"
echo "├── logs/ (Application logs)"
echo "├── instance/ (Instance-specific files)"
echo "├── gunicorn.conf.py (Production server config)"
echo "├── deploy.sh (Deployment script)"
echo "├── production_requirements.txt (Dependencies)"
echo "├── .env.example (Environment template)"
echo "└── README.md (Documentation)"

echo "✅ Codebase cleanup completed successfully!"
echo "📦 Ready for Git commit and Ubuntu server deployment!"
# Inventory Management System

## Overview

This is a comprehensive Flask-based inventory management system designed for small to medium businesses. The application provides complete inventory tracking, sales management, financial reporting, and user management capabilities with a modern web interface.

## System Architecture

The system follows a traditional MVC architecture with Flask as the web framework:

- **Frontend**: Bootstrap 5 with responsive design, Font Awesome icons, and JavaScript for dynamic interactions
- **Backend**: Flask web framework with SQLAlchemy ORM
- **Database**: PostgreSQL (configured to work with Replit's database service)
- **Authentication**: Custom authentication system with session management
- **Email**: Flask-Mail for email notifications and user verification

## Key Components

### Core Models
- **User**: User account management with admin roles and authentication
- **Item**: Product/inventory item management with categories and stock tracking  
- **Sale**: Sales transaction management with line items
- **Category**: Product categorization system
- **FinancialTransaction**: Financial record keeping
- **Customer**: Customer management and loyalty tracking

### Service Layer
- **AuthService**: Authentication and authorization logic
- **AccountingService**: Basic accounting functionality and chart of accounts
- **EmailService**: Email notifications and password reset functionality
- **NotificationService**: SMS and email notification system (Twilio/SendGrid integration)
- **Various Analytics Services**: Business intelligence, predictive analytics, and reporting

### Admin Portal
- **User Management**: Admin interface for managing users and permissions
- **System Monitoring**: Dashboard for system statistics and user activity
- **Role-based Access Control**: Admin-only sections with proper authorization

## Data Flow

1. **User Registration/Login**: Users register through the web interface, with email verification
2. **Inventory Management**: Users add/edit items through forms, data persisted to PostgreSQL
3. **Sales Processing**: Sales are recorded with automatic inventory updates and financial entries
4. **Reporting**: Analytics services query the database to generate business intelligence reports
5. **Notifications**: System monitors stock levels and sends alerts via email/SMS

## External Dependencies

### Required Services
- **PostgreSQL Database**: Primary data storage (DATABASE_URL environment variable)
- **Email Provider**: SMTP configuration for email notifications
- **Optional Integrations**:
  - Twilio for SMS notifications
  - SendGrid for enhanced email delivery

### Python Packages
- Flask ecosystem (Flask, SQLAlchemy, Mail)
- Authentication libraries (werkzeug for password hashing)
- Data processing (pandas for analytics)
- External API clients (requests, twilio, firebase-admin)

## Deployment Strategy

The application is designed for Replit deployment with the following considerations:

1. **Database Setup**: Uses Replit's PostgreSQL service via DATABASE_URL
2. **Environment Variables**: All sensitive configuration via environment variables
3. **Static Files**: Served directly by Flask (suitable for development/small scale)
4. **Session Management**: File-based sessions (appropriate for single-instance deployment)

### Configuration Files
- `main.py`: Entry point for Replit
- `wsgi.py`: WSGI application entry point
- `requirements.txt`: Python dependencies
- Database initialization scripts for PostgreSQL setup

## Changelog
- July 11, 2025: Critical Syntax and Database Model Fixes + Redirect Loop Resolution + Modern Cover Page
  - Fixed duplicate return statement syntax error in app.py line 852
  - Removed duplicate User model definition that was causing SQLAlchemy primary key conflicts
  - Added missing login_required import from flask_login
  - Resolved "expected 'except' or 'finally' block" syntax error
  - Fixed infinite redirect loop by replacing Flask-Login's login_required with custom session-based decorator
  - Updated all current_user references to use session.get('user_id') for consistent authentication
  - Added get_current_user() context processor for template access to current user data
  - Application now starts successfully with proper PostgreSQL authentication
  - All navigation works correctly without redirect loops, login and dashboard pages load properly
  - Created modern system cover page with glassmorphism design and sign up/sign in functionality
  - Investigating transaction completion issue - API endpoint appears correct but frontend shows "Failed to complete transaction"

- July 5, 2025: Sales Transaction Processing Fix and Firebase Cleanup
  - Fixed critical transaction completion failure by implementing proper session-based authentication in sales API
  - Updated api_create_sale endpoint to use session.get('user_id') instead of current_user references
  - Added proper user authorization for item access during sales processing
  - Enhanced stock tracking to handle both quantity and stock_quantity fields correctly
  - Added credentials: 'same-origin' to all fetch requests for proper authentication
  - Fixed sales tab product visibility with proper authentication and user filtering
  - Enhanced inventory API with session-based user filtering for secure data isolation
  - Added "Show All Products" functionality to sales interface for better user experience
  - Removed firebase-auth.js file to eliminate "Server response was not valid JSON" registration errors
  - Application now properly handles complete sales transactions with inventory updates
  
- July 5, 2025: Enhanced UI/UX Design and Navigation
  - Redesigned login page with modern glassmorphism effects, gradient animations, and enhanced visual appeal
  - Created comprehensive dashboard enhancements with gradient summary cards, quick action buttons, and improved layout
  - Fixed vertical navigation bar positioning and tab scrolling issues with responsive design
  - Added tab scroll indicators and smooth scrolling for better user experience
  - Implemented navigation enhancements JavaScript for improved mobile experience
  - Created .gitignore file to exclude environment variables from version control
  - Added authentication protection to API endpoints that were missing login requirements

- July 4, 2025: Authentication System Cleanup
  - Completely removed Firebase authentication in favor of PostgreSQL-only authentication
  - Cleaned up Firebase references from models, auth service, and documentation
  - Fixed API handler inconsistencies causing repeated "Error loading on-demand products" and "Error loading category breakdown" errors
  - Updated all API methods to use consistent response handling patterns

- July 1, 2025: Resolved application startup and routing errors
  - Fixed duplicate model definitions causing SQLAlchemy startup errors
  - Added missing model classes (StockMovement, InstallmentPlan, ChartOfAccounts, Journal, Supplier, PurchaseOrder)
  - Resolved database import issues and circular dependencies
  - Added missing 'categories' route to fix navigation BuildError
  - Application now starts successfully without errors on port 5000
- June 30, 2025: Fixed critical database and JavaScript errors
  - Added missing customer_id foreign key to Sale model
  - Fixed database schema issues with Category table (added parent_id, sort_order, user_id columns)
  - Resolved JavaScript syntax error in dashboard.js 
  - Added sample categories and inventory items to resolve empty data issues
  - Installed missing numpy and pandas dependencies for predictive analytics
- June 29, 2025: Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.
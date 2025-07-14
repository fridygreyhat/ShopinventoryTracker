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
- July 14, 2025: Complete CRUD Operations Implementation & System Enhancement
  - **✅ COMPREHENSIVE CRUD OPERATIONS COMPLETED** - All major system modules now have fully functional CRUD operations:
    
    **Items/Inventory Management:**
    - ✅ POST /api/items - Create new inventory items with automatic SKU generation
    - ✅ GET /api/items - List all items with user filtering and search
    - ✅ GET /api/items/:id - Get specific item details
    - ✅ PUT /api/items/:id - Update item information (name, description, pricing, stock)
    - ✅ DELETE /api/items/:id - Soft delete (mark as inactive)
    
    **Customer Management:**
    - ✅ POST /api/customers - Create new customers
    - ✅ GET /api/customers - List all customers for current user
    - ✅ GET /api/customers/:id - Get specific customer details
    - ✅ PUT /api/customers/:id - Update customer information
    - ✅ DELETE /api/customers/:id - Delete customer records
    
    **Sales Management:**
    - ✅ POST /api/sales - Create new sales with automatic inventory updates
    - ✅ GET /api/sales - List all sales with pagination and item details
    - ✅ GET /api/sales/:id - Get specific sale with complete item breakdown
    - ✅ PUT /api/sales/:id - Update sale information (limited fields)
    - ✅ DELETE /api/sales/:id - Delete sale and restore inventory
    
    **Financial Transactions:**
    - ✅ POST /api/transactions - Create new financial transactions
    - ✅ GET /api/transactions - List transactions with filtering and summaries
    - ✅ GET /api/transactions/:id - Get specific transaction details
    - ✅ PUT /api/transactions/:id - Update transaction information
    - ✅ DELETE /api/transactions/:id - Delete transaction records
    
    **Categories Management:**
    - ✅ POST /api/categories - Create new categories with hierarchical support
    - ✅ GET /api/categories - List all categories with subcategories
    - ✅ PUT /api/categories/:id - Update category information
    - ✅ DELETE /api/categories/:id - Delete categories
    
  - **Database Schema & Relationships:**
    - Fixed all foreign key constraints between user, customer, sale, and item tables
    - Resolved Item model field inconsistencies (unified stock_quantity, retail_price)
    - Enhanced Sale and SaleItem models with proper cascade relationships
    - All database operations now include proper user isolation and authentication
    
  - **API Security & Authentication:**
    - All endpoints now require proper session-based authentication
    - User data isolation enforced across all operations
    - Proper error handling and validation on all CRUD operations
    - Session management working reliably with PostgreSQL backend
    
  - **Sales Transaction Processing:**
    - Sales creation with real-time inventory updates (e.g., 50→48 units)
    - Proper stock tracking through StockMovement records
    - Support for multiple payment methods and customer information
    - Sale deletion with automatic inventory restoration
    
  - **System Testing Results:**
    - ✅ Item creation: Working (Test Product created with SKU generation)
    - ✅ Item updates: Working (Coca Cola updated successfully)
    - ✅ Customer updates: Working (John Doe updated multiple times)
    - ✅ Sales creation: Working (SALE-20250714175252 processed correctly)
    - ✅ Transaction management: Working (Income/Expense tracking functional)
    - ✅ Inventory soft delete: Working (Item ID 8 marked inactive)
    - ✅ User authentication: Working (Session-based auth across all endpoints)
    
  - **Technical Improvements:**
    - Added proper pagination for large datasets
    - Implemented comprehensive error handling and logging
    - Enhanced API response formats with success/error states
    - Added proper user filtering to prevent data leakage
    - All endpoints now return consistent JSON responses
    
  - **Database Integrity:**
    - Foreign key constraints properly maintained
    - Cascading deletes working correctly
    - User isolation enforced at database level
    - All CRUD operations maintain referential integrity
    
  **SYSTEM STATUS: All major CRUD operations fully functional with proper authentication, user isolation, and database integrity. The inventory management system now provides complete, reliable data operations across all business modules.**

- July 14, 2025: Major Codebase Cleanup and System Optimization
  - Removed all Firebase dependencies and references from the codebase
  - Unified authentication system to use session-based authentication exclusively
  - Cleaned up redundant files: auth.py, routes.py, multiple migration scripts
  - Removed unused utilities: check_*.py, migrate_*.py, inventory_service.py
  - Consolidated all routes into app.py for better organization and maintainability
  - Fixed import conflicts and circular dependencies
  - Streamlined authentication decorators and context processors
  - Enhanced error handling and logging throughout the application
  - Optimized database queries and session management
  - All API endpoints now properly handle authentication and user isolation
  - System now runs with cleaner, more maintainable architecture

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
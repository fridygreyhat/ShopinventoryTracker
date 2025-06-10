# MauzoTZ Inventory Management System

A comprehensive business management platform built with Flask, designed for multi-location inventory management, sales tracking, customer management, and financial analytics with SMS notifications.

## Features

### Core Functionality
- **Multi-location Inventory Management** - Track stock across multiple locations
- **Sales Management** - Process sales with installment payment options
- **Customer Management** - Comprehensive customer database with SMS integration
- **Financial Analytics** - Profit margin analysis and accounting dashboard
- **SMS Notifications** - Automated customer communications via Twilio
- **Multi-language Support** - English and Swahili languages
- **Role-based Access Control** - Admin, manager, and staff permissions

### Advanced Features
- **Predictive Analytics** - ABC analysis and demand forecasting
- **Smart Automation** - Auto-generated purchase orders and notifications
- **On-demand Products** - Special order management
- **Category Management** - Hierarchical product categorization
- **Stock Transfer Management** - Inter-location stock movements
- **Payment Tracking** - Installment and layaway management

## Technology Stack

- **Backend**: Flask, SQLAlchemy, PostgreSQL
- **Frontend**: Bootstrap 5, Jinja2 templates
- **Authentication**: Flask-Login with session management
- **SMS Integration**: Twilio API
- **Email**: Flask-Mail with SMTP
- **Deployment**: Gunicorn, Nginx, systemd

## Quick Start

### Prerequisites
- Ubuntu Server 20.04+ or similar Linux distribution
- Python 3.11+
- PostgreSQL 12+
- Nginx
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd mauzotz-inventory
   ```

2. **Run the deployment script** (for Ubuntu server)
   ```bash
   sudo ./deploy.sh
   ```

3. **Configure environment variables**
   ```bash
   sudo nano /var/www/mauzotz/.env
   ```
   Add your specific configuration:
   - Database credentials
   - Email SMTP settings
   - Twilio SMS credentials
   - Security keys

4. **Create admin user**
   ```bash
   cd /var/www/mauzotz
   python3 create_admin_user.py
   ```

### Manual Installation

1. **Install dependencies**
   ```bash
   pip install -r production_requirements.txt
   ```

2. **Set up PostgreSQL database**
   ```bash
   sudo -u postgres createdb mauzotz_db
   sudo -u postgres createuser mauzotz
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize database**
   ```bash
   python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

5. **Run application**
   ```bash
   gunicorn --config gunicorn.conf.py wsgi:app
   ```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `FLASK_ENV` | Environment (production/development) | Yes |
| `SECRET_KEY` | Flask secret key | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `TWILIO_ACCOUNT_SID` | Twilio account SID for SMS | Optional |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | Optional |
| `TWILIO_PHONE_NUMBER` | Twilio phone number | Optional |
| `MAIL_SERVER` | SMTP server | Optional |
| `MAIL_USERNAME` | Email username | Optional |
| `MAIL_PASSWORD` | Email password | Optional |

### Database Configuration

The application uses PostgreSQL as the primary database. Ensure proper connection pooling and backup strategies are in place for production environments.

### SMS Configuration

To enable SMS notifications:
1. Sign up for a Twilio account
2. Get your Account SID, Auth Token, and phone number
3. Add credentials to environment variables
4. Enable SMS notifications in user settings

## Usage

### Admin Panel
- Access admin features at `/admin/dashboard`
- Manage users, view system statistics
- Configure system-wide settings

### Inventory Management
- Add and manage products across multiple locations
- Track stock levels and movements
- Set up automatic reorder points

### Sales Processing
- Create sales with multiple payment options
- Handle cash, installment, and layaway transactions
- Generate sales reports and analytics

### Customer Management
- Maintain comprehensive customer database
- Send bulk SMS campaigns
- Track customer purchase history

### Financial Analytics
- View profit margin analysis
- Generate accounting reports
- Track financial transactions

## API Endpoints

The application provides RESTful endpoints for key operations:
- `/api/inventory` - Inventory management
- `/api/sales` - Sales processing
- `/api/customers` - Customer management
- `/api/reports` - Analytics and reporting

## Security Features

- CSRF protection enabled
- Secure session management
- Role-based access control
- SQL injection prevention
- XSS protection headers
- Secure password hashing

## Deployment

### Production Deployment

The included deployment script handles:
- System dependencies installation
- PostgreSQL setup
- Application configuration
- Nginx reverse proxy setup
- Systemd service configuration
- SSL certificate setup (with Certbot)

### Docker Deployment

For containerized deployment:
```bash
docker build -t mauzotz .
docker run -d -p 5000:5000 --env-file .env mauzotz
```

### Cloud Deployment

The application is compatible with major cloud providers:
- AWS (EC2, RDS, SES)
- Google Cloud Platform
- Digital Ocean
- Heroku

## Monitoring and Maintenance

### Logs
- Application logs: `/var/log/mauzotz/`
- Nginx logs: `/var/log/nginx/`
- System logs: `journalctl -u mauzotz`

### Backup
- Database: Regular PostgreSQL backups
- Static files: Backup upload directories
- Configuration: Version control environment files

### Performance Monitoring
- Monitor response times
- Track database performance
- Monitor memory and CPU usage
- Set up alerts for critical issues

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For support and documentation:
- Check the wiki for detailed guides
- Review existing issues before creating new ones
- Contact support at info@mauzotz.com

## License

This project is proprietary software. All rights reserved.

## Changelog

### Version 2.0.0
- Added SMS notification system
- Implemented multi-location inventory
- Enhanced financial analytics
- Improved user interface
- Added predictive analytics

### Version 1.0.0
- Initial release
- Basic inventory management
- Sales tracking
- Customer management
- User authentication
# MauzoTZ Production Deployment Guide

## Quick Deployment (Ubuntu Server)

### 1. Server Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Clone repository
git clone <your-repository-url> /var/www/mauzotz
cd /var/www/mauzotz

# Run automated deployment
sudo chmod +x deploy.sh
sudo ./deploy.sh
```

### 2. Configuration
```bash
# Edit environment variables
sudo nano /var/www/mauzotz/.env

# Required variables:
FLASK_ENV=production
SECRET_KEY=your-secure-random-key
SESSION_SECRET=your-session-secret
DATABASE_URL=postgresql://mauzotz:password@localhost:5432/mauzotz_db

# Optional SMS/Email:
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=+1234567890
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### 3. Create Admin User
```bash
cd /var/www/mauzotz
source venv/bin/activate
python3 create_admin_user.py
```

### 4. SSL Setup (Production)
```bash
# Configure domain in Nginx
sudo nano /etc/nginx/sites-available/mauzotz
# Update server_name to your domain

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com
```

## Manual Deployment Steps

### Prerequisites
- Ubuntu 20.04+ or CentOS 8+
- Python 3.11+
- PostgreSQL 12+
- Nginx
- 2GB+ RAM, 20GB+ storage

### 1. System Dependencies
```bash
sudo apt install python3-pip python3-venv python3-dev \
                 postgresql postgresql-contrib \
                 nginx supervisor git curl \
                 build-essential libpq-dev
```

### 2. Database Setup
```bash
sudo -u postgres psql
CREATE USER mauzotz WITH PASSWORD 'secure_password';
CREATE DATABASE mauzotz_db OWNER mauzotz;
GRANT ALL PRIVILEGES ON DATABASE mauzotz_db TO mauzotz;
\q
```

### 3. Application Setup
```bash
# Create application directory
sudo mkdir -p /var/www/mauzotz
cd /var/www/mauzotz

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r production_requirements.txt

# Set permissions
sudo chown -R www-data:www-data /var/www/mauzotz
sudo chmod -R 755 /var/www/mauzotz
```

### 4. Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location /static {
        alias /var/www/mauzotz/static;
        expires 1y;
    }
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. Systemd Service
```ini
[Unit]
Description=MauzoTZ Inventory Management System
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/mauzotz
Environment=PATH=/var/www/mauzotz/venv/bin
ExecStart=/var/www/mauzotz/venv/bin/gunicorn --config gunicorn.conf.py wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

## Security Checklist

- [ ] Environment variables secured (.env with 600 permissions)
- [ ] Database credentials unique and strong
- [ ] SSL certificate installed
- [ ] Firewall configured (ports 80, 443, 22 only)
- [ ] Regular backups scheduled
- [ ] Log rotation configured
- [ ] Security headers enabled in Nginx
- [ ] Admin user created with strong password

## Monitoring

### Log Locations
- Application: `/var/www/mauzotz/logs/`
- Nginx: `/var/log/nginx/`
- System: `journalctl -u mauzotz`

### Health Checks
```bash
# Check services
systemctl status mauzotz
systemctl status nginx
systemctl status postgresql

# Check logs
tail -f /var/www/mauzotz/logs/error.log
```

## Backup Strategy

### Database Backup
```bash
# Daily backup script
pg_dump -U mauzotz mauzotz_db > backup_$(date +%Y%m%d).sql
```

### File Backup
```bash
# Backup uploads and logs
tar -czf backup_files_$(date +%Y%m%d).tar.gz \
    /var/www/mauzotz/static/uploads \
    /var/www/mauzotz/logs
```

## Troubleshooting

### Common Issues

1. **Application won't start**
   - Check environment variables in `.env`
   - Verify database connection
   - Check Python dependencies

2. **SMS not working**
   - Verify Twilio credentials
   - Check phone number format (+country_code)
   - Review SMS service logs

3. **Database connection failed**
   - Verify PostgreSQL is running
   - Check database credentials
   - Ensure database exists

4. **Static files not loading**
   - Check Nginx configuration
   - Verify file permissions
   - Clear browser cache

### Performance Optimization

1. **Database**
   - Configure connection pooling
   - Set up database indexing
   - Monitor query performance

2. **Application**
   - Adjust Gunicorn workers
   - Enable Nginx gzip compression
   - Implement caching strategies

3. **Monitoring**
   - Set up application monitoring
   - Configure alerting
   - Monitor resource usage

## Production Features

✅ **Core Functionality**
- Multi-location inventory management
- Sales processing with installments
- Customer management with SMS
- Financial analytics and reporting
- Role-based access control
- Multi-language support (English/Swahili)

✅ **Advanced Features**
- SMS notifications via Twilio
- Predictive analytics and ABC analysis
- Smart automation for purchase orders
- On-demand product management
- Hierarchical category management
- Payment tracking and reminders

✅ **Security Features**
- CSRF protection
- Secure session management
- SQL injection prevention
- XSS protection headers
- Role-based permissions

✅ **Production Ready**
- Gunicorn WSGI server
- Nginx reverse proxy
- PostgreSQL database
- SSL/TLS encryption
- Systemd service management
- Comprehensive logging

## Support

For deployment assistance:
- Review application logs for errors
- Check system resource usage
- Verify network connectivity
- Contact support with specific error messages
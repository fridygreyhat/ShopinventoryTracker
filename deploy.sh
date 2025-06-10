#!/bin/bash

# MauzoTZ Inventory Management System Deployment Script
# For Ubuntu Server

set -e

echo "🚀 Starting MauzoTZ deployment..."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="mauzotz"
APP_DIR="/var/www/$APP_NAME"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
NGINX_CONFIG="/etc/nginx/sites-available/$APP_NAME"
PYTHON_VERSION="3.11"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

install_dependencies() {
    log_info "Installing system dependencies..."
    
    apt update
    apt install -y python3-pip python3-venv python3-dev \
                   postgresql postgresql-contrib \
                   nginx supervisor git curl \
                   build-essential libpq-dev \
                   certbot python3-certbot-nginx

    log_success "System dependencies installed"
}

setup_postgresql() {
    log_info "Setting up PostgreSQL..."
    
    # Start PostgreSQL service
    systemctl start postgresql
    systemctl enable postgresql
    
    # Create database and user
    sudo -u postgres psql -c "CREATE USER mauzotz WITH PASSWORD 'secure_password_123';"
    sudo -u postgres psql -c "CREATE DATABASE mauzotz_db OWNER mauzotz;"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE mauzotz_db TO mauzotz;"
    
    log_success "PostgreSQL setup completed"
}

setup_application() {
    log_info "Setting up application..."
    
    # Create application directory
    mkdir -p $APP_DIR
    cd $APP_DIR
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install Python dependencies
    pip install -r production_requirements.txt
    
    # Create necessary directories
    mkdir -p logs static/uploads instance
    
    # Set proper permissions
    chown -R www-data:www-data $APP_DIR
    chmod -R 755 $APP_DIR
    chmod -R 777 $APP_DIR/logs
    chmod -R 777 $APP_DIR/static/uploads
    
    log_success "Application setup completed"
}

setup_environment() {
    log_info "Setting up environment configuration..."
    
    cat > $APP_DIR/.env << EOL
FLASK_ENV=production
SECRET_KEY=$(openssl rand -base64 32)
SESSION_SECRET=$(openssl rand -base64 32)
DATABASE_URL=postgresql://mauzotz:secure_password_123@localhost:5432/mauzotz_db
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_DEFAULT_SENDER=info@mauzotz.com
BUSINESS_NAME=MauzoTZ
BUSINESS_EMAIL=info@mauzotz.com
UPLOAD_FOLDER=static/uploads
MAX_CONTENT_LENGTH=16777216
EOL
    
    chown www-data:www-data $APP_DIR/.env
    chmod 600 $APP_DIR/.env
    
    log_success "Environment configuration created"
}

setup_systemd_service() {
    log_info "Setting up systemd service..."
    
    cat > $SERVICE_FILE << EOL
[Unit]
Description=MauzoTZ Inventory Management System
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/gunicorn --config gunicorn.conf.py wsgi:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL
    
    systemctl daemon-reload
    systemctl enable $APP_NAME
    
    log_success "Systemd service configured"
}

setup_nginx() {
    log_info "Setting up Nginx..."
    
    cat > $NGINX_CONFIG << EOL
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss;
    
    # Static files
    location /static {
        alias $APP_DIR/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Main application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        proxy_buffering off;
    }
    
    # Security
    location ~ /\.ht {
        deny all;
    }
    
    # Limit request size
    client_max_body_size 16M;
}
EOL
    
    ln -sf $NGINX_CONFIG /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    nginx -t
    systemctl restart nginx
    systemctl enable nginx
    
    log_success "Nginx configured"
}

initialize_database() {
    log_info "Initializing database..."
    
    cd $APP_DIR
    source venv/bin/activate
    
    # Run database migrations/initialization
    python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created successfully')
"
    
    log_success "Database initialized"
}

start_services() {
    log_info "Starting services..."
    
    systemctl start $APP_NAME
    systemctl restart nginx
    
    log_success "Services started"
}

display_status() {
    echo
    log_info "Deployment Status:"
    echo "=================="
    
    systemctl is-active --quiet postgresql && log_success "PostgreSQL: Active" || log_error "PostgreSQL: Inactive"
    systemctl is-active --quiet nginx && log_success "Nginx: Active" || log_error "Nginx: Inactive"
    systemctl is-active --quiet $APP_NAME && log_success "MauzoTZ App: Active" || log_error "MauzoTZ App: Inactive"
    
    echo
    log_info "Next Steps:"
    echo "1. Update your domain in /etc/nginx/sites-available/$APP_NAME"
    echo "2. Configure SSL with: certbot --nginx -d your-domain.com"
    echo "3. Set up email credentials in $APP_DIR/.env"
    echo "4. Configure SMS credentials (Twilio) in $APP_DIR/.env"
    echo "5. Create admin user with: cd $APP_DIR && python3 create_admin_user.py"
    echo
    log_success "MauzoTZ Inventory Management System deployed successfully!"
}

# Main deployment process
main() {
    log_info "Starting MauzoTZ deployment on Ubuntu Server"
    
    check_root
    install_dependencies
    setup_postgresql
    setup_application
    setup_environment
    setup_systemd_service
    setup_nginx
    initialize_database
    start_services
    display_status
}

# Run main function
main "$@"
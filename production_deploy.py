#!/usr/bin/env python3
"""
Production deployment verification and setup script for MauzoTZ
Ensures all components are properly configured before deployment
"""

import os
import sys
import subprocess
import json
from pathlib import Path

class ProductionValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success = []
        
    def log_error(self, message):
        self.errors.append(message)
        print(f"ERROR: {message}")
        
    def log_warning(self, message):
        self.warnings.append(message)
        print(f"WARNING: {message}")
        
    def log_success(self, message):
        self.success.append(message)
        print(f"SUCCESS: {message}")
        
    def check_required_files(self):
        """Check that all required files are present"""
        required_files = [
            'app.py', 'wsgi.py', 'config.py', 'models.py',
            'routes.py', 'auth.py', 'gunicorn.conf.py',
            'production_requirements.txt', '.env.example',
            'deploy.sh', 'README.md'
        ]
        
        for file in required_files:
            if os.path.exists(file):
                self.log_success(f"Required file found: {file}")
            else:
                self.log_error(f"Missing required file: {file}")
                
    def check_directory_structure(self):
        """Verify proper directory structure"""
        required_dirs = ['templates', 'static', 'logs']
        
        for directory in required_dirs:
            path = Path(directory)
            if path.exists() and path.is_dir():
                self.log_success(f"Directory exists: {directory}")
            else:
                os.makedirs(directory, exist_ok=True)
                self.log_success(f"Created directory: {directory}")
                
    def check_environment_template(self):
        """Verify environment template has all required variables"""
        if not os.path.exists('.env.example'):
            self.log_error("Missing .env.example file")
            return
            
        required_vars = [
            'FLASK_ENV', 'SECRET_KEY', 'DATABASE_URL',
            'MAIL_SERVER', 'MAIL_USERNAME', 'MAIL_PASSWORD',
            'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN'
        ]
        
        with open('.env.example', 'r') as f:
            content = f.read()
            
        for var in required_vars:
            if var in content:
                self.log_success(f"Environment variable template found: {var}")
            else:
                self.log_warning(f"Missing environment variable template: {var}")
                
    def check_security_configuration(self):
        """Verify security settings are production-ready"""
        try:
            with open('config.py', 'r') as f:
                content = f.read()
                
            security_checks = [
                ('SESSION_COOKIE_SECURE', 'True'),
                ('SESSION_COOKIE_HTTPONLY', 'True'),
                ('WTF_CSRF_ENABLED', 'True'),
                ('FORCE_HTTPS', 'True')
            ]
            
            for setting, expected in security_checks:
                if setting in content:
                    self.log_success(f"Security setting found: {setting}")
                else:
                    self.log_warning(f"Security setting missing: {setting}")
                    
        except FileNotFoundError:
            self.log_error("config.py not found")
            
    def check_database_models(self):
        """Verify database models are properly structured"""
        try:
            # Import to check for syntax errors
            import models
            self.log_success("Database models imported successfully")
            
            # Check for required models
            required_models = ['User', 'Item', 'Sale', 'Customer']
            for model_name in required_models:
                if hasattr(models, model_name):
                    self.log_success(f"Model found: {model_name}")
                else:
                    self.log_error(f"Missing required model: {model_name}")
                    
        except ImportError as e:
            self.log_error(f"Failed to import models: {e}")
            
    def check_application_imports(self):
        """Verify all application modules can be imported"""
        modules_to_check = [
            'app', 'routes', 'auth', 'sms_service',
            'language_utils', 'currency_utils'
        ]
        
        for module in modules_to_check:
            try:
                __import__(module)
                self.log_success(f"Module imports successfully: {module}")
            except ImportError as e:
                self.log_error(f"Import error in {module}: {e}")
                
    def check_template_structure(self):
        """Verify template files are properly structured"""
        template_dirs = ['templates/auth', 'templates/sms', 'templates/accounting']
        
        for template_dir in template_dirs:
            if os.path.exists(template_dir):
                self.log_success(f"Template directory found: {template_dir}")
            else:
                self.log_warning(f"Template directory missing: {template_dir}")
                
    def clean_development_files(self):
        """Remove development-specific files"""
        dev_files = [
            'attached_assets', 'src', '.replit', 'uv.lock',
            'migrate_firebase_to_postgresql.py', 'database_inspector.py',
            'complete_data_migration.py', 'admin_routes.py'
        ]
        
        for item in dev_files:
            if os.path.exists(item):
                if os.path.isdir(item):
                    import shutil
                    shutil.rmtree(item)
                else:
                    os.remove(item)
                self.log_success(f"Removed development file/directory: {item}")
                
    def create_production_summary(self):
        """Create a deployment summary report"""
        summary = {
            'timestamp': str(subprocess.check_output(['date'], text=True).strip()),
            'total_files_checked': len(self.success) + len(self.errors) + len(self.warnings),
            'errors': self.errors,
            'warnings': self.warnings,
            'success_count': len(self.success),
            'deployment_ready': len(self.errors) == 0
        }
        
        with open('deployment_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
            
        self.log_success("Deployment summary created: deployment_summary.json")
        
    def run_validation(self):
        """Run all validation checks"""
        print("Starting MauzoTZ production deployment validation...")
        print("=" * 60)
        
        self.check_required_files()
        self.check_directory_structure()
        self.check_environment_template()
        self.check_security_configuration()
        self.check_database_models()
        self.check_application_imports()
        self.check_template_structure()
        self.clean_development_files()
        self.create_production_summary()
        
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY:")
        print(f"Successes: {len(self.success)}")
        print(f"Warnings: {len(self.warnings)}")
        print(f"Errors: {len(self.errors)}")
        
        if self.errors:
            print("\nCritical errors found. Please fix before deployment:")
            for error in self.errors:
                print(f"  - {error}")
            return False
        else:
            print("\nAll critical checks passed. Ready for deployment!")
            print("\nNext steps:")
            print("1. Copy codebase to Ubuntu server")
            print("2. Run: sudo ./deploy.sh")
            print("3. Configure domain and SSL")
            print("4. Set up environment variables")
            print("5. Create admin user")
            return True

if __name__ == "__main__":
    validator = ProductionValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)
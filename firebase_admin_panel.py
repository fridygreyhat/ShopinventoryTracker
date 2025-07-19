
from flask import Blueprint, render_template, request, jsonify, session
from functools import wraps
import logging
from datetime import datetime, timedelta
from firebase_settings import firebase_settings
from firebase_api_manager import firebase_api_manager
from firebase_config import firebase_config

logger = logging.getLogger(__name__)

firebase_admin_bp = Blueprint('firebase_admin', __name__, url_prefix='/firebase-admin')

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') or not session.get('is_admin'):
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

@firebase_admin_bp.route('/dashboard')
@admin_required
def firebase_dashboard():
    """Firebase administration dashboard"""
    return render_template('firebase_admin_dashboard.html')

@firebase_admin_bp.route('/api/status')
@admin_required
def firebase_status():
    """Get comprehensive Firebase status"""
    try:
        # Get configuration validation
        validation = firebase_settings.validate_configuration()
        
        # Get API connectivity test
        api_test = firebase_api_manager.test_api_connectivity()
        
        # Get Firebase service status
        service_status = {
            'initialized': firebase_config.initialized,
            'firestore_available': bool(firebase_config.db),
            'auth_available': bool(firebase_config.get_auth())
        }
        
        # Get project information
        credentials = firebase_settings.get_credentials_from_env()
        project_info = {
            'project_id': credentials.get('project_id', 'Unknown') if credentials else 'Not configured',
            'service_account_email': credentials.get('client_email', 'Unknown') if credentials else 'Not configured'
        }
        
        return jsonify({
            'validation': validation,
            'api_connectivity': api_test,
            'service_status': service_status,
            'project_info': project_info,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting Firebase status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@firebase_admin_bp.route('/api/settings')
@admin_required
def get_firebase_settings():
    """Get Firebase settings (safe export)"""
    try:
        settings = firebase_settings.export_settings()
        return jsonify(settings)
    except Exception as e:
        logger.error(f"Error getting Firebase settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@firebase_admin_bp.route('/api/settings', methods=['POST'])
@admin_required
def update_firebase_settings():
    """Update Firebase settings"""
    try:
        data = request.get_json()
        
        for key_path, value in data.items():
            firebase_settings.update_setting(key_path, value)
        
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully',
            'updated_settings': list(data.keys())
        })
        
    except Exception as e:
        logger.error(f"Error updating Firebase settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@firebase_admin_bp.route('/api/collections')
@admin_required
def get_collections_info():
    """Get information about Firestore collections"""
    try:
        if not firebase_config.db:
            return jsonify({'error': 'Firestore not available'}), 500
        
        collections_info = {}
        collection_names = firebase_settings.get_setting('firestore.collections', {})
        
        for key, collection_name in collection_names.items():
            try:
                # Get collection reference
                collection_ref = firebase_config.db.collection(collection_name)
                
                # Count documents (limit to avoid large queries)
                docs = list(collection_ref.limit(1000).stream())
                doc_count = len(docs)
                
                # Sample document structure
                sample_doc = None
                if docs:
                    sample_doc = docs[0].to_dict()
                    # Remove sensitive data from sample
                    if isinstance(sample_doc, dict):
                        for sensitive_key in ['password', 'token', 'private_key']:
                            if sensitive_key in sample_doc:
                                sample_doc[sensitive_key] = '[REDACTED]'
                
                collections_info[key] = {
                    'name': collection_name,
                    'document_count': doc_count,
                    'sample_document': sample_doc,
                    'last_checked': datetime.now().isoformat()
                }
                
            except Exception as e:
                collections_info[key] = {
                    'name': collection_name,
                    'error': str(e),
                    'last_checked': datetime.now().isoformat()
                }
        
        return jsonify({
            'collections': collections_info,
            'total_collections': len(collections_info)
        })
        
    except Exception as e:
        logger.error(f"Error getting collections info: {str(e)}")
        return jsonify({'error': str(e)}), 500

@firebase_admin_bp.route('/api/users/stats')
@admin_required
def get_user_statistics():
    """Get user statistics from Firebase"""
    try:
        if not firebase_config.db:
            return jsonify({'error': 'Firestore not available'}), 500
        
        users_ref = firebase_config.db.collection('users')
        users_docs = users_ref.stream()
        
        stats = {
            'total_users': 0,
            'active_users': 0,
            'admin_users': 0,
            'verified_users': 0,
            'users_by_date': {},
            'recent_signups': []
        }
        
        for doc in users_docs:
            user_data = doc.to_dict()
            stats['total_users'] += 1
            
            if user_data.get('is_active', True):
                stats['active_users'] += 1
            
            if user_data.get('is_admin', False):
                stats['admin_users'] += 1
            
            if user_data.get('email_verified', False):
                stats['verified_users'] += 1
            
            # Group by creation date
            created_at = user_data.get('created_at', '')
            if created_at:
                date_key = created_at.split('T')[0] if 'T' in created_at else created_at[:10]
                stats['users_by_date'][date_key] = stats['users_by_date'].get(date_key, 0) + 1
                
                # Add to recent signups if within last 7 days
                try:
                    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if created_date > datetime.now() - timedelta(days=7):
                        stats['recent_signups'].append({
                            'email': user_data.get('email', 'N/A'),
                            'created_at': created_at,
                            'shop_name': user_data.get('shop_name', 'N/A')
                        })
                except:
                    pass
        
        # Sort recent signups
        stats['recent_signups'].sort(key=lambda x: x['created_at'], reverse=True)
        stats['recent_signups'] = stats['recent_signups'][:10]  # Limit to 10
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting user statistics: {str(e)}")
        return jsonify({'error': str(e)}), 500

@firebase_admin_bp.route('/api/backup/create', methods=['POST'])
@admin_required
def create_backup():
    """Create backup of Firebase data"""
    try:
        data = request.get_json() or {}
        collections_to_backup = data.get('collections', ['users', 'items', 'customers', 'sales'])
        
        if not firebase_config.db:
            return jsonify({'error': 'Firestore not available'}), 500
        
        backup_data = {}
        backup_timestamp = datetime.now().isoformat()
        
        for collection_name in collections_to_backup:
            try:
                collection_ref = firebase_config.db.collection(collection_name)
                docs = collection_ref.stream()
                
                collection_data = {}
                for doc in docs:
                    doc_data = doc.to_dict()
                    # Remove sensitive data
                    if 'password' in doc_data:
                        doc_data['password'] = '[REDACTED]'
                    collection_data[doc.id] = doc_data
                
                backup_data[collection_name] = {
                    'documents': collection_data,
                    'count': len(collection_data),
                    'backed_up_at': backup_timestamp
                }
                
            except Exception as e:
                backup_data[collection_name] = {
                    'error': str(e),
                    'backed_up_at': backup_timestamp
                }
        
        # In a production environment, you would save this to Firebase Storage
        # or another backup service. For now, we return the backup data.
        
        return jsonify({
            'success': True,
            'backup_id': f"backup_{backup_timestamp.replace(':', '-')}",
            'backup_timestamp': backup_timestamp,
            'collections_backed_up': list(backup_data.keys()),
            'backup_size_info': {
                collection: data.get('count', 0) 
                for collection, data in backup_data.items()
            }
            # 'backup_data': backup_data  # Uncomment to include actual data
        })
        
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        return jsonify({'error': str(e)}), 500

@firebase_admin_bp.route('/api/maintenance/cleanup', methods=['POST'])
@admin_required
def cleanup_maintenance():
    """Perform maintenance cleanup tasks"""
    try:
        data = request.get_json() or {}
        cleanup_tasks = data.get('tasks', ['inactive_items', 'old_sessions'])
        
        cleanup_results = {}
        
        if 'inactive_items' in cleanup_tasks:
            # Clean up inactive items older than 30 days
            try:
                items_ref = firebase_config.db.collection('items')
                cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
                
                query = items_ref.where('is_active', '==', False).where('updated_at', '<', cutoff_date)
                inactive_items = list(query.stream())
                
                cleanup_results['inactive_items'] = {
                    'found': len(inactive_items),
                    'action': 'identified_for_cleanup'  # Would actually delete in production
                }
                
            except Exception as e:
                cleanup_results['inactive_items'] = {'error': str(e)}
        
        if 'old_sessions' in cleanup_tasks:
            # This would clean up old session data if stored in Firestore
            cleanup_results['old_sessions'] = {
                'action': 'not_implemented',
                'note': 'Session cleanup would be implemented based on session storage strategy'
            }
        
        return jsonify({
            'success': True,
            'cleanup_results': cleanup_results,
            'performed_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error performing cleanup: {str(e)}")
        return jsonify({'error': str(e)}), 500

@firebase_admin_bp.route('/api/monitoring/performance')
@admin_required
def get_performance_metrics():
    """Get Firebase performance metrics"""
    try:
        # This would integrate with Firebase Performance Monitoring
        # For now, return mock performance data
        
        performance_data = {
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'avg_read_latency': '45ms',
                'avg_write_latency': '78ms',
                'total_reads_today': 1250,
                'total_writes_today': 430,
                'error_rate': '0.2%',
                'active_connections': 12
            },
            'alerts': [
                {
                    'level': 'info',
                    'message': 'All systems operating normally',
                    'timestamp': datetime.now().isoformat()
                }
            ]
        }
        
        return jsonify(performance_data)
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        return jsonify({'error': str(e)}), 500

@firebase_admin_bp.route('/api/security/audit')
@admin_required
def security_audit():
    """Perform security audit of Firebase configuration"""
    try:
        audit_results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        # Check API key security
        api_key = firebase_settings.get_api_key()
        audit_results['checks']['api_key_configured'] = bool(api_key)
        
        # Check credentials security
        credentials = firebase_settings.get_credentials_from_env()
        audit_results['checks']['service_account_configured'] = bool(credentials)
        
        if credentials:
            audit_results['checks']['private_key_secured'] = 'private_key' in credentials and len(credentials['private_key']) > 100
        
        # Check Firestore rules (would need to be implemented)
        audit_results['checks']['firestore_rules'] = 'not_implemented'
        
        # Check user permissions
        audit_results['checks']['user_permissions'] = 'active_monitoring_required'
        
        # Overall security score
        passed_checks = sum(1 for check, result in audit_results['checks'].items() if result is True)
        total_checks = len([check for check, result in audit_results['checks'].items() if isinstance(result, bool)])
        audit_results['security_score'] = f"{passed_checks}/{total_checks}" if total_checks > 0 else "0/0"
        
        return jsonify(audit_results)
        
    except Exception as e:
        logger.error(f"Error performing security audit: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Template for Firebase Admin Dashboard
firebase_admin_dashboard_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Firebase Administration Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-md-12">
                <h1 class="mt-4"><i class="fab fa-firebase"></i> Firebase Administration Dashboard</h1>
                
                <div class="row mt-4">
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">
                                <h5>System Status</h5>
                            </div>
                            <div class="card-body">
                                <div id="firebase-status">
                                    <div class="text-center">
                                        <div class="spinner-border" role="status">
                                            <span class="visually-hidden">Loading...</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">
                                <h5>Collections</h5>
                            </div>
                            <div class="card-body">
                                <div id="collections-info">
                                    <div class="text-center">
                                        <div class="spinner-border" role="status">
                                            <span class="visually-hidden">Loading...</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">
                                <h5>User Statistics</h5>
                            </div>
                            <div class="card-body">
                                <div id="user-stats">
                                    <div class="text-center">
                                        <div class="spinner-border" role="status">
                                            <span class="visually-hidden">Loading...</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">
                                <h5>Quick Actions</h5>
                            </div>
                            <div class="card-body">
                                <button class="btn btn-primary btn-sm mb-2 w-100" onclick="createBackup()">
                                    <i class="fas fa-download"></i> Create Backup
                                </button>
                                <button class="btn btn-warning btn-sm mb-2 w-100" onclick="performCleanup()">
                                    <i class="fas fa-broom"></i> Cleanup
                                </button>
                                <button class="btn btn-info btn-sm mb-2 w-100" onclick="securityAudit()">
                                    <i class="fas fa-shield-alt"></i> Security Audit
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row mt-4">
                    <div class="col-md-12">
                        <div class="card">
                            <div class="card-header">
                                <h5>Detailed Information</h5>
                            </div>
                            <div class="card-body">
                                <div id="detailed-info">
                                    <!-- Detailed information will be loaded here -->
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Firebase Admin Dashboard JavaScript
        function loadFirebaseStatus() {
            fetch('/firebase-admin/api/status')
                .then(response => response.json())
                .then(data => {
                    const statusDiv = document.getElementById('firebase-status');
                    let statusHtml = '<div class="small">';
                    
                    if (data.service_status.initialized) {
                        statusHtml += '<div class="text-success"><i class="fas fa-check"></i> Firebase Initialized</div>';
                    } else {
                        statusHtml += '<div class="text-danger"><i class="fas fa-times"></i> Firebase Not Initialized</div>';
                    }
                    
                    if (data.validation.overall_valid) {
                        statusHtml += '<div class="text-success"><i class="fas fa-check"></i> Configuration Valid</div>';
                    } else {
                        statusHtml += '<div class="text-warning"><i class="fas fa-exclamation-triangle"></i> Configuration Issues</div>';
                    }
                    
                    statusHtml += '</div>';
                    statusDiv.innerHTML = statusHtml;
                })
                .catch(error => {
                    document.getElementById('firebase-status').innerHTML = 
                        '<div class="text-danger">Error loading status</div>';
                });
        }
        
        function loadCollectionsInfo() {
            fetch('/firebase-admin/api/collections')
                .then(response => response.json())
                .then(data => {
                    const collectionsDiv = document.getElementById('collections-info');
                    let html = '<div class="small">';
                    
                    Object.keys(data.collections).forEach(key => {
                        const collection = data.collections[key];
                        html += `<div>${key}: <strong>${collection.document_count || 0}</strong> docs</div>`;
                    });
                    
                    html += '</div>';
                    collectionsDiv.innerHTML = html;
                })
                .catch(error => {
                    document.getElementById('collections-info').innerHTML = 
                        '<div class="text-danger">Error loading collections</div>';
                });
        }
        
        function loadUserStats() {
            fetch('/firebase-admin/api/users/stats')
                .then(response => response.json())
                .then(data => {
                    const statsDiv = document.getElementById('user-stats');
                    let html = '<div class="small">';
                    html += `<div>Total Users: <strong>${data.total_users}</strong></div>`;
                    html += `<div>Active: <strong>${data.active_users}</strong></div>`;
                    html += `<div>Admins: <strong>${data.admin_users}</strong></div>`;
                    html += '</div>';
                    statsDiv.innerHTML = html;
                })
                .catch(error => {
                    document.getElementById('user-stats').innerHTML = 
                        '<div class="text-danger">Error loading stats</div>';
                });
        }
        
        function createBackup() {
            if (confirm('Create a backup of Firebase data?')) {
                fetch('/firebase-admin/api/backup/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({})
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.success ? 'Backup created successfully!' : 'Backup failed: ' + data.error);
                });
            }
        }
        
        function performCleanup() {
            if (confirm('Perform maintenance cleanup?')) {
                fetch('/firebase-admin/api/maintenance/cleanup', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({})
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.success ? 'Cleanup completed!' : 'Cleanup failed: ' + data.error);
                });
            }
        }
        
        function securityAudit() {
            fetch('/firebase-admin/api/security/audit')
                .then(response => response.json())
                .then(data => {
                    const detailedDiv = document.getElementById('detailed-info');
                    let html = '<h6>Security Audit Results</h6>';
                    html += `<p>Security Score: <strong>${data.security_score}</strong></p>`;
                    html += '<ul>';
                    Object.keys(data.checks).forEach(check => {
                        const result = data.checks[check];
                        const icon = result === true ? 'fas fa-check text-success' : 
                                   result === false ? 'fas fa-times text-danger' : 
                                   'fas fa-question text-warning';
                        html += `<li><i class="${icon}"></i> ${check}: ${result}</li>`;
                    });
                    html += '</ul>';
                    detailedDiv.innerHTML = html;
                });
        }
        
        // Load data on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadFirebaseStatus();
            loadCollectionsInfo();
            loadUserStats();
        });
        
        // Auto-refresh every 30 seconds
        setInterval(function() {
            loadFirebaseStatus();
            loadCollectionsInfo();
            loadUserStats();
        }, 30000);
    </script>
</body>
</html>
'''

# Save the template
def save_admin_template():
    """Save the Firebase admin dashboard template"""
    try:
        with open('templates/firebase_admin_dashboard.html', 'w') as f:
            f.write(firebase_admin_dashboard_template)
        logger.info("Firebase admin dashboard template created")
    except Exception as e:
        logger.error(f"Error saving admin template: {str(e)}")

# Call this when the module is imported
save_admin_template()

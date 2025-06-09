"""
Language switching routes for the business management system
"""

from flask import Blueprint, request, redirect, url_for, jsonify, session
from language_utils import set_language, get_current_language, SUPPORTED_LANGUAGES

language_bp = Blueprint('language', __name__, url_prefix='/language')

@language_bp.route('/switch/<language_code>')
def switch_language(language_code):
    """Switch application language"""
    if set_language(language_code):
        # Redirect back to the referring page or dashboard
        return redirect(request.referrer or url_for('dashboard'))
    else:
        # Invalid language code, redirect to dashboard
        return redirect(url_for('dashboard'))

@language_bp.route('/current')
def current_language():
    """Get current language as JSON"""
    return jsonify({
        'current': get_current_language(),
        'supported': SUPPORTED_LANGUAGES
    })

@language_bp.route('/api/switch', methods=['POST'])
def api_switch_language():
    """API endpoint to switch language via AJAX"""
    data = request.get_json()
    language_code = data.get('language')
    
    if set_language(language_code):
        return jsonify({
            'success': True,
            'language': language_code,
            'message': 'Language switched successfully'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Invalid language code'
        }), 400
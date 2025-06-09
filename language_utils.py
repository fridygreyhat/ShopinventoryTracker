"""
Language utilities for the business management system
Handles language detection, switching, and template context
"""

from flask import session, request, g
from translations import get_translation, get_all_translations

# Supported languages
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'sw': 'Kiswahili'
}

def get_current_language():
    """Get the current language from session or default to English"""
    return session.get('language', 'en')

def set_language(language_code):
    """Set the current language in session"""
    if language_code in SUPPORTED_LANGUAGES:
        session['language'] = language_code
        return True
    return False

def detect_browser_language():
    """Detect language from browser Accept-Language header"""
    if request.headers.get('Accept-Language'):
        # Simple detection - look for 'sw' (Swahili) in accept languages
        accept_languages = request.headers.get('Accept-Language', '').lower()
        if 'sw' in accept_languages:
            return 'sw'
    return 'en'

def init_language_context():
    """Initialize language context for templates"""
    # Get current language
    current_lang = get_current_language()
    
    # Set global template variables
    g.current_language = current_lang
    g.supported_languages = SUPPORTED_LANGUAGES
    g.t = lambda key: get_translation(key, current_lang)
    g.translations = get_all_translations(current_lang)

def translate(key, language=None):
    """Translate a key using current or specified language"""
    if language is None:
        language = get_current_language()
    return get_translation(key, language)

# Template filter for translations
def translate_filter(key):
    """Jinja2 filter for translations"""
    return translate(key)
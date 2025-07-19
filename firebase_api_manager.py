
import requests
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from firebase_settings import firebase_settings

logger = logging.getLogger(__name__)

class FirebaseAPIManager:
    """Comprehensive Firebase API management system"""
    
    def __init__(self):
        self.settings = firebase_settings
        self.base_urls = {
            'auth': 'https://identitytoolkit.googleapis.com/v1',
            'firestore': 'https://firestore.googleapis.com/v1',
            'storage': 'https://firebasestorage.googleapis.com/v0',
            'functions': 'https://cloudfunctions.googleapis.com/v1',
            'messaging': 'https://fcm.googleapis.com/v1'
        }
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """Setup HTTP session with default headers"""
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def get_auth_headers(self, include_api_key: bool = True) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        headers = {}
        
        if include_api_key:
            api_key = self.settings.get_api_key()
            if api_key:
                headers['X-Firebase-API-Key'] = api_key
        
        return headers
    
    # Firebase Authentication API Methods
    def create_user_with_email(self, email: str, password: str, display_name: str = '') -> Dict[str, Any]:
        """Create user using Firebase Auth REST API"""
        api_key = self.settings.get_api_key()
        if not api_key:
            raise ValueError("Firebase API key not configured")
        
        url = f"{self.base_urls['auth']}/accounts:signUp?key={api_key}"
        payload = {
            'email': email,
            'password': password,
            'displayName': display_name,
            'returnSecureToken': True
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating user: {str(e)}")
            raise
    
    def sign_in_with_email(self, email: str, password: str) -> Dict[str, Any]:
        """Sign in user using Firebase Auth REST API"""
        api_key = self.settings.get_api_key()
        if not api_key:
            raise ValueError("Firebase API key not configured")
        
        url = f"{self.base_urls['auth']}/accounts:signInWithPassword?key={api_key}"
        payload = {
            'email': email,
            'password': password,
            'returnSecureToken': True
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error signing in user: {str(e)}")
            raise
    
    def refresh_id_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh ID token using refresh token"""
        api_key = self.settings.get_api_key()
        if not api_key:
            raise ValueError("Firebase API key not configured")
        
        url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise
    
    def send_password_reset_email(self, email: str) -> Dict[str, Any]:
        """Send password reset email"""
        api_key = self.settings.get_api_key()
        if not api_key:
            raise ValueError("Firebase API key not configured")
        
        url = f"{self.base_urls['auth']}/accounts:sendOobCode?key={api_key}"
        payload = {
            'requestType': 'PASSWORD_RESET',
            'email': email
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending password reset: {str(e)}")
            raise
    
    def verify_id_token(self, id_token: str) -> Dict[str, Any]:
        """Verify Firebase ID token"""
        api_key = self.settings.get_api_key()
        if not api_key:
            raise ValueError("Firebase API key not configured")
        
        url = f"{self.base_urls['auth']}/accounts:lookup?key={api_key}"
        payload = {
            'idToken': id_token
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error verifying token: {str(e)}")
            raise
    
    # Firestore API Methods
    def create_firestore_document(self, collection: str, document_id: str, data: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        """Create document in Firestore using REST API"""
        credentials = self.settings.get_credentials_from_env()
        if not credentials:
            raise ValueError("Firebase credentials not configured")
        
        project_id = credentials.get('project_id')
        url = f"{self.base_urls['firestore']}/projects/{project_id}/databases/(default)/documents/{collection}/{document_id}"
        
        headers = self.get_auth_headers()
        headers['Authorization'] = f'Bearer {access_token}'
        
        # Convert data to Firestore format
        firestore_data = {'fields': self._convert_to_firestore_format(data)}
        
        try:
            response = self.session.patch(url, json=firestore_data, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating Firestore document: {str(e)}")
            raise
    
    def get_firestore_document(self, collection: str, document_id: str, access_token: str) -> Dict[str, Any]:
        """Get document from Firestore using REST API"""
        credentials = self.settings.get_credentials_from_env()
        if not credentials:
            raise ValueError("Firebase credentials not configured")
        
        project_id = credentials.get('project_id')
        url = f"{self.base_urls['firestore']}/projects/{project_id}/databases/(default)/documents/{collection}/{document_id}"
        
        headers = self.get_auth_headers()
        headers['Authorization'] = f'Bearer {access_token}'
        
        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            return self._convert_from_firestore_format(response.json())
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting Firestore document: {str(e)}")
            raise
    
    def query_firestore_collection(self, collection: str, filters: List[Dict], access_token: str) -> List[Dict[str, Any]]:
        """Query Firestore collection using REST API"""
        credentials = self.settings.get_credentials_from_env()
        if not credentials:
            raise ValueError("Firebase credentials not configured")
        
        project_id = credentials.get('project_id')
        url = f"{self.base_urls['firestore']}/projects/{project_id}/databases/(default)/documents:runQuery"
        
        headers = self.get_auth_headers()
        headers['Authorization'] = f'Bearer {access_token}'
        
        # Build query
        query = {
            'structuredQuery': {
                'from': [{'collectionId': collection}],
                'where': self._build_firestore_filters(filters)
            }
        }
        
        try:
            response = self.session.post(url, json=query, headers=headers)
            response.raise_for_status()
            
            results = []
            for item in response.json():
                if 'document' in item:
                    results.append(self._convert_from_firestore_format(item['document']))
            
            return results
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying Firestore: {str(e)}")
            raise
    
    # Firebase Storage API Methods
    def upload_file_to_storage(self, file_path: str, file_data: bytes, content_type: str, access_token: str) -> Dict[str, Any]:
        """Upload file to Firebase Storage"""
        credentials = self.settings.get_credentials_from_env()
        if not credentials:
            raise ValueError("Firebase credentials not configured")
        
        project_id = credentials.get('project_id')
        bucket = f"{project_id}.appspot.com"
        url = f"{self.base_urls['storage']}/b/{bucket}/o?uploadType=media&name={file_path}"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': content_type
        }
        
        try:
            response = self.session.post(url, data=file_data, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise
    
    def get_file_download_url(self, file_path: str, access_token: str) -> str:
        """Get download URL for file in Firebase Storage"""
        credentials = self.settings.get_credentials_from_env()
        if not credentials:
            raise ValueError("Firebase credentials not configured")
        
        project_id = credentials.get('project_id')
        bucket = f"{project_id}.appspot.com"
        url = f"{self.base_urls['storage']}/b/{bucket}/o/{file_path}"
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get('downloadURL', '')
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting download URL: {str(e)}")
            raise
    
    # Firebase Cloud Messaging API Methods
    def send_push_notification(self, token: str, title: str, body: str, data: Dict = None, access_token: str = None) -> Dict[str, Any]:
        """Send push notification via FCM"""
        credentials = self.settings.get_credentials_from_env()
        if not credentials:
            raise ValueError("Firebase credentials not configured")
        
        project_id = credentials.get('project_id')
        url = f"{self.base_urls['messaging']}/projects/{project_id}/messages:send"
        
        headers = self.get_auth_headers()
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'
        
        message = {
            'message': {
                'token': token,
                'notification': {
                    'title': title,
                    'body': body
                }
            }
        }
        
        if data:
            message['message']['data'] = data
        
        try:
            response = self.session.post(url, json=message, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending notification: {str(e)}")
            raise
    
    # Helper Methods
    def _convert_to_firestore_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Python dict to Firestore field format"""
        converted = {}
        for key, value in data.items():
            if isinstance(value, str):
                converted[key] = {'stringValue': value}
            elif isinstance(value, int):
                converted[key] = {'integerValue': str(value)}
            elif isinstance(value, float):
                converted[key] = {'doubleValue': value}
            elif isinstance(value, bool):
                converted[key] = {'booleanValue': value}
            elif isinstance(value, datetime):
                converted[key] = {'timestampValue': value.isoformat()}
            elif isinstance(value, dict):
                converted[key] = {'mapValue': {'fields': self._convert_to_firestore_format(value)}}
            elif isinstance(value, list):
                array_values = []
                for item in value:
                    if isinstance(item, dict):
                        array_values.append({'mapValue': {'fields': self._convert_to_firestore_format(item)}})
                    else:
                        array_values.append(self._convert_to_firestore_format({'temp': item})['temp'])
                converted[key] = {'arrayValue': {'values': array_values}}
            else:
                converted[key] = {'stringValue': str(value)}
        return converted
    
    def _convert_from_firestore_format(self, firestore_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Firestore document to Python dict"""
        if 'fields' not in firestore_doc:
            return firestore_doc
        
        converted = {}
        for key, field in firestore_doc['fields'].items():
            if 'stringValue' in field:
                converted[key] = field['stringValue']
            elif 'integerValue' in field:
                converted[key] = int(field['integerValue'])
            elif 'doubleValue' in field:
                converted[key] = field['doubleValue']
            elif 'booleanValue' in field:
                converted[key] = field['booleanValue']
            elif 'timestampValue' in field:
                converted[key] = field['timestampValue']
            elif 'mapValue' in field:
                converted[key] = self._convert_from_firestore_format(field['mapValue'])
            elif 'arrayValue' in field:
                array_items = []
                for item in field['arrayValue'].get('values', []):
                    if 'mapValue' in item:
                        array_items.append(self._convert_from_firestore_format(item['mapValue']))
                    else:
                        # Handle primitive values in array
                        for val_type, val in item.items():
                            if val_type == 'stringValue':
                                array_items.append(val)
                            elif val_type == 'integerValue':
                                array_items.append(int(val))
                            elif val_type == 'doubleValue':
                                array_items.append(val)
                            elif val_type == 'booleanValue':
                                array_items.append(val)
                converted[key] = array_items
        
        return converted
    
    def _build_firestore_filters(self, filters: List[Dict]) -> Dict[str, Any]:
        """Build Firestore query filters"""
        if not filters:
            return {}
        
        filter_conditions = []
        for filter_item in filters:
            condition = {
                'fieldFilter': {
                    'field': {'fieldPath': filter_item['field']},
                    'op': filter_item.get('op', 'EQUAL'),
                    'value': self._convert_to_firestore_format({'temp': filter_item['value']})['temp']
                }
            }
            filter_conditions.append(condition)
        
        if len(filter_conditions) == 1:
            return filter_conditions[0]
        else:
            return {
                'compositeFilter': {
                    'op': 'AND',
                    'filters': filter_conditions
                }
            }
    
    def test_api_connectivity(self) -> Dict[str, Any]:
        """Test Firebase API connectivity"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {}
        }
        
        # Test API key availability
        api_key = self.settings.get_api_key()
        results['tests']['api_key_available'] = bool(api_key)
        
        # Test credentials availability
        credentials = self.settings.get_credentials_from_env()
        results['tests']['credentials_available'] = bool(credentials)
        
        # Test Auth API
        if api_key:
            try:
                url = f"{self.base_urls['auth']}/accounts:lookup?key={api_key}"
                response = self.session.post(url, json={'idToken': 'test_token'})
                results['tests']['auth_api_accessible'] = response.status_code in [400, 401]  # Expected for invalid token
            except Exception as e:
                results['tests']['auth_api_accessible'] = False
                results['tests']['auth_api_error'] = str(e)
        
        # Test overall status
        results['overall_status'] = all([
            results['tests'].get('api_key_available', False),
            results['tests'].get('credentials_available', False)
        ])
        
        return results

# Global Firebase API manager instance
firebase_api_manager = FirebaseAPIManager()

def get_firebase_api_manager() -> FirebaseAPIManager:
    """Get global Firebase API manager instance"""
    return firebase_api_manager

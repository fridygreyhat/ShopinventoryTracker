
#!/usr/bin/env python3
"""
Firebase Database Configuration Checker
Run this script to get a comprehensive overview of your Firebase setup
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from firebase_config_viewer import display_firebase_configuration, get_firebase_configuration_json
import json

def main():
    print("🔥 Firebase Database Configuration Checker")
    print("=" * 50)
    print()
    
    try:
        # Display human-readable configuration
        config = display_firebase_configuration()
        
        # Optional: Save to JSON file
        print("\n💾 Saving detailed configuration to 'firebase_config_report.json'...")
        with open('firebase_config_report.json', 'w') as f:
            json.dump(config, f, indent=2)
        print("✅ Configuration report saved!")
        
        # Quick status summary
        print("\n📊 QUICK STATUS SUMMARY:")
        
        env_vars = config.get('environment_variables', {})
        creds_present = env_vars.get('FIREBASE_CREDENTIALS', {}).get('present', False)
        creds_valid = env_vars.get('FIREBASE_CREDENTIALS', {}).get('valid_json', False)
        api_key_present = env_vars.get('FIREBASE_API_KEY', {}).get('present', False)
        
        init_status = config.get('initialization_status', {})
        firebase_init = init_status.get('firebase_admin_initialized', False)
        firestore_available = init_status.get('firestore_db_available', False)
        auth_available = init_status.get('auth_module_available', False)
        
        project_info = config.get('project_information', {})
        project_configured = 'error' not in project_info
        
        api_test = config.get('api_connectivity', {})
        api_connected = api_test.get('overall_status', False)
        
        overall_health = all([
            creds_present,
            creds_valid,
            api_key_present,
            firebase_init,
            firestore_available,
            auth_available,
            project_configured,
            api_connected
        ])
        
        print(f"🟢 Overall Health: {'EXCELLENT' if overall_health else 'NEEDS ATTENTION'}")
        print(f"🔑 Credentials: {'✅ Valid' if creds_present and creds_valid else '❌ Issues'}")
        print(f"🔐 API Key: {'✅ Present' if api_key_present else '❌ Missing'}")
        print(f"🚀 Firebase Init: {'✅ Success' if firebase_init else '❌ Failed'}")
        print(f"🗄️ Firestore: {'✅ Available' if firestore_available else '❌ Unavailable'}")
        print(f"👤 Auth: {'✅ Available' if auth_available else '❌ Unavailable'}")
        print(f"📋 Project: {'✅ Configured' if project_configured else '❌ Not configured'}")
        print(f"🌐 API: {'✅ Connected' if api_connected else '❌ Connection issues'}")
        
        if not overall_health:
            print("\n🔧 RECOMMENDED ACTIONS:")
            
            if not creds_present:
                print("  1. Add FIREBASE_CREDENTIALS environment variable")
                print("     - Get service account JSON from Firebase Console")
                print("     - Add to Replit Secrets as FIREBASE_CREDENTIALS")
            
            if not creds_valid and creds_present:
                print("  2. Fix FIREBASE_CREDENTIALS JSON format")
                print("     - Ensure valid JSON syntax")
                print("     - Check for missing quotes or commas")
            
            if not api_key_present:
                print("  3. Add FIREBASE_API_KEY environment variable")
                print("     - Get Web API key from Firebase Console")
                print("     - Add to Replit Secrets as FIREBASE_API_KEY")
            
            if not firebase_init:
                print("  4. Check Firebase initialization")
                print("     - Restart the application")
                print("     - Check logs for initialization errors")
            
            if not api_connected:
                print("  5. Check network connectivity")
                print("     - Verify Firebase project is active")
                print("     - Check API quotas and billing")
        
    except Exception as e:
        print(f"❌ Error checking Firebase configuration: {str(e)}")
        print("\nThis might indicate that Firebase is not properly set up.")
        print("Please check your Firebase credentials and try again.")

if __name__ == "__main__":
    main()

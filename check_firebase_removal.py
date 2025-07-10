
#!/usr/bin/env python3
"""
Script to check for any remaining Firebase references in the codebase
"""

import os
import re

def scan_files_for_firebase():
    """Scan all Python files for Firebase references"""
    firebase_patterns = [
        r'firebase',
        r'Firebase',
        r'FIREBASE',
        r'firebase_admin',
        r'firebase_uid',
        r'firestore',
        r'auth\.create_user',
        r'auth\.get_user'
    ]
    
    python_files = []
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        if any(skip_dir in root for skip_dir in ['.git', '__pycache__', 'node_modules', '.env']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    firebase_references = []
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    for pattern in firebase_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            firebase_references.append({
                                'file': file_path,
                                'line': line_num,
                                'content': line.strip(),
                                'pattern': pattern
                            })
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    return firebase_references

def check_environment_variables():
    """Check for Firebase-related environment variables"""
    firebase_env_vars = []
    
    # Check .env file if it exists
    if os.path.exists('.env'):
        try:
            with open('.env', 'r') as f:
                lines = f.readlines()
                for line_num, line in enumerate(lines, 1):
                    if 'firebase' in line.lower() or 'FIREBASE' in line:
                        firebase_env_vars.append({
                            'file': '.env',
                            'line': line_num,
                            'content': line.strip()
                        })
        except Exception as e:
            print(f"Error reading .env file: {e}")
    
    return firebase_env_vars

def main():
    """Main function to check for Firebase references"""
    print("Firebase Reference Removal Verification")
    print("=" * 50)
    
    print("\n🔍 Scanning Python files for Firebase references...")
    firebase_refs = scan_files_for_firebase()
    
    if firebase_refs:
        print(f"⚠️ Found {len(firebase_refs)} Firebase references:")
        for ref in firebase_refs:
            print(f"   📁 {ref['file']}:{ref['line']}")
            print(f"      {ref['content']}")
            print(f"      Pattern: {ref['pattern']}")
            print()
    else:
        print("✅ No Firebase references found in Python files!")
    
    print("\n🔍 Checking environment variables...")
    firebase_env_vars = check_environment_variables()
    
    if firebase_env_vars:
        print(f"⚠️ Found {len(firebase_env_vars)} Firebase environment variables:")
        for var in firebase_env_vars:
            print(f"   📁 {var['file']}:{var['line']}")
            print(f"      {var['content']}")
            print()
    else:
        print("✅ No Firebase environment variables found!")
    
    print("\n🔍 Checking for configuration files...")
    config_files = [
        'firebase-adminsdk.json',
        'serviceAccountKey.json',
        'firebase-config.json',
        'google-services.json'
    ]
    
    found_config_files = []
    for config_file in config_files:
        if os.path.exists(config_file):
            found_config_files.append(config_file)
    
    if found_config_files:
        print(f"⚠️ Found {len(found_config_files)} Firebase configuration files:")
        for file in found_config_files:
            print(f"   📁 {file}")
            print("   🗑️ Consider removing this file")
    else:
        print("✅ No Firebase configuration files found!")
    
    print("\n" + "=" * 50)
    
    if not firebase_refs and not firebase_env_vars and not found_config_files:
        print("🎉 SUCCESS: All Firebase references have been removed!")
        print("📊 Your application is now using PostgreSQL exclusively")
    else:
        total_issues = len(firebase_refs) + len(firebase_env_vars) + len(found_config_files)
        print(f"⚠️ Found {total_issues} Firebase-related items that should be addressed")
        print("🔧 Please review and remove the items listed above")

if __name__ == "__main__":
    main()

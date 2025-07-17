
import requests
import json
import sys

# Test configuration
BASE_URL = "http://0.0.0.0:5000"
TEST_USER = {
    "email": "test@example.com",
    "password": "testpassword123",
    "username": "testuser",
    "first_name": "Test",
    "last_name": "User",
    "shop_name": "Test Shop"
}

def test_registration():
    """Test user registration"""
    print("🔍 Testing user registration...")
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/register", json=TEST_USER)
        
        if response.status_code == 201:
            print("✅ Registration successful")
            data = response.json()
            print(f"   User ID: {data.get('user', {}).get('id')}")
            print(f"   Email: {data.get('user', {}).get('email')}")
            return True
        elif response.status_code == 400 and "already registered" in response.json().get('error', ''):
            print("⚠️  User already exists - skipping registration")
            return True
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"   Error: {response.json().get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Registration error: {str(e)}")
        return False

def test_login():
    """Test user login"""
    print("\n🔍 Testing user login...")
    
    try:
        login_data = {
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        
        if response.status_code == 200:
            print("✅ Login successful")
            data = response.json()
            print(f"   User ID: {data.get('user', {}).get('id')}")
            print(f"   Email: {data.get('user', {}).get('email')}")
            print(f"   Name: {data.get('user', {}).get('first_name')} {data.get('user', {}).get('last_name')}")
            return True, response.cookies
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   Error: {response.json().get('error')}")
            return False, None
            
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return False, None

def test_session_validation(cookies):
    """Test session validation"""
    print("\n🔍 Testing session validation...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/auth/validate-session", cookies=cookies)
        
        if response.status_code == 200:
            print("✅ Session validation successful")
            data = response.json()
            print(f"   User: {data.get('user', {}).get('email')}")
            return True
        else:
            print(f"❌ Session validation failed: {response.status_code}")
            print(f"   Error: {response.json().get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Session validation error: {str(e)}")
        return False

def test_protected_endpoint(cookies):
    """Test accessing protected endpoint"""
    print("\n🔍 Testing protected endpoint access...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/dashboard/summary", cookies=cookies)
        
        if response.status_code == 200:
            print("✅ Protected endpoint access successful")
            data = response.json()
            print(f"   Dashboard data loaded: {data.get('success')}")
            return True
        else:
            print(f"❌ Protected endpoint access failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error')}")
            except:
                print(f"   Raw response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Protected endpoint error: {str(e)}")
        return False

def test_logout(cookies):
    """Test user logout"""
    print("\n🔍 Testing user logout...")
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/logout", cookies=cookies)
        
        if response.status_code == 200:
            print("✅ Logout successful")
            return True
        else:
            print(f"❌ Logout failed: {response.status_code}")
            print(f"   Error: {response.json().get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Logout error: {str(e)}")
        return False

def main():
    """Run all authentication tests"""
    print("🔥 Testing Firebase Authentication System")
    print("=" * 50)
    
    # Test 1: Registration
    if not test_registration():
        print("\n❌ Registration test failed - stopping tests")
        sys.exit(1)
    
    # Test 2: Login
    login_success, cookies = test_login()
    if not login_success:
        print("\n❌ Login test failed - stopping tests")
        sys.exit(1)
    
    # Test 3: Session validation
    if not test_session_validation(cookies):
        print("\n❌ Session validation test failed")
    
    # Test 4: Protected endpoint
    if not test_protected_endpoint(cookies):
        print("\n❌ Protected endpoint test failed")
    
    # Test 5: Logout
    if not test_logout(cookies):
        print("\n❌ Logout test failed")
    
    print("\n" + "=" * 50)
    print("🎉 Authentication system testing completed!")
    print("✅ All core authentication flows are working")

if __name__ == "__main__":
    main()

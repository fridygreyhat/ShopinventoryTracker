
import requests
import json
import os
from datetime import datetime

def test_firebase_api():
    """Test Firebase API endpoints"""
    base_url = "http://0.0.0.0:5000"
    
    print("🔥 Testing Firebase API Routes")
    print("=" * 50)
    
    # Test user registration
    print("\n1. Testing User Registration...")
    register_data = {
        "username": f"testuser_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "email": f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com",
        "password": "testpass123",
        "first_name": "Test",
        "last_name": "User",
        "shop_name": "Test Shop"
    }
    
    try:
        response = requests.post(f"{base_url}/api/auth/register", json=register_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 201:
            print("✅ User registration successful")
        else:
            print("❌ User registration failed")
            
    except Exception as e:
        print(f"❌ Registration error: {str(e)}")
    
    # Test user login
    print("\n2. Testing User Login...")
    login_data = {
        "email": register_data["email"],
        "password": register_data["password"]
    }
    
    try:
        response = requests.post(f"{base_url}/api/auth/login", json=login_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ User login successful")
            # Store session cookies for subsequent requests
            session_cookies = response.cookies
        else:
            print("❌ User login failed")
            return
            
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return
    
    # Test adding an item
    print("\n3. Testing Add Item...")
    item_data = {
        "name": "Test Product",
        "description": "A test product for Firebase",
        "stock_quantity": 100,
        "buying_price": 10.0,
        "retail_price": 15.0,
        "wholesale_price": 12.0,
        "category": "Electronics",
        "minimum_stock": 5
    }
    
    try:
        response = requests.post(f"{base_url}/api/inventory", json=item_data, cookies=session_cookies)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 201:
            print("✅ Item creation successful")
            item_id = response.json().get('id')
        else:
            print("❌ Item creation failed")
            item_id = None
            
    except Exception as e:
        print(f"❌ Add item error: {str(e)}")
        item_id = None
    
    # Test getting inventory
    print("\n4. Testing Get Inventory...")
    try:
        response = requests.get(f"{base_url}/api/inventory", cookies=session_cookies)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Get inventory successful")
        else:
            print("❌ Get inventory failed")
            
    except Exception as e:
        print(f"❌ Get inventory error: {str(e)}")
    
    # Test adding a customer
    print("\n5. Testing Add Customer...")
    customer_data = {
        "name": "Test Customer",
        "email": "customer@example.com",
        "phone": "1234567890",
        "address": "123 Test St",
        "customer_type": "retail"
    }
    
    try:
        response = requests.post(f"{base_url}/api/customers", json=customer_data, cookies=session_cookies)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 201:
            print("✅ Customer creation successful")
        else:
            print("❌ Customer creation failed")
            
    except Exception as e:
        print(f"❌ Add customer error: {str(e)}")
    
    # Test getting customers
    print("\n6. Testing Get Customers...")
    try:
        response = requests.get(f"{base_url}/api/customers", cookies=session_cookies)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Get customers successful")
        else:
            print("❌ Get customers failed")
            
    except Exception as e:
        print(f"❌ Get customers error: {str(e)}")
    
    # Test dashboard summary
    print("\n7. Testing Dashboard Summary...")
    try:
        response = requests.get(f"{base_url}/api/dashboard/summary", cookies=session_cookies)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Dashboard summary successful")
        else:
            print("❌ Dashboard summary failed")
            
    except Exception as e:
        print(f"❌ Dashboard summary error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🔥 Firebase API Testing Complete")

if __name__ == "__main__":
    test_firebase_api()

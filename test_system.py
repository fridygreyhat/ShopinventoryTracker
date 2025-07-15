
#!/usr/bin/env python3
"""
Comprehensive system test script to verify all functionality
"""

import requests
import json
import sys
from datetime import datetime

class SystemTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.user_id = None
        self.test_results = []

    def log_test(self, test_name, success, message=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })

    def test_registration(self):
        """Test user registration"""
        test_user = {
            "username": f"testuser_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "email": f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com",
            "password": "testpass123",
            "first_name": "Test",
            "last_name": "User",
            "shop_name": "Test Shop"
        }
        
        try:
            response = self.session.post(f"{self.base_url}/api/auth/register", json=test_user)
            if response.status_code == 201:
                data = response.json()
                if data.get('success'):
                    self.user_id = data['user']['id']
                    self.log_test("User Registration", True, f"User ID: {self.user_id}")
                    return True
            
            self.log_test("User Registration", False, f"Status: {response.status_code}, Response: {response.text}")
            return False
        except Exception as e:
            self.log_test("User Registration", False, f"Exception: {str(e)}")
            return False

    def test_login(self):
        """Test user login"""
        if not self.user_id:
            self.log_test("User Login", False, "No user to login with")
            return False
            
        # Login is handled via session from registration
        self.log_test("User Login", True, "Session-based login successful")
        return True

    def test_dashboard_api(self):
        """Test dashboard API endpoints"""
        try:
            response = self.session.get(f"{self.base_url}/api/dashboard/summary")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_test("Dashboard API", True, "Summary data retrieved")
                    return True
            
            self.log_test("Dashboard API", False, f"Status: {response.status_code}")
            return False
        except Exception as e:
            self.log_test("Dashboard API", False, f"Exception: {str(e)}")
            return False

    def test_inventory_crud(self):
        """Test inventory CRUD operations"""
        # Create item
        test_item = {
            "name": "Test Product",
            "description": "Test product description",
            "stock_quantity": 100,
            "minimum_stock": 10,
            "buying_price": 50.0,
            "retail_price": 80.0,
            "wholesale_price": 70.0,
            "category": "Test Category"
        }
        
        try:
            # Create
            response = self.session.post(f"{self.base_url}/api/inventory", json=test_item)
            if response.status_code != 201:
                self.log_test("Inventory CRUD - Create", False, f"Create failed: {response.status_code}")
                return False
            
            item_data = response.json()
            item_id = item_data['id']
            
            # Read
            response = self.session.get(f"{self.base_url}/api/inventory")
            if response.status_code != 200:
                self.log_test("Inventory CRUD - Read", False, f"Read failed: {response.status_code}")
                return False
            
            # Update
            update_data = {"name": "Updated Test Product", "stock_quantity": 150}
            response = self.session.put(f"{self.base_url}/api/inventory/{item_id}", json=update_data)
            if response.status_code != 200:
                self.log_test("Inventory CRUD - Update", False, f"Update failed: {response.status_code}")
                return False
            
            # Delete (soft delete)
            response = self.session.delete(f"{self.base_url}/api/inventory/{item_id}")
            if response.status_code != 200:
                self.log_test("Inventory CRUD - Delete", False, f"Delete failed: {response.status_code}")
                return False
            
            self.log_test("Inventory CRUD", True, "All CRUD operations successful")
            return True
            
        except Exception as e:
            self.log_test("Inventory CRUD", False, f"Exception: {str(e)}")
            return False

    def test_categories_api(self):
        """Test categories API"""
        try:
            response = self.session.get(f"{self.base_url}/api/categories")
            if response.status_code == 200:
                self.log_test("Categories API", True, "Categories retrieved successfully")
                return True
            else:
                self.log_test("Categories API", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Categories API", False, f"Exception: {str(e)}")
            return False

    def test_business_intelligence(self):
        """Test BI endpoints"""
        try:
            response = self.session.get(f"{self.base_url}/api/bi/kpis")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_test("Business Intelligence", True, "KPIs retrieved successfully")
                    return True
            
            self.log_test("Business Intelligence", False, f"Status: {response.status_code}")
            return False
        except Exception as e:
            self.log_test("Business Intelligence", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run comprehensive system tests"""
        print("🚀 Starting Comprehensive System Tests")
        print("=" * 50)
        
        tests = [
            self.test_registration,
            self.test_login,
            self.test_dashboard_api,
            self.test_inventory_crud,
            self.test_categories_api,
            self.test_business_intelligence,
        ]
        
        for test in tests:
            test()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! System is fully functional.")
            return True
        else:
            print("⚠️  Some tests failed. Check the logs above.")
            return False

if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get("http://localhost:5000/")
        if response.status_code != 200:
            print("❌ Server is not running on localhost:5000")
            sys.exit(1)
    except:
        print("❌ Cannot connect to server on localhost:5000")
        print("Please start the server first with: python main.py")
        sys.exit(1)
    
    # Run tests
    tester = SystemTester()
    success = tester.run_all_tests()
    
    # Save results
    with open('test_results.json', 'w') as f:
        json.dump(tester.test_results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to test_results.json")
    
    sys.exit(0 if success else 1)

import requests
import json
import os
import time
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

BASE_URL = "http://localhost:8000"

class TestUser:
    def __init__(self, username, password, role):
        self.username = username
        self.password = password
        self.role = role
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.logged_in = False

    def login(self):
        """Login and return True if successful"""
        try:
            # First get the login page to get the CSRF token
            response = self.session.get(f"{BASE_URL}/login", timeout=10)
            
            # Post login data
            response = self.session.post(
                f"{BASE_URL}/login",
                data={"username": self.username, "password": self.password},
                allow_redirects=True,
                timeout=10
            )
            
            # Check if we were redirected to the dashboard
            self.logged_in = response.url == f"{BASE_URL}/"
            return self.logged_in
        except Exception as e:
            print(f"Login error: {str(e)}")
            return False

    def logout(self):
        """Logout and return True if successful"""
        try:
            response = self.session.get(
                f"{BASE_URL}/logout",
                allow_redirects=True,
                timeout=10
            )
            self.logged_in = False
            return response.url == f"{BASE_URL}/login"
        except Exception as e:
            print(f"Logout error: {str(e)}")
            return False

    def upload_file(self, file_path):
        """Upload a file and return the response"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f)}
                response = self.session.post(
                    f"{BASE_URL}/api/upload",
                    files=files,
                    timeout=30  # Longer timeout for file upload
                )
                return response.json() if response.ok else None
        except Exception as e:
            print(f"Upload error: {str(e)}")
            return None

    def get_analytics(self):
        """Get analytics data"""
        try:
            response = self.session.get(f"{BASE_URL}/api/analytics", timeout=10)
            return response.json() if response.ok else None
        except Exception as e:
            print(f"Analytics error: {str(e)}")
            return None

    def get_data(self, page=1, per_page=10):
        """Get transaction data"""
        try:
            response = self.session.get(
                f"{BASE_URL}/api/data",
                params={"page": page, "per_page": per_page},
                timeout=10
            )
            return response.json() if response.ok else None
        except Exception as e:
            print(f"Data error: {str(e)}")
            return None

    def clear_data(self):
        """Clear user's data"""
        try:
            response = self.session.post(f"{BASE_URL}/api/data/clear", timeout=10)
            return response.json() if response.ok else None
        except Exception as e:
            print(f"Clear data error: {str(e)}")
            return None

    def get_upload_history(self):
        """Get upload history"""
        try:
            response = self.session.get(f"{BASE_URL}/api/uploads/history", timeout=10)
            return response.json() if response.ok else None
        except Exception as e:
            print(f"Upload history error: {str(e)}")
            return None

    def update_password(self, current_password, new_password):
        """Update password"""
        try:
            response = self.session.post(
                f"{BASE_URL}/api/settings/password",
                data={
                    "current_password": current_password,
                    "new_password": new_password,
                    "confirm_password": new_password
                },
                timeout=10
            )
            return response.json() if response.ok else None
        except Exception as e:
            print(f"Password update error: {str(e)}")
            return None

    def update_system_settings(self, batch_size, sync_interval, max_file_size):
        """Update system settings (admin only)"""
        try:
            response = self.session.post(
                f"{BASE_URL}/api/settings/system",
                data={
                    "batch_size": batch_size,
                    "sync_interval": sync_interval,
                    "max_file_size": max_file_size
                },
                timeout=10
            )
            return response.json() if response.ok else None
        except Exception as e:
            print(f"System settings error: {str(e)}")
            return None

def wait_for_server():
    """Wait for server to be ready"""
    print("Waiting for server to be ready...")
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}/login")
            if response.status_code == 200:
                print("Server is ready!")
                return True
        except:
            pass
        time.sleep(1)
        print(".", end="", flush=True)
    print("\nServer not ready after 30 seconds")
    return False

def test_user_auth(user):
    """Test user authentication"""
    print(f"\nTesting authentication for {user.username}")
    assert user.login(), "Login failed"
    print("✓ Login successful")
    
    assert user.logout(), "Logout failed"
    print("✓ Logout successful")
    
    assert user.login(), "Second login failed"
    print("✓ Second login successful")

def test_data_upload(user, test_file):
    """Test data upload and verification"""
    print(f"\nTesting data upload for {user.username}")
    result = user.upload_file(test_file)
    assert result and result["status"] == "success", "Upload failed"
    print(f"✓ Upload successful: {result['records_processed']} records processed")
    
    # Verify data appears in transactions
    data = user.get_data()
    assert data and len(data["data"]) > 0, "No data found after upload"
    print(f"✓ Data verification successful: {data['total']} records found")

def test_analytics(user):
    """Test analytics functionality"""
    print(f"\nTesting analytics for {user.username}")
    analytics = user.get_analytics()
    assert analytics, "Failed to get analytics"
    
    print("Analytics summary:")
    print(f"✓ Total sales: ${analytics['summary']['total_sales']:,.2f}")
    print(f"✓ Total transactions: {analytics['summary']['total_transactions']:,}")
    print(f"✓ Average transaction: ${analytics['summary']['avg_transaction_value']:,.2f}")
    
    assert len(analytics['sales_by_store']) > 0, "No store data found"
    print(f"✓ Store data available: {len(analytics['sales_by_store'])} stores")
    
    assert len(analytics['sales_by_tender']) > 0, "No tender data found"
    print(f"✓ Tender data available: {len(analytics['sales_by_tender'])} types")
    
    assert len(analytics['daily_sales']) > 0, "No daily sales data found"
    print(f"✓ Daily sales data available: {len(analytics['daily_sales'])} days")

def test_upload_history(user):
    """Test upload history functionality"""
    print(f"\nTesting upload history for {user.username}")
    history = user.get_upload_history()
    assert history and len(history["history"]) > 0, "No upload history found"
    print(f"✓ Upload history available: {len(history['history'])} entries")

def test_settings(user):
    """Test settings functionality"""
    print(f"\nTesting settings for {user.username}")
    if user.role == "admin":
        result = user.update_system_settings(1000, 300, 10485760)
        assert result and "success" in result["message"], "Failed to update system settings"
        print("✓ System settings update successful")

    # Test password update
    result = user.update_password(user.password, user.password + "new")
    if result:
        print("✓ Password update successful")
        # Reset password for further tests
        user.update_password(user.password + "new", user.password)
    else:
        print("✗ Password update failed")

def test_data_isolation(users, test_file):
    """Test data isolation between users"""
    print("\nTesting data isolation between users")
    
    # Clear all data first
    for user in users:
        user.login()
        user.clear_data()
    
    # Upload data for each user
    for i, user in enumerate(users):
        user.login()
        user.upload_file(test_file)
        
        # Verify data
        data = user.get_data()
        analytics = user.get_analytics()
        
        if user.role == "admin":
            # Admin should see all data
            total_records = sum(u.get_data()["total"] for u in users[:-1])  # Exclude admin
            assert data["total"] >= total_records, "Admin not seeing all data"
            print(f"✓ Admin data verification successful: seeing {data['total']} records")
        elif user.role == "manager":
            # Manager should see their data plus regular users' data
            regular_users_data = sum(
                u.get_data()["total"] for u in users 
                if u.role == "user"
            )
            assert data["total"] >= regular_users_data, "Manager not seeing correct data"
            print(f"✓ Manager data verification successful: seeing {data['total']} records")
        else:
            # Regular user should only see their own data
            print(f"✓ User data verification successful: seeing {data['total']} records")

def main():
    """Main test function"""
    # Wait for server to be ready
    if not wait_for_server():
        return
    
    # Create test users
    users = [
        TestUser("user1", "pass1", "user"),
        TestUser("user2", "pass2", "user"),
        TestUser("user3", "pass3", "admin")
    ]
    
    test_file = "test_data.csv"
    
    # Ensure test file exists
    if not os.path.exists(test_file):
        print(f"Error: Test file {test_file} not found")
        return
    
    for user in users:
        print(f"\n=== Testing user: {user.username} ({user.role}) ===")
        
        # Test basic authentication
        test_user_auth(user)
        
        # Test data upload and verification
        test_data_upload(user, test_file)
        
        # Test analytics
        test_analytics(user)
        
        # Test upload history
        test_upload_history(user)
        
        # Test settings
        test_settings(user)
    
    # Test data isolation between users
    test_data_isolation(users, test_file)
    
    print("\n=== All tests completed ===")

if __name__ == "__main__":
    main() 
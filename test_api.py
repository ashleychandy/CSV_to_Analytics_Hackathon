import requests
import json

BASE_URL = "http://localhost:8000"
SESSION = requests.Session()

def test_login():
    """Test login functionality"""
    print("\nTesting Login...")
    data = {
        "username": "user1",
        "password": "pass1"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = SESSION.post(f"{BASE_URL}/login", data=data, headers=headers, allow_redirects=False)
    print(f"Login Status: {response.status_code}")
    return response.status_code == 303  # Redirect on success

def test_upload():
    """Test file upload"""
    print("\nTesting File Upload...")
    files = {
        'file': ('test_data.csv', open('test_data.csv', 'rb'), 'text/csv')
    }
    response = SESSION.post(f"{BASE_URL}/api/upload", files=files)
    print(f"Upload Response: {response.json()}")
    return response.status_code == 200

def test_analytics():
    """Test analytics endpoint"""
    print("\nTesting Analytics...")
    response = SESSION.get(f"{BASE_URL}/api/analytics")
    print(f"Analytics Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_data():
    """Test data endpoint"""
    print("\nTesting Data Retrieval...")
    response = SESSION.get(f"{BASE_URL}/api/data")
    print(f"Data Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_settings():
    """Test settings endpoints"""
    print("\nTesting Settings Update...")
    # Test password update
    data = {
        "current_password": "pass1",
        "new_password": "newpass1",
        "confirm_password": "newpass1"
    }
    response = SESSION.post(f"{BASE_URL}/api/settings/password", data=data)
    print(f"Password Update Response: {response.json()}")
    
    # Test system settings update (admin only)
    data = {
        "batch_size": 1000,
        "sync_interval": 300,
        "max_file_size": 10485760  # 10MB
    }
    response = SESSION.post(f"{BASE_URL}/api/settings/system", data=data)
    print(f"System Settings Update Response: {response.json()}")
    return response.status_code == 200

def test_logout():
    """Test logout functionality"""
    print("\nTesting Logout...")
    response = SESSION.get(f"{BASE_URL}/logout", allow_redirects=False)
    print(f"Logout Status: {response.status_code}")
    return response.status_code == 303  # Redirect on success

def test_clear_data():
    """Test clear data functionality"""
    print("\nTesting Clear Data...")
    response = SESSION.post(f"{BASE_URL}/api/data/clear")
    print(f"Clear Data Response: {response.json()}")
    return response.status_code == 200

def test_upload_history():
    """Test upload history functionality"""
    print("\nTesting Upload History...")
    response = SESSION.get(f"{BASE_URL}/api/uploads/history")
    print(f"Upload History Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def main():
    """Run all tests"""
    try:
        # Test login
        if not test_login():
            print("Login failed!")
            return

        # Test file upload
        if not test_upload():
            print("File upload failed!")
            return

        # Test analytics
        if not test_analytics():
            print("Analytics retrieval failed!")
            return

        # Test data retrieval
        if not test_data():
            print("Data retrieval failed!")
            return

        # Test upload history
        if not test_upload_history():
            print("Upload history retrieval failed!")
            return

        # Test settings
        if not test_settings():
            print("Settings update failed!")
            return

        # Test clear data
        if not test_clear_data():
            print("Clear data failed!")
            return

        # Test logout
        if not test_logout():
            print("Logout failed!")
            return

        print("\nAll tests completed successfully!")

    except Exception as e:
        print(f"\nError during testing: {str(e)}")

if __name__ == "__main__":
    main() 
import os
from google.cloud import storage
import json
import hashlib
from datetime import datetime

class UserAuth:
    def __init__(self, storage_client, bucket_name):
        self.storage_client = storage_client
        self.bucket = storage_client.bucket(bucket_name)
        self.users_blob = self.bucket.blob('users/users.json')
        
        # Create users.json if it doesn't exist
        if not self.users_blob.exists():
            print("Creating new users.json file")
            self._save_users({})

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def _get_users(self):
        try:
            if self.users_blob.exists():
                content = self.users_blob.download_as_string()
                return json.loads(content)
            else:
                print("users.json does not exist, creating it")
                self._save_users({})
                return {}
        except Exception as e:
            print(f"Error getting users: {str(e)}")
            return {}

    def _save_users(self, users):
        try:
            self.users_blob.upload_from_string(
                json.dumps(users),
                content_type='application/json'
            )
            print(f"Saved users.json with {len(users)} users")
        except Exception as e:
            print(f"Error saving users: {str(e)}")

    def register_user(self, username, password, email):
        try:
            users = self._get_users()
            
            if username in users:
                return False, "Username already exists"
            
            users[username] = {
                'password': self._hash_password(password),
                'email': email,
                'created_at': datetime.now().isoformat()
            }
            
            self._save_users(users)
            print(f"User registered: {username}")
            return True, "User registered successfully"
        except Exception as e:
            print(f"Registration error: {str(e)}")
            return False, f"Registration error: {str(e)}"

    def login_user(self, username, password):
        try:
            print(f"Attempting login for user: {username}")
            users = self._get_users()
            
            if not users:
                print("No users found in the system")
                return False, "No users found in the system. Please register first."
            
            if username not in users:
                print(f"User not found: {username}")
                return False, "User not found"
            
            hashed_password = self._hash_password(password)
            if users[username]['password'] != hashed_password:
                print("Invalid password")
                return False, "Invalid password"
            
            print(f"Login successful for: {username}")
            return True, "Login successful"
        except Exception as e:
            print(f"Login error: {str(e)}")
            return False, f"Login error: {str(e)}"

    def get_user_info(self, username):
        try:
            users = self._get_users()
            if username in users:
                user_info = users[username].copy()
                user_info.pop('password', None)  # Remove password from returned data
                return user_info
            print(f"User info not found for: {username}")
            return None
        except Exception as e:
            print(f"Error getting user info: {str(e)}")
            return None 
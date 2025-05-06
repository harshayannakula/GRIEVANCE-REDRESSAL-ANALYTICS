import os
from flask import Flask, request, render_template, flash, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename
import json
import hashlib
from datetime import datetime, timedelta
import base64
import uuid
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Session configuration
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

# Configure storage folders
DATA_FOLDER = 'data'
USERS_FILE = os.path.join(DATA_FOLDER, 'users.json')
COMPLAINTS_FOLDER = os.path.join(DATA_FOLDER, 'complaints')
UPLOADS_FOLDER = os.path.join(DATA_FOLDER, 'uploads')

# Create necessary folders
for folder in [DATA_FOLDER, COMPLAINTS_FOLDER, UPLOADS_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Create users.json if it doesn't exist
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump({}, f)

# User Authentication functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading users: {str(e)}")
        return {}

def save_users(users):
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f)
    except Exception as e:
        print(f"Error saving users: {str(e)}")

def register_user(username, password, email):
    users = get_users()
    
    if username in users:
        return False, "Username already exists"
    
    users[username] = {
        'password': hash_password(password),
        'email': email,
        'created_at': datetime.now().isoformat()
    }
    
    save_users(users)
    return True, "User registered successfully"

def login_user(username, password):
    print(f"Attempting login for user: {username}")
    users = get_users()
    
    if not users:
        return False, "No users found. Please register first."
    
    if username not in users:
        return False, "User not found"
    
    hashed_password = hash_password(password)
    if users[username]['password'] != hashed_password:
        return False, "Invalid password"
    
    return True, "Login successful"

def get_user_info(username):
    users = get_users()
    if username in users:
        user_info = users[username].copy()
        user_info.pop('password', None)
        return user_info
    return None

# Complaint functions
def generate_unique_folder_name():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    return f"complaint_{timestamp}_{unique_id}"

def save_complaint(username, text=None, photo_data=None, location_data=None):
    folder_name = generate_unique_folder_name()
    complaint_folder = os.path.join(COMPLAINTS_FOLDER, folder_name)
    os.makedirs(complaint_folder)
    
    complaint_data = {
        'user': username,
        'timestamp': datetime.now().isoformat(),
        'status': 'pending'
    }
    
    # Save text
    if text:
        with open(os.path.join(complaint_folder, 'complaint.txt'), 'w') as f:
            f.write(text)
        complaint_data['has_text'] = True
    
    # Save photo
    if photo_data:
        try:
            photo_data = photo_data.split(',')[1]
            photo_bytes = base64.b64decode(photo_data)
            with open(os.path.join(complaint_folder, 'photo.jpg'), 'wb') as f:
                f.write(photo_bytes)
            complaint_data['has_photo'] = True
        except Exception as e:
            print(f"Error saving photo: {str(e)}")
    
    # Save location
    if location_data:
        with open(os.path.join(complaint_folder, 'location.json'), 'w') as f:
            f.write(location_data)
        complaint_data['has_location'] = True
    
    # Save metadata
    with open(os.path.join(complaint_folder, 'metadata.json'), 'w') as f:
        json.dump(complaint_data, f)
    
    return folder_name

def get_user_complaints(username):
    complaints = []
    
    for folder_name in os.listdir(COMPLAINTS_FOLDER):
        metadata_file = os.path.join(COMPLAINTS_FOLDER, folder_name, 'metadata.json')
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                if metadata.get('user') == username:
                    # Get complaint text if available
                    text_content = None
                    text_file = os.path.join(COMPLAINTS_FOLDER, folder_name, 'complaint.txt')
                    if os.path.exists(text_file):
                        with open(text_file, 'r') as f:
                            text_content = f.read()
                    
                    # Get photo path if available
                    photo_url = None
                    photo_file = os.path.join(COMPLAINTS_FOLDER, folder_name, 'photo.jpg')
                    if os.path.exists(photo_file):
                        photo_url = f"/complaints/{folder_name}/photo.jpg"
                    
                    # Get location if available
                    location = None
                    location_file = os.path.join(COMPLAINTS_FOLDER, folder_name, 'location.json')
                    if os.path.exists(location_file):
                        with open(location_file, 'r') as f:
                            location = json.load(f)
                    
                    complaints.append({
                        'id': folder_name,
                        'text': text_content,
                        'photo_url': photo_url,
                        'location': location,
                        'timestamp': metadata.get('timestamp'),
                        'status': metadata.get('status', 'pending')
                    })
            except Exception as e:
                print(f"Error processing complaint {folder_name}: {str(e)}")
    
    # Sort complaints by timestamp in descending order
    complaints.sort(key=lambda x: x['timestamp'], reverse=True)
    return complaints

# Route decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please login to access this page')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required')
            return render_template('login.html')
        
        success, message = login_user(username, password)
        if success:
            session['username'] = username
            flash(message)
            return redirect(url_for('dashboard'))
        flash(message)
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        if not username or not password or not email:
            flash('All fields are required')
            return render_template('register.html')
        
        success, message = register_user(username, password, email)
        flash(message)
        if success:
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        username = session['username']
        user_info = get_user_info(username)
        if not user_info:
            flash('User information not found. Please login again.')
            session.pop('username', None)
            return redirect(url_for('login'))
        
        complaints = get_user_complaints(username)
        return render_template('dashboard.html', user_info=user_info, complaints=complaints)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}')
        print(f"Dashboard error: {str(e)}")
        return redirect(url_for('login'))

@app.route('/submit_complaint', methods=['GET', 'POST'])
@login_required
def submit_complaint():
    if request.method == 'POST':
        try:
            text = request.form.get('text')
            photo = request.form.get('photo')
            location = request.form.get('location')
            
            if not text and not photo:
                flash('Please provide complaint details')
                return redirect(request.url)
            
            save_complaint(session['username'], text, photo, location)
            flash('Complaint submitted successfully')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'An error occurred: {str(e)}')
            return redirect(request.url)
    
    return render_template('submit_complaint.html')

# Route to serve photos
@app.route('/complaints/<folder>/<filename>')
@login_required
def serve_photo(folder, filename):
    if filename != 'photo.jpg':
        return "Not found", 404
    
    # Check if the user has access to this complaint
    metadata_file = os.path.join(COMPLAINTS_FOLDER, folder, 'metadata.json')
    if os.path.exists(metadata_file):
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            if metadata.get('user') != session['username']:
                return "Unauthorized", 403
        except:
            return "Error", 500
    
    return send_from_directory(os.path.join(COMPLAINTS_FOLDER, folder), filename)

if __name__ == '__main__':
    app.run(debug=True, port=5001) 
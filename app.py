import os
from flask import Flask, request, render_template, flash, redirect, url_for, session, jsonify
from google.cloud import storage
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from google.api_core import exceptions
import uuid
from datetime import datetime, timedelta
import base64
import json
from user_auth import UserAuth
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Generate a secure random secret key
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Session configuration
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

# Configure Google Cloud Storage
try:
    storage_client = storage.Client.from_service_account_json('optical-net-452113-n9-064952459436.json')
    bucket_name = os.getenv('BUCKET_NAME', 'mastertest_1')
    bucket = storage_client.bucket(bucket_name)
    user_auth = UserAuth(storage_client, bucket_name)
except Exception as e:
    print(f"Error initializing Google Cloud Storage: {str(e)}")
    raise

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_unique_folder_name():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    return f"complaint_{timestamp}_{unique_id}"

def get_user_complaints(username):
    complaints = []
    blobs = bucket.list_blobs(prefix='complaint_')
    
    for blob in blobs:
        if blob.name.endswith('metadata.json'):
            try:
                metadata = json.loads(blob.download_as_string())
                if metadata.get('user') == username:
                    # Get the folder name from the blob path
                    folder_name = blob.name.rsplit('/', 1)[0]
                    
                    # Get complaint text if available
                    text_content = None
                    text_blob = bucket.blob(f'{folder_name}/complaint.txt')
                    if text_blob.exists():
                        text_content = text_blob.download_as_string().decode('utf-8')
                    
                    # Get photo URL if available
                    photo_url = None
                    photo_blob = bucket.blob(f'{folder_name}/photo.jpg')
                    if photo_blob.exists():
                        photo_url = photo_blob.generate_signed_url(
                            version="v4",
                            expiration=datetime.now() + timedelta(hours=1),
                            method="GET"
                        )
                    
                    # Get location if available
                    location = None
                    location_blob = bucket.blob(f'{folder_name}/location.json')
                    if location_blob.exists():
                        location = json.loads(location_blob.download_as_string())
                    
                    # Get department information if available
                    department_info = None
                    department_blob = bucket.blob(f'{folder_name}/department.json')
                    if department_blob.exists():
                        department_info = json.loads(department_blob.download_as_string())
                    
                    # Get status history if available
                    status_history = None
                    history_blob = bucket.blob(f'{folder_name}/status_history.json')
                    if history_blob.exists():
                        status_history = json.loads(history_blob.download_as_string())
                    
                    # Get similar complaints
                    similar_complaints = []
                    if text_content:
                        # This is a simplified version - in a real system, you'd use NLP or ML to find similar complaints
                        similar_complaints = find_similar_complaints(text_content, username)
                    
                    complaints.append({
                        'id': folder_name,
                        'text': text_content,
                        'photo_url': photo_url,
                        'location': location,
                        'timestamp': metadata.get('timestamp'),
                        'status': metadata.get('status', 'pending'),
                        'department': department_info.get('name') if department_info else None,
                        'department_contact': department_info.get('contact') if department_info else None,
                        'expected_resolution': department_info.get('resolution_time') if department_info else None,
                        'status_history': status_history,
                        'similar_complaints': similar_complaints
                    })
            except Exception as e:
                print(f"Error processing complaint {blob.name}: {str(e)}")
                continue
    
    # Sort complaints by timestamp in descending order
    complaints.sort(key=lambda x: x['timestamp'], reverse=True)
    return complaints

def find_similar_complaints(text, username):
    """Find similar complaints based on text similarity"""
    # This is a placeholder function - in a real system, you'd use NLP or ML
    # to find similar complaints based on text content
    return [
        {
            'id': 'C001',
            'similarity': 85,
            'text': 'Similar complaint about infrastructure'
        },
        {
            'id': 'C002',
            'similarity': 72,
            'text': 'Related issue in same area'
        },
        {
            'id': 'C003',
            'similarity': 65,
            'text': 'Similar type of complaint'
        }
    ]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please login to access this page')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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
        
        try:
            success, message = user_auth.login_user(username, password)
            if success:
                session['username'] = username
                flash(message)
                return redirect(url_for('dashboard'))
            else:
                flash(message)
        except Exception as e:
            flash(f'Login error: {str(e)}')
            print(f"Login error: {str(e)}")
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        success, message = user_auth.register_user(username, password, email)
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
    if 'username' not in session:
        flash('Please login to access the dashboard')
        return redirect(url_for('login'))
    
    try:
        username = session['username']
        print(f"Loading dashboard for user: {username}")
        
        user_info = user_auth.get_user_info(username)
        if not user_info:
            flash('User information not found. Please login again.')
            session.pop('username', None)
            return redirect(url_for('login'))
        
        complaints = get_user_complaints(username)
        print(f"Found {len(complaints)} complaints for user: {username}")
        
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
            if 'text' not in request.form and 'photo' not in request.form:
                flash('Please provide complaint details')
                return redirect(request.url)
            
            # Generate unique folder name for this complaint
            folder_name = generate_unique_folder_name()
            
            # Create complaint metadata
            complaint_data = {
                'user': session['username'],
                'timestamp': datetime.now().isoformat(),
                'status': 'pending'
            }
            
            # Handle text upload
            if 'text' in request.form:
                text_content = request.form['text']
                if text_content:
                    try:
                        text_blob = bucket.blob(f'{folder_name}/complaint.txt')
                        text_blob.upload_from_string(text_content)
                        complaint_data['has_text'] = True
                    except exceptions.Forbidden as e:
                        flash(f'Error uploading complaint text: {str(e)}')
                        return redirect(request.url)
            
            # Handle photo upload
            if 'photo' in request.form and request.form['photo']:
                try:
                    photo_data = request.form['photo'].split(',')[1]
                    photo_bytes = base64.b64decode(photo_data)
                    photo_blob = bucket.blob(f'{folder_name}/photo.jpg')
                    photo_blob.upload_from_string(photo_bytes, content_type='image/jpeg')
                    complaint_data['has_photo'] = True
                except exceptions.Forbidden as e:
                    flash(f'Error uploading photo: {str(e)}')
                    return redirect(request.url)
            
            # Handle location upload
            if 'location' in request.form and request.form['location']:
                try:
                    location_data = json.loads(request.form['location'])
                    if 'latitude' in location_data and 'longitude' in location_data:
                        location_blob = bucket.blob(f'{folder_name}/location.json')
                        location_blob.upload_from_string(
                            json.dumps({
                                'latitude': float(location_data['latitude']),
                                'longitude': float(location_data['longitude'])
                            }),
                            content_type='application/json'
                        )
                        complaint_data['has_location'] = True
                except (json.JSONDecodeError, ValueError, exceptions.Forbidden) as e:
                    flash(f'Error uploading location data: {str(e)}')
                    return redirect(request.url)
            
            # Save complaint metadata
            metadata_blob = bucket.blob(f'{folder_name}/metadata.json')
            metadata_blob.upload_from_string(
                json.dumps(complaint_data),
                content_type='application/json'
            )
            
            # Save meta.json file for compatibility with the Cloud Function
            meta = {
                'timestamp': datetime.now().isoformat()
            }
            meta_blob = bucket.blob(f'{folder_name}/meta.json')
            meta_blob.upload_from_string(
                json.dumps(meta),
                content_type='application/json'
            )
            
            flash('Complaint submitted successfully')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'An error occurred: {str(e)}')
            return redirect(request.url)
    
    return render_template('submit_complaint.html')

@app.route('/withdraw_complaint/<complaint_id>', methods=['POST'])
@login_required
def withdraw_complaint(complaint_id):
    try:
        # Get the metadata blob
        metadata_blob = bucket.blob(f'{complaint_id}/metadata.json')
        if not metadata_blob.exists():
            return jsonify({'success': False, 'message': 'Complaint not found'}), 404

        # Download and update metadata
        metadata = json.loads(metadata_blob.download_as_string())
        
        # Check if the complaint belongs to the current user
        if metadata.get('user') != session['username']:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        # Update status to withdrawn
        metadata['status'] = 'withdrawn'
        metadata['withdrawn_at'] = datetime.now().isoformat()
        metadata['withdrawn_by'] = session['username']

        # Save updated metadata
        metadata_blob.upload_from_string(
            json.dumps(metadata),
            content_type='application/json'
        )

        # Create or update status history
        history_blob = bucket.blob(f'{complaint_id}/status_history.json')
        status_history = []
        if history_blob.exists():
            status_history = json.loads(history_blob.download_as_string())
        
        status_history.append({
            'status': 'withdrawn',
            'timestamp': datetime.now().isoformat(),
            'action': 'withdrawn',
            'by': session['username'],
            'notes': 'Complaint withdrawn by user for review'
        })

        history_blob.upload_from_string(
            json.dumps(status_history),
            content_type='application/json'
        )

        return jsonify({
            'success': True,
            'message': 'Complaint withdrawn successfully. It will be reviewed by officials.'
        })

    except Exception as e:
        print(f"Error withdrawing complaint: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error withdrawing complaint: {str(e)}'
        }), 500

@app.route('/get_all_complaints')
def get_all_complaints():
    try:
        # Get all complaints from the bucket
        complaints = []
        blobs = bucket.list_blobs(prefix='complaint_')
        
        for blob in blobs:
            if blob.name.endswith('metadata.json'):
                try:
                    # Get the folder name from the blob path
                    folder_name = blob.name.rsplit('/', 1)[0]
                    
                    # Get metadata
                    metadata = json.loads(blob.download_as_text())
                    if metadata.get('status') == 'withdrawn':
                        continue
                    
                    # Get location data
                    location_blob = bucket.blob(f'{folder_name}/location.json')
                    if location_blob.exists():
                        location_data = json.loads(location_blob.download_as_text())
                        if 'latitude' in location_data and 'longitude' in location_data:
                            complaints.append({
                                'id': folder_name,
                                'location': {
                                    'latitude': float(location_data['latitude']),
                                    'longitude': float(location_data['longitude'])
                                },
                                'status': metadata.get('status', 'pending'),
                                'timestamp': metadata.get('timestamp')
                            })
                except Exception as e:
                    print(f"Error processing complaint {blob.name}: {str(e)}")
                    continue
        
        return jsonify(complaints)
    except Exception as e:
        print(f"Error fetching complaints: {str(e)}")
        return jsonify([])

if __name__ == '__main__':
    app.run(debug=True, port=5001) 
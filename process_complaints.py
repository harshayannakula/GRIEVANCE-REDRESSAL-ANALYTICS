import os
import json
import datetime
from google.cloud import storage, bigquery
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up Google Cloud clients
storage_client = storage.Client.from_service_account_json('optical-net-452113-n9-064952459436.json')
bigquery_client = bigquery.Client.from_service_account_json('optical-net-452113-n9-064952459436.json')

# Constants
BUCKET_NAME = 'dataingestion_master'
BIGQUERY_TABLE_ID = 'optical-net-452113-n9.Grievance.extract'
PROCESSED_MARKER = 'processed_for_bigquery.txt'

def blob_exists(bucket_name, source_blob_name):
    """Check if a blob exists in the bucket."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    return blob.exists()

def download_blob(bucket_name, source_blob_name):
    """Download a blob's content as text."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    return blob.download_as_text()

def upload_blob(bucket_name, source_string, destination_blob_name):
    """Upload a string to a blob."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(source_string)

def get_public_url(bucket_name, file_name):
    """Generate a public URL for a file in the bucket."""
    return f"https://storage.googleapis.com/{bucket_name}/{file_name}"

def determine_department(issue_type):
    """Determine which department should handle the complaint."""
    issue_type = issue_type.lower() if issue_type else "unknown"
    if issue_type == "pothole":
        return "Road Maintenance Department"
    elif issue_type in ["garbage", "collapsed trees", "tree fallen"]:
        return "Municipal Corporation"
    elif issue_type in ["sewage leak", "sewage", "water leakage", "blocked drain"]:
        return "Water Supply and Sewerage Board"
    elif issue_type in ["street light", "electric pole", "power cut"]:
        return "Electricity Department"
    else:
        return "General Department"

def determine_priority(urgency_keywords):
    """Determine the priority of the complaint based on urgency keywords."""
    if not urgency_keywords:
        return "Normal"
    
    high_priority_terms = ["urgent", "emergency", "dangerous"]
    for term in high_priority_terms:
        if any(term in keyword.lower() for keyword in urgency_keywords):
            return "High"
    
    return "Medium"

def extract_label_prediction(label_data):
    """Extract the prediction information from label.json data."""
    try:
        # Parse the label data
        if isinstance(label_data, str):
            label_data = json.loads(label_data)
        
        # Handle different possible structures of the label data
        if isinstance(label_data, list) and len(label_data) > 0:
            label_data = label_data[0]
        
        # Extract predictions
        if 'predictions' in label_data and 'predictions' in label_data['predictions']:
            predictions = label_data['predictions']['predictions']
            if predictions and len(predictions) > 0:
                # Sort predictions by confidence (highest first)
                sorted_predictions = sorted(predictions, key=lambda x: x.get('confidence', 0), reverse=True)
                
                # Return the highest confidence prediction
                top_prediction = sorted_predictions[0]
                return {
                    'class': top_prediction.get('class', 'Unknown'),
                    'confidence': top_prediction.get('confidence', 0)
                }
        
        return {'class': 'No prediction', 'confidence': 0}
    except Exception as e:
        logging.warning(f"Error extracting label prediction: {str(e)}")
        return {'class': 'Error', 'confidence': 0}

def get_table_schema(table_id):
    """Get the schema of an existing BigQuery table."""
    try:
        table = bigquery_client.get_table(table_id)
        return [field.name for field in table.schema]
    except Exception as e:
        logging.error(f"Error getting table schema: {str(e)}")
        # Return a minimal set of fields that should exist
        return ["complaint_id", "user_id", "description", "status"]

def insert_into_bigquery(row, table_id):
    """Insert a row into BigQuery, filtering out fields that don't exist in the schema."""
    try:
        # Get the existing table schema
        schema_fields = get_table_schema(table_id)
        
        # Filter the row to only include fields that exist in the schema
        filtered_row = {k: v for k, v in row.items() if k in schema_fields}
        
        # Log what fields were removed
        removed_fields = set(row.keys()) - set(filtered_row.keys())
        if removed_fields:
            logging.warning(f"Removed fields not in schema: {removed_fields}")
        
        errors = bigquery_client.insert_rows_json(table_id, [filtered_row])
        if errors:
            logging.error(f"BigQuery insert errors: {errors}")
            raise RuntimeError(f"BigQuery insert errors: {errors}")
        logging.info(f"Successfully inserted data into BigQuery table {table_id}")
        return True
    except Exception as e:
        logging.error(f"Error inserting into BigQuery: {str(e)}")
        return False

def process_complaint(folder_name):
    """Process a complaint folder and insert data into BigQuery."""
    try:
        # Check if this complaint has already been processed
        marker_path = f"{folder_name}/{PROCESSED_MARKER}"
        if blob_exists(BUCKET_NAME, marker_path):
            logging.info(f"Complaint {folder_name} already processed, skipping")
            return False
        
        # Define file paths
        metadata_path = f"{folder_name}/metadata.json"
        location_path = f"{folder_name}/location.json"
        meta_path = f"{folder_name}/meta.json"
        complaint_text_path = f"{folder_name}/complaint.txt"
        extract_path = f"{folder_name}/complaint_extract.json"
        photo_path = f"{folder_name}/photo.jpg"
        label_path = f"{folder_name}/label.json"
        
        # Check if required files exist
        if not blob_exists(BUCKET_NAME, metadata_path):
            logging.warning(f"Required file not found: {metadata_path}")
            return False
        
        if not blob_exists(BUCKET_NAME, location_path):
            logging.warning(f"Required file not found: {location_path}")
            return False
        
        if not blob_exists(BUCKET_NAME, complaint_text_path):
            logging.warning(f"Required file not found: {complaint_text_path}")
            return False
        
        # Load data
        metadata = json.loads(download_blob(BUCKET_NAME, metadata_path))
        location = json.loads(download_blob(BUCKET_NAME, location_path))
        complaint_text = download_blob(BUCKET_NAME, complaint_text_path)
        
        # Get timestamp from metadata if meta.json doesn't exist
        timestamp = datetime.datetime.now().isoformat()
        if blob_exists(BUCKET_NAME, meta_path):
            meta = json.loads(download_blob(BUCKET_NAME, meta_path))
            timestamp = meta.get("timestamp", timestamp)
        else:
            # Use timestamp from metadata.json if available
            timestamp = metadata.get("timestamp", timestamp)
        
        # Load text analysis results
        extract = {}
        try:
            if blob_exists(BUCKET_NAME, extract_path):
                extract = json.loads(download_blob(BUCKET_NAME, extract_path))
                logging.info(f"Text analysis results loaded for {folder_name}")
            else:
                logging.warning(f"Text analysis file not found: {extract_path}")
        except Exception as e:
            logging.warning(f"Could not load text analysis results: {str(e)}")
        
        # Load image analysis results and extract label prediction
        label_prediction = {'class': 'No label', 'confidence': 0}
        try:
            if blob_exists(BUCKET_NAME, label_path):
                label_data = json.loads(download_blob(BUCKET_NAME, label_path))
                logging.info(f"Image analysis results loaded for {folder_name}")
                label_prediction = extract_label_prediction(label_data)
                logging.info(f"Extracted label prediction: {label_prediction}")
            else:
                logging.warning(f"Image analysis file not found: {label_path}")
        except Exception as e:
            logging.warning(f"Could not load image analysis results: {str(e)}")
        
        # Extract issue type from text analysis
        issue_types = extract.get("Issue Type", [])
        issue_type = issue_types[0] if issue_types else "Unknown"
        
        # Determine department based on issue type
        department = determine_department(issue_type)
        
        # Determine priority based on urgency keywords
        urgency_keywords = extract.get("Urgency", [])
        priority = determine_priority(urgency_keywords)
        
        # Extract location details
        extracted_locations = extract.get("Location", [])
        location_text = ", ".join(extracted_locations) if extracted_locations else "Unknown"
        
        # Extract dates mentioned
        dates_mentioned = extract.get("Date", [])
        date_text = ", ".join(dates_mentioned) if dates_mentioned else ""
        
        # Get image detection results if available
        image_detections = []
        if 'predictions' in label_data and 'predictions' in label_data['predictions']:
            predictions = label_data['predictions']['predictions']
            for prediction in predictions:
                if 'class' in prediction and 'confidence' in prediction:
                    image_detections.append({
                        'class': prediction['class'],
                        'confidence': prediction['confidence']
                    })
        
        # Build row for BigQuery - include all possible fields
        # The insert_into_bigquery function will filter out fields that don't exist in the schema
        row = {
            "complaint_id": folder_name,
            "user_id": metadata.get("user", metadata.get("username", "anonymous")),
            "description": complaint_text.strip(),
            "image_url": get_public_url(BUCKET_NAME, photo_path),
            "image": get_public_url(BUCKET_NAME, photo_path),  # For backward compatibility
            "latitude": float(location.get("latitude", 0)),
            "longitude": float(location.get("longitude", 0)),
            "location": json.dumps(location),  # For backward compatibility
            "location_text": location_text,
            "status": metadata.get("status", "pending"),
            "submitted_at": timestamp,
            "issue_type": issue_type,
            "extract": issue_type,  # For backward compatibility
            "department": department,
            "priority": priority,
            "dates_mentioned": date_text,
            "image_detections": json.dumps(image_detections),
            "text_analysis": json.dumps(extract),
            "processed_at": datetime.datetime.now().isoformat(),
            "label": label_prediction.get("class", "Unknown")  # Add the label prediction class
        }
        
        # Insert into BigQuery
        success = insert_into_bigquery(row, BIGQUERY_TABLE_ID)
        
        if success:
            # Mark this complaint as processed
            upload_blob(BUCKET_NAME, datetime.datetime.now().isoformat(), marker_path)
            logging.info(f"Successfully processed complaint {folder_name}")
            return True
        else:
            logging.error(f"Failed to insert complaint {folder_name} into BigQuery")
            return False
            
    except Exception as e:
        logging.error(f"Error processing complaint {folder_name}: {str(e)}")
        return False

def find_unprocessed_complaints():
    """Find all complaint folders that haven't been processed yet."""
    bucket = storage_client.bucket(BUCKET_NAME)
    blobs = list(bucket.list_blobs(prefix='complaint_'))
    
    # Extract unique folder names
    folders = set()
    for blob in blobs:
        if '/' in blob.name:
            folder_name = blob.name.split('/')[0]
            if folder_name.startswith('complaint_'):
                folders.add(folder_name)
    
    # Filter for unprocessed complaints
    unprocessed = []
    for folder in folders:
        marker_path = f"{folder}/{PROCESSED_MARKER}"
        if not blob_exists(BUCKET_NAME, marker_path):
            unprocessed.append(folder)
    
    return unprocessed

def main():
    """Main function to process all unprocessed complaints."""
    logging.info("Starting complaint processing script")
    
    # Find unprocessed complaints
    unprocessed = find_unprocessed_complaints()
    logging.info(f"Found {len(unprocessed)} unprocessed complaints")
    
    # Process each complaint
    processed_count = 0
    for folder in unprocessed:
        logging.info(f"Processing complaint folder: {folder}")
        if process_complaint(folder):
            processed_count += 1
    
    logging.info(f"Processing complete. Processed {processed_count} complaints.")

if __name__ == "__main__":
    main()

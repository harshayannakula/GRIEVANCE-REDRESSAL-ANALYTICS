from google.cloud import storage
import json
import os

# Initialize storage client
storage_client = storage.Client()

# Define bucket name
BUCKET_NAME = "dataingestion_master"

def read_json_from_gcs(bucket_name, file_path):
    """Read JSON file from Google Cloud Storage"""
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        if not blob.exists():
            return None
        return json.loads(blob.download_as_text())
    except Exception as e:
        print(f"Error reading {file_path}: {str(e)}")
        return None

def process_complaint(event, context):
    """Cloud Function triggered by new file upload to bucket"""
    try:
        # Get the file details from the event
        file_name = event['name']
        folder_prefix = file_name.rsplit('/', 1)[0] + '/'
        
        # Read metadata
        metadata = read_json_from_gcs(BUCKET_NAME, folder_prefix + "metadata.json")
        if not metadata:
            print(f"No metadata found for {folder_prefix}")
            return
            
        # Read location data if available
        location = read_json_from_gcs(BUCKET_NAME, folder_prefix + "location.json")
        
        # Read label data if available
        label = read_json_from_gcs(BUCKET_NAME, folder_prefix + "label.json")
        
        # Process the complaint data
        print(f"Processing complaint: {metadata.get('id', 'unknown')}")
        print(f"Location: {location}")
        print(f"Label: {label}")
        
        # Add any additional processing logic here
        
    except Exception as e:
        print(f"Error processing complaint: {str(e)}")
        raise 
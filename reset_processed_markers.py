import os
import json
from google.cloud import storage
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up Google Cloud clients
storage_client = storage.Client.from_service_account_json('optical-net-452113-n9-064952459436.json')

# Constants
BUCKET_NAME = 'dataingestion_master'
PROCESSED_MARKER = 'processed_for_bigquery.txt'

def delete_blob(bucket_name, blob_name):
    """Delete a blob from the bucket."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    try:
        blob.delete()
        return True
    except Exception as e:
        logging.error(f"Error deleting blob {blob_name}: {str(e)}")
        return False

def find_complaint_folders():
    """Find all complaint folders in the bucket."""
    bucket = storage_client.bucket(BUCKET_NAME)
    blobs = list(bucket.list_blobs(prefix='complaint_'))
    
    # Extract unique folder names
    folders = set()
    for blob in blobs:
        if '/' in blob.name:
            folder_name = blob.name.split('/')[0]
            if folder_name.startswith('complaint_'):
                folders.add(folder_name)
    
    return folders

def reset_processed_markers():
    """Reset all processed markers in complaint folders."""
    folders = find_complaint_folders()
    logging.info(f"Found {len(folders)} complaint folders")
    
    reset_count = 0
    for folder in folders:
        marker_path = f"{folder}/{PROCESSED_MARKER}"
        if delete_blob(BUCKET_NAME, marker_path):
            logging.info(f"Reset processed marker for {folder}")
            reset_count += 1
    
    logging.info(f"Reset {reset_count} processed markers")
    return reset_count

if __name__ == "__main__":
    reset_processed_markers()

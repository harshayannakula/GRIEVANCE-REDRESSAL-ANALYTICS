import base64
import datetime
import json
from google.cloud import storage, bigquery
import logging

def download_blob(bucket_name, source_blob_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    return blob.download_as_text()

def blob_exists(bucket_name, source_blob_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    return blob.exists()

def get_public_url(bucket_name, file_name):
    return f"https://storage.googleapis.com/{bucket_name}/{file_name}"

def determine_department(issue_type):
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
    if not urgency_keywords:
        return "Normal"
    
    high_priority_terms = ["urgent", "emergency", "dangerous"]
    for term in high_priority_terms:
        if any(term in keyword.lower() for keyword in urgency_keywords):
            return "High"
    
    return "Medium"

def get_table_schema(table_id):
    """Get the schema of an existing BigQuery table."""
    try:
        client = bigquery.Client()
        table = client.get_table(table_id)
        return [field.name for field in table.schema]
    except Exception as e:
        logging.error(f"Error getting table schema: {str(e)}")
        # Return a minimal set of fields that should exist
        return ["complaint_id", "user_id", "description", "status"]

def insert_into_bigquery(row, table_id):
    try:
        # Get the existing table schema
        schema_fields = get_table_schema(table_id)
        
        # Filter the row to only include fields that exist in the schema
        filtered_row = {k: v for k, v in row.items() if k in schema_fields}
        
        # Log what fields were removed
        removed_fields = set(row.keys()) - set(filtered_row.keys())
        if removed_fields:
            logging.warning(f"Removed fields not in schema: {removed_fields}")
        
        client = bigquery.Client()
        errors = client.insert_rows_json(table_id, [filtered_row])
        if errors:
            logging.error(f"BigQuery insert errors: {errors}")
            raise RuntimeError(f"BigQuery insert errors: {errors}")
        logging.info(f"Successfully inserted data into BigQuery table {table_id}")
    except Exception as e:
        logging.error(f"Error inserting into BigQuery: {str(e)}")
        raise

def process_complaint1(event, context):
    """
    Cloud Function triggered by a Pub/Sub message to process complaint data
    and insert it into BigQuery after both text and image analysis are complete.
    
    Args:
        event (dict): The dictionary with data specific to this type of event.
        context (google.cloud.functions.Context): The Cloud Functions event metadata.
    """
    try:
        # Decode the Pub/Sub message
        pubsub_message = base64.b64decode(event['data']).decode('utf-8')
        data = json.loads(pubsub_message)
        
        logging.info(f"Processing complaint data: {data}")
        
        bucket_name = data['bucket']
        folder_name = data['file'].split("/")[0]
        
        # Define file paths
        metadata_path = f"{folder_name}/metadata.json"
        location_path = f"{folder_name}/location.json"
        meta_path = f"{folder_name}/meta.json"
        complaint_text_path = f"{folder_name}/complaint.txt"
        extract_path = f"{folder_name}/complaint_extract.json"
        photo_path = f"{folder_name}/photo.jpg"
        label_path = f"{folder_name}/label.json"
        
        # Check if required files exist
        if not blob_exists(bucket_name, metadata_path):
            raise FileNotFoundError(f"Required file not found: {metadata_path}")
        
        if not blob_exists(bucket_name, location_path):
            raise FileNotFoundError(f"Required file not found: {location_path}")
        
        if not blob_exists(bucket_name, complaint_text_path):
            raise FileNotFoundError(f"Required file not found: {complaint_text_path}")
        
        # Load data
        metadata = json.loads(download_blob(bucket_name, metadata_path))
        location = json.loads(download_blob(bucket_name, location_path))
        complaint_text = download_blob(bucket_name, complaint_text_path)
        
        # Get timestamp from metadata if meta.json doesn't exist
        timestamp = datetime.datetime.now().isoformat()
        if blob_exists(bucket_name, meta_path):
            meta = json.loads(download_blob(bucket_name, meta_path))
            timestamp = meta.get("timestamp", timestamp)
        else:
            # Use timestamp from metadata.json if available
            timestamp = metadata.get("timestamp", timestamp)
        
        # Load text analysis results
        extract = {}
        try:
            if blob_exists(bucket_name, extract_path):
                extract = json.loads(download_blob(bucket_name, extract_path))
                logging.info(f"Text analysis results: {extract}")
            else:
                logging.warning(f"Text analysis file not found: {extract_path}")
        except Exception as e:
            logging.warning(f"Could not load text analysis results: {str(e)}")
        
        # Load image analysis results
        image_labels = {}
        try:
            if blob_exists(bucket_name, label_path):
                image_labels = json.loads(download_blob(bucket_name, label_path))
                logging.info(f"Image analysis results: {image_labels}")
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
        if image_labels and 'predictions' in image_labels:
            for prediction in image_labels['predictions']:
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
            "image_url": get_public_url(bucket_name, photo_path),
            "image": get_public_url(bucket_name, photo_path),  # For backward compatibility
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
            "processed_at": datetime.datetime.now().isoformat()
        }
        
        # Insert into BigQuery
        table_id = "optical-net-452113-n9.Grievance.extract"
        insert_into_bigquery(row, table_id)
        
        logging.info(f"Successfully processed complaint {folder_name}")
        
        return {
            "success": True,
            "complaint_id": folder_name,
            "message": f"Complaint processed and inserted into BigQuery"
        }
        
    except Exception as e:
        error_message = f"Error processing complaint: {str(e)}"
        logging.error(error_message)
        return {
            "success": False,
            "error": error_message
        }

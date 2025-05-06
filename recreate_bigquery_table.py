import os
import json
from google.cloud import bigquery
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up BigQuery client
bigquery_client = bigquery.Client.from_service_account_json('optical-net-452113-n9-064952459436.json')

# Constants
PROJECT_ID = 'optical-net-452113-n9'
DATASET_ID = 'Grievance'
TABLE_ID = 'extract'
FULL_TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

def delete_table():
    """Delete the existing BigQuery table."""
    try:
        bigquery_client.delete_table(FULL_TABLE_ID, not_found_ok=True)
        logging.info(f"Table {FULL_TABLE_ID} deleted successfully")
        return True
    except Exception as e:
        logging.error(f"Error deleting table: {str(e)}")
        return False

def create_table_with_schema():
    """Create a new BigQuery table with the updated schema."""
    try:
        # Define the schema
        schema = [
            bigquery.SchemaField("complaint_id", "STRING", mode="REQUIRED", description="Unique identifier for the complaint"),
            bigquery.SchemaField("user_id", "STRING", mode="NULLABLE", description="User who submitted the complaint"),
            bigquery.SchemaField("description", "STRING", mode="NULLABLE", description="Text description of the complaint"),
            bigquery.SchemaField("image", "STRING", mode="NULLABLE", description="URL to the complaint image"),
            bigquery.SchemaField("location", "STRING", mode="NULLABLE", description="Location data as JSON string"),
            bigquery.SchemaField("status", "STRING", mode="NULLABLE", description="Current status of the complaint"),
            bigquery.SchemaField("submitted_at", "TIMESTAMP", mode="NULLABLE", description="Timestamp when the complaint was submitted"),
            bigquery.SchemaField("extract", "STRING", mode="NULLABLE", description="Issue type extracted from text analysis"),
            bigquery.SchemaField("department", "STRING", mode="NULLABLE", description="Department assigned to handle the complaint"),
            bigquery.SchemaField("label", "STRING", mode="NULLABLE", description="Prediction label from image analysis")
        ]
        
        # Create table reference
        dataset_ref = bigquery_client.dataset(DATASET_ID)
        table_ref = dataset_ref.table(TABLE_ID)
        
        # Create table with schema
        table = bigquery.Table(table_ref, schema=schema)
        table = bigquery_client.create_table(table)
        
        logging.info(f"Table {FULL_TABLE_ID} created successfully with updated schema")
        return True
    except Exception as e:
        logging.error(f"Error creating table: {str(e)}")
        return False

def main():
    """Main function to recreate the BigQuery table with updated schema."""
    logging.info("Starting BigQuery table recreation")
    
    # Delete existing table
    if delete_table():
        # Create new table with updated schema
        if create_table_with_schema():
            logging.info("BigQuery table recreation completed successfully")
        else:
            logging.error("Failed to create new table with updated schema")
    else:
        logging.error("Failed to delete existing table")

if __name__ == "__main__":
    main()

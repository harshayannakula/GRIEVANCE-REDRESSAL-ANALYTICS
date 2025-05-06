import os
import json
from google.cloud import storage
from inference_sdk import InferenceHTTPClient

# Roboflow Inference Client
client = InferenceHTTPClient(
    api_url="https://detect.roboflow.com",
    api_key="IV2dgqzZX6EJ5p0ewlWJ"  # Replace with your actual API key
)

def label_image1(event, context):
    bucket_name = event['bucket']
    file_name = event['name']

    # Check if the file is an image and ends with 'photo.jpg'
    if not file_name.endswith("photo.jpg"):
        print(f"Ignored file: {file_name}")
        return

    image_url = f"https://storage.googleapis.com/{bucket_name}/{file_name}"
    print(f"Processing image: {image_url}")

    try:
        # Run inference using Roboflow's custom model
        result = client.run_workflow(
            workspace_name="aditya-gadey",  # Replace with your workspace name
            workflow_id="custom-workflow",  # Replace with your workflow ID
            images={"image": image_url},
            use_cache=True
        )

        print("Roboflow Result:", result)

        # Ensure that the result is formatted properly into JSON
        result_json = json.dumps(result)

        # The result will be saved as label.json in the same folder as the image
        output_blob_name = f"{file_name.rsplit('/', 1)[0]}/label.json"

        # Initialize Google Cloud Storage client
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(output_blob_name)

        # Upload the result as JSON
        blob.upload_from_string(result_json, content_type='application/json')

        print(f"Saved labeled result to: {output_blob_name}")

    except Exception as e:
        print(f"Error processing image {image_url}: {e}")

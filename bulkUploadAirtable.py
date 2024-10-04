import requests
import os
import json
import logging
from dotenv import load_dotenv
from time import sleep, time
import boto3
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Load environment variables from .env file
load_dotenv()

# Configuration
BASE_ID = os.getenv("BASE_ID")
TABLE_ID = os.getenv("TABLE_ID")
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

gdrive_credentials_path = os.getenv("GDRIVE_CREDENTIALS_PATH")
use_storage = os.getenv("USE_STORAGE", "s3").lower()  # Options: 's3' or 'gdrive'

# Verify that all variables are loaded
if not all([BASE_ID, TABLE_ID, AIRTABLE_TOKEN]):
    raise ValueError("One or more environment variables are missing.")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("upload_logs.log"),
                        logging.StreamHandler()
                    ])

def get_table_schema():
    """
    Get the table schema to understand the fields that need to be populated.
    """
    url = f"https://api.airtable.com/v0/meta/bases/{BASE_ID}/tables"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    retries = 3
    for attempt in range(retries):
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            tables = response.json().get("tables", [])
            for table in tables:
                if table["id"] == TABLE_ID or table["name"] == TABLE_ID:
                    return table
            return None
        else:
            logging.error(f"Error fetching table schema (attempt {attempt + 1}): {response.json()}")
            if attempt < retries - 1:
                sleep(2 ** attempt)  # Exponential backoff
            else:
                raise Exception(f"Failed to fetch table schema after {retries} attempts.")

def upload_to_s3(file_path):
    """
    Upload file to AWS S3 and return the file URL.
    """
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    try:
        s3.upload_file(file_path, S3_BUCKET_NAME, os.path.basename(file_path))
        url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{os.path.basename(file_path)}"
        logging.info(f"S3 Public URL: {url}")
        logging.info(f"Uploaded {file_path} to S3 successfully.")
        return url
    except Exception as e:
        logging.error(f"Error uploading {file_path} to S3: {str(e)}")
        return None

def delete_from_s3(file_path):
    """
    Delete file from AWS S3.
    """
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    try:
        s3.delete_object(Bucket=S3_BUCKET_NAME, Key=os.path.basename(file_path))
        logging.info(f"Deleted {file_path} from S3 successfully.")
    except Exception as e:
        logging.error(f"Error deleting {file_path} from S3: {str(e)}")

def upload_to_gdrive(file_path):
    """
    Upload file to Google Drive and return the file URL.
    """
    creds = service_account.Credentials.from_service_account_file(gdrive_credentials_path, scopes=["https://www.googleapis.com/auth/drive.file"])
    drive_service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': os.path.basename(file_path)}
    media = MediaFileUpload(file_path, resumable=True)
    try:
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = file.get('id')
        url = f"https://drive.google.com/uc?id={file_id}"
        logging.info(f"Uploaded {file_path} to Google Drive successfully.")
        return url
    except Exception as e:
        logging.error(f"Error uploading {file_path} to Google Drive: {str(e)}")
        return None

def upload_files(folder_path, default_fields, attachment_field_names):
    """
    Upload multiple files as new records with the default fields filled in.
    """
    files_to_upload = []
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            if filename == ".DS_Store":
                continue
            file_path = os.path.join(root, filename)
            files_to_upload.append(file_path)

    attachment_urls = []
    for file_path in files_to_upload:
        if use_storage == 's3':
            attachment_url = upload_to_s3(file_path)
        elif use_storage == 'gdrive':
            attachment_url = upload_to_gdrive(file_path)
        else:
            logging.error(f"Invalid storage option specified: {use_storage}")
            continue

        if attachment_url:
            logging.info(f"Attachment URL for {os.path.basename(file_path)}: {attachment_url}")
            attachment_urls.append((file_path, attachment_url))
        else:
            logging.error(f"Failed to upload {file_path} to {use_storage}.")

    if not attachment_urls:
        logging.error("No files were successfully uploaded.")
        return

    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }

    for file_path, attachment_url in attachment_urls:
        filename = os.path.basename(file_path)
        data = {
            "fields": default_fields.copy()
        }
        # Add attachment to the specified attachment fields
        attachment = [{"url": attachment_url, "filename": filename}]
        for field_name in attachment_field_names:
            data["fields"][field_name] = attachment

        retries = 3
        for attempt in range(retries):
            response = requests.post(url, headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                logging.info(f"Uploaded {filename} successfully to Airtable.")
                break
            else:
                logging.error(f"Error uploading {filename} to Airtable (attempt {attempt + 1}): {response.json()}")
                if attempt < retries - 1:
                    sleep(2 ** attempt)  # Exponential backoff
                else:
                    logging.error(f"Failed to upload {filename} to Airtable after {retries} attempts.")

    # Wait and validate that the images are uploaded
    validation_time = len(attachment_urls) * 5  # Total validation time is 5 seconds per file
    logging.info(f"Waiting for up to {validation_time} seconds to validate attachments in Airtable.")
    start_time = time()
    while time() - start_time < validation_time:
        all_uploaded = True
        for file_path, attachment_url in attachment_urls:
            record_id = get_record_id_by_attachment(attachment_url, attachment_field_names)
            if not record_id or not validate_attachment_uploaded(record_id, attachment_field_names):
                all_uploaded = False
                break
        if all_uploaded:
            break
        sleep(5)  # Check every 5 seconds

    # Delete the files from S3 regardless of whether the upload succeeded or failed
    if use_storage == 's3':
        for file_path, _ in attachment_urls:
            delete_from_s3(file_path)

    if not all_uploaded:
        logging.error("Some images were not uploaded successfully to Airtable after validation time.")

def get_record_id_by_attachment(attachment_url, attachment_field_names):
    """
    Get the record ID by searching for the attachment URL in Airtable.
    """
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        records = response.json().get("records", [])
        for record in records:
            for field_name in attachment_field_names:
                attachments = record.get("fields", {}).get(field_name, [])
                if attachments:
                    return record.get("id")
    return None

def validate_attachment_uploaded(record_id, attachment_field_names):
    """
    Validate if the attachment is uploaded correctly in Airtable.
    """
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}/{record_id}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        record = response.json()
        for field_name in attachment_field_names:
            attachments = record.get("fields", {}).get(field_name, [])
            if attachments:
                return True
    return False

def main():
    """
    Main function to upload files from a folder to Airtable.
    """

    # User Input
    folder_path = "" #/path/to/your/folder
    attachment_fields_input = [""]  # Specify where your attachment fields are located in your Airtable table

    # Validate folder path
    if not os.path.isdir(folder_path):
        logging.error("Invalid folder path.")
        return
    
    # Validate attachment fields
    attachment_fields_string = ",".join(attachment_fields_input)  # Convert the list to a comma-separated string
    attachment_field_names = [field.strip() for field in attachment_fields_string.split(',') if field.strip()]

    # Get schema to identify default fields
    try:
        table_schema = get_table_schema()
    except Exception as e:
        logging.error(str(e))
        return

    if not table_schema:
        logging.error("Table schema not found.")
        return

    fields = table_schema.get("fields", [])
    field_names = [field["name"] for field in fields if field["type"] not in ['multipleAttachments', 'unknownFieldType']]
    default_fields = {field_name: None for field_name in field_names}

    # Allow user to specify default values for the fields, except restricted fields
    print("Specify default values for fields (leave blank to skip):")
    for field in fields:
        field_name = field["name"]
        if field["type"] not in ['multipleAttachments', 'unknownFieldType']:
            value = input(f"Enter default value for '{field_name}': ")
            if value:
                default_fields[field_name] = value

    if not attachment_field_names:
        logging.error("No valid attachment fields specified.")
        return

    # Upload all files at once
    upload_files(folder_path, default_fields, attachment_field_names)

if __name__ == "__main__":
    main()
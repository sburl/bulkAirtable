import requests
import os
import json
import logging
from dotenv import load_dotenv
from time import sleep
import boto3
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Load environment variables from .env file
load_dotenv()

# Configuration
BASE_ID = os.getenv("BASE_ID")
TABLE_ID = os.getenv("TABLE_ID_OR_NAME")
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
    try:
        s3.upload_file(file_path, s3_bucket_name, os.path.basename(file_path))
        url = f"https://{s3_bucket_name}.s3.amazonaws.com/{os.path.basename(file_path)}"
        logging.info(f"Uploaded {file_path} to S3 successfully.")
        return url
    except Exception as e:
        logging.error(f"Error uploading {file_path} to S3: {str(e)}")
        return None

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

def upload_file_record(file_path, default_fields, attachment_field_names):
    """
    Upload a file as a new record with the default fields filled in.
    """
    filename = os.path.basename(file_path)
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }

    # Upload the file to S3 or Google Drive to get a publicly accessible URL
    if use_storage == 's3':
        attachment_url = upload_to_s3(file_path)
    elif use_storage == 'gdrive':
        attachment_url = upload_to_gdrive(file_path)
    else:
        logging.error(f"Invalid storage option specified: {use_storage}")
        return

    if not attachment_url:
        logging.error(f"Failed to upload {filename} to {use_storage}.")
        return

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
            logging.info(f"Uploaded {filename} successfully.")
            break
        else:
            logging.error(f"Error uploading {filename} (attempt {attempt + 1}): {response.json()}")
            if attempt < retries - 1:
                sleep(2 ** attempt)  # Exponential backoff
            else:
                logging.error(f"Failed to upload {filename} after {retries} attempts.")

def main():
    """
    Main function to upload files from a folder to Airtable.
    """

    # Specify folder path
    folder_path = "/Users/sqb/Desktop/test" #/path/to/your/folder
    if not os.path.isdir(folder_path):
        logging.error("Invalid folder path.")
        return

    # Specify attachment fields
    attachment_fields_input = [""]  # Specify where your attachment fields are located in your Airtable table
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
    field_names = [field["name"] for field in fields]
    default_fields = {field_name: None for field_name in field_names}

    # Allow user to modify default fields if desired
    print("Specify default values for fields (leave blank to skip):")
    for key in default_fields.keys():
        value = input(f"Enter default value for '{key}': ")
        if value:
            default_fields[key] = value
        else:
            default_fields[key] = None

    if not attachment_field_names:
        logging.error("No valid attachment fields specified.")
        return

    # Upload each file in the folder, including subdirectories
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                upload_file_record(file_path, default_fields, attachment_field_names)
            except Exception as e:
                logging.error(f"Unexpected error uploading {filename}: {str(e)}")

if __name__ == "__main__":
    main()
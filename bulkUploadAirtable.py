import requests
import os
import json
import logging
from dotenv import load_dotenv
from time import sleep

# Load environment variables from .env file
load_dotenv()

# Configuration
base_id = os.getenv("BASE_ID")
table_id_or_name = os.getenv("TABLE_ID_OR_NAME")
airtable_token = os.getenv("AIRTABLE_TOKEN")
view_name = os.getenv("VIEW_NAME", "Grid view")

# Verify that all variables are loaded
if not all([base_id, table_id_or_name, airtable_token]):
    raise ValueError("One or more environment variables are missing.")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_table_schema():
    """
    Get the table schema to understand the fields that need to be populated.
    """
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {"Authorization": f"Bearer {airtable_token}"}
    retries = 3
    for attempt in range(retries):
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            tables = response.json().get("tables", [])
            for table in tables:
                if table["id"] == table_id_or_name or table["name"] == table_id_or_name:
                    return table
            return None
        else:
            logging.error(f"Error fetching table schema (attempt {attempt + 1}): {response.json()}")
            if attempt < retries - 1:
                sleep(2 ** attempt)  # Exponential backoff
            else:
                raise Exception(f"Failed to fetch table schema after {retries} attempts.")

def upload_file_record(file_path, default_fields, attachment_field_names):
    """
    Upload a file as a new record with the default fields filled in.
    """
    filename = os.path.basename(file_path)
    url = f"https://api.airtable.com/v0/{base_id}/{table_id_or_name}"
    headers = {
        "Authorization": f"Bearer {airtable_token}",
        "Content-Type": "application/json"
    }

    # Airtable requires a publicly accessible URL for attachments
    # Here, we simulate this by uploading the file to Airtable's attachment upload endpoint
    # Note: As of 2023-10, Airtable allows direct file uploads via the API

    # Upload the file to Airtable's temporary attachment endpoint
    attachment_upload_url = 'https://api.airtable.com/v0/{baseId}/attachments'
    with open(file_path, 'rb') as file_content:
        files = {'file': (filename, file_content)}
        upload_headers = {
            "Authorization": f"Bearer {airtable_token}"
        }
        upload_response = requests.post(
            attachment_upload_url.replace('{baseId}', base_id),
            headers=upload_headers,
            files=files
        )

    if upload_response.status_code != 200:
        logging.error(f"Error uploading attachment {filename}: {upload_response.json()}")
        return

    attachment_data = upload_response.json()
    attachment_url = attachment_data.get('url')
    if not attachment_url:
        logging.error(f"No URL returned for attachment {filename}")
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

    # Ask the user to specify the attachment fields
    print("\nAvailable fields:", ', '.join(field_names))
    attachment_fields_input = input("Enter the names of the attachment fields (comma-separated): ")
    attachment_field_names = [field.strip() for field in attachment_fields_input.split(',') if field.strip() in field_names]

    if not attachment_field_names:
        logging.error("No valid attachment fields specified.")
        return

    # Get folder path from user
    folder_path = input("Enter the path of the folder containing files to upload: ")
    if not os.path.isdir(folder_path):
        logging.error("Invalid folder path.")
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
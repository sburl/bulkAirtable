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
table_id = os.getenv("TABLE_ID")
api_key = os.getenv("API_KEY")
view_name = os.getenv("VIEW_NAME", "Grid view")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_table_schema():
    """
    Get the table schema to understand the fields that need to be populated.
    """
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {"Authorization": f"Bearer {api_key}"}
    retries = 3
    for attempt in range(retries):
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            tables = response.json().get("tables", [])
            for table in tables:
                if table["id"] == table_id or table["name"] == table_id:
                    return table["fields"]
            return []
        else:
            logging.error(f"Error fetching table schema (attempt {attempt + 1}): {response.json()}")
            if attempt < retries - 1:
                sleep(2 ** attempt)  # Exponential backoff
            else:
                raise Exception(f"Failed to fetch table schema after {retries} attempts.")

def upload_file_record(file_path, default_fields):
    """
    Upload a file as a new record with the default fields filled in.
    """
    filename = os.path.basename(file_path)
    url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "fields": default_fields
    }
    # Add attachment to the data
    data["fields"]["Attachment"] = [{"url": f"file://{os.path.abspath(file_path)}"}]
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
        fields = get_table_schema()
    except Exception as e:
        logging.error(str(e))
        return
    
    default_fields = {field["name"]: None for field in fields}
    
    # Allow user to modify default fields if desired
    for key in default_fields.keys():
        value = input(f"Enter default value for '{key}' (leave blank for None): ")
        if value:
            default_fields[key] = value
    
    # Get folder path from user
    folder_path = input("Enter the path of the folder containing files to upload: ")
    if not os.path.isdir(folder_path):
        logging.error("Invalid folder path.")
        return

    # Upload each file in the folder, including subdirectories
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.pdf', '.docx', '.xlsx', '.txt')):
                file_path = os.path.join(root, filename)
                try:
                    upload_file_record(file_path, default_fields)
                except Exception as e:
                    logging.error(f"Unexpected error uploading {filename}: {str(e)}")

if __name__ == "__main__":
    main()
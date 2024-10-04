# combined Airtable-Bulk-Attachments-Download.py and Airtable-Bulk-multiple-Attachments-Download_with_folders.py

import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
base_id = os.getenv("BASE_ID")
table_id = os.getenv("TABLE_ID")
api_key = os.getenv("API_KEY")

# Options
desired_file_types = []  # e.g., ["application/pdf", "application/vnd.ms-powerpoint"], or empty list for all types
desired_file_extensions = []  # e.g., ["pdf", "ppt"], or empty list for all extensions
desired_view_names = []  # e.g., ["MyViewName1", "MyViewName2"], or empty list for all records

# Feature toggles
organize_by_directory = True  # Set to True to enable organizing files into folders based on type

# Airtable API setup
headers = {"Authorization": f"Bearer {api_key}"}

# Fetch records from Airtable
airtable_records = []
for view_name in desired_view_names if desired_view_names else [None]:
    params = {"view": view_name} if view_name else {}
    run = True
    while run:
        response = requests.get(f"https://api.airtable.com/v0/{base_id}/{table_id}", params=params, headers=headers)
        airtable_response = response.json()

        # Handle potential errors in the response
        if 'error' in airtable_response:
            break

        airtable_records += airtable_response.get('records', [])
        offset = airtable_response.get('offset')
        if offset:
            params['offset'] = offset
        else:
            run = False

# Process records
for record in airtable_records:
    fields = record.get('fields', {})
    attachments = fields.get('Attachments', [])

    for attachment in attachments:
        attachment_url = attachment.get('url')
        attachment_filename = attachment.get('filename')
        attachment_type = attachment.get('type')
        filename_extension = attachment_filename.split('.')[-1].lower()

        # Check if the attachment matches the desired types and extensions
        type_match = not desired_file_types or attachment_type in desired_file_types
        extension_match = not desired_file_extensions or filename_extension in desired_file_extensions

        if type_match and extension_match:
            # Determine the download path
            if organize_by_directory:
                # Create directories based on file type if the feature is enabled
                folder_name = filename_extension.upper()
                os.makedirs(folder_name, exist_ok=True)
                download_path = os.path.join(folder_name, attachment_filename)
            else:
                download_path = attachment_filename

            # Download the file
            file_response = requests.get(attachment_url)
            with open(download_path, 'wb') as f:
                f.write(file_response.content)
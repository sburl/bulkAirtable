import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
base_id = os.getenv("BASE_ID")
table_id = os.getenv("TABLE_ID")
api_key = os.getenv("API_KEY")

# Airtable API setup
headers = {"Authorization": f"Bearer {api_key}"}

def fetch_records_from_airtable(view_names):
    """
    Fetch records from Airtable based on the specified view names.
    """
    airtable_records = []
    for view_name in view_names if view_names else [None]:
        params = {"view": view_name} if view_name else {}
        run = True
        while run:
            response = requests.get(f"https://api.airtable.com/v0/{base_id}/{table_id}", params=params, headers=headers)
            airtable_response = response.json()

            # Handle potential errors in the response
            if 'error' in airtable_response:
                print(f"Error fetching records: {airtable_response['error']['message']}")
                break

            airtable_records += airtable_response.get('records', [])
            offset = airtable_response.get('offset')
            if offset:
                params['offset'] = offset
            else:
                run = False

    return airtable_records

def process_records(airtable_records, desired_file_types, desired_file_extensions, organize_by_directory):
    """
    Process records and download attachments based on specified file types and extensions.
    """
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
                download_attachment(attachment_url, download_path)

def download_attachment(attachment_url, download_path):
    """
    Download the attachment from the specified URL to the given path.
    """
    response = requests.get(attachment_url)
    if response.status_code == 200:
        with open(download_path, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded {download_path}")
    else:
        print(f"Failed to download {download_path}: {response.status_code}")

def main():
    """
    Main function to orchestrate the download of attachments from Airtable.
    """
    # Options
    desired_file_types = []  # e.g., ["application/pdf", "application/vnd.ms-powerpoint"], or empty list for all types
    desired_file_extensions = []  # e.g., ["pdf", "ppt"], or empty list for all extensions
    desired_view_names = []  # e.g., ["MyViewName1", "MyViewName2"], or empty list for all records
    organize_by_directory = True  # Set to True to enable organizing files into folders based on type

    # Fetch records
    airtable_records = fetch_records_from_airtable(desired_view_names)

    # Process records and download attachments
    process_records(airtable_records, desired_file_types, desired_file_extensions, organize_by_directory)

if __name__ == "__main__":
    main()
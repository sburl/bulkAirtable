import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
base_id = os.getenv("BASE_ID")
table_id = os.getenv("TABLE_ID")
airtable_token = os.getenv("AIRTABLE_TOKEN")

# Verify that all variables are loaded
if not all([base_id, table_id, airtable_token]):
    raise ValueError("One or more environment variables are missing.")

# Airtable API setup
headers = {"Authorization": f"Bearer {airtable_token}"}

def fetch_records_from_airtable(view_names):
    """
    Fetch records from Airtable based on the specified view names.
    """
    airtable_records = []
    for view_name in view_names if view_names else [None]:
        params = {"view": view_name} if view_name else {}
        run = True
        while run:
            response = requests.get(
                f"https://api.airtable.com/v0/{base_id}/{table_id}",
                params=params,
                headers=headers
            )
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

def process_records(airtable_records, desired_file_types, desired_file_extensions, attachment_field_names, organize_by_directory, output_directory):
    """
    Process records and download attachments based on specified file types and extensions.
    """
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    for record in airtable_records:
        fields = record.get('fields', {})
        # Collect attachments from specified fields
        attachments = []
        for field_name in attachment_field_names:
            attachments.extend(fields.get(field_name, []))

        for attachment in attachments:
            attachment_url = attachment.get('url')
            attachment_filename = attachment.get('filename')
            attachment_type = attachment.get('type')
            filename_extension = attachment_filename.split('.')[-1].lower()

            # Check if the attachment matches the desired types and extensions
            type_match = not desired_file_types or attachment_type in desired_file_types
            extension_match = not desired_file_extensions or filename_extension in [ext.lower() for ext in desired_file_extensions]

            if type_match and extension_match:
                # Determine the download path
                if organize_by_directory:
                    # Create directories based on file extension
                    folder_name = filename_extension.upper()
                    target_directory = os.path.join(output_directory, folder_name)
                    os.makedirs(target_directory, exist_ok=True)
                    download_path = os.path.join(target_directory, attachment_filename)
                else:
                    download_path = os.path.join(output_directory, attachment_filename)

                # Download the file
                download_attachment(attachment_url, download_path)
            else:
                print(f"Skipping {attachment_filename} due to file type {attachment_type} or extension {filename_extension}")

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
    desired_file_types = []  # e.g., ["application/pdf"], or empty list for all types
    desired_file_extensions = []  # e.g., ["pdf"], or empty list for all extensions
    desired_view_names = ["test"]  # e.g., ["MyViewName"], or empty list for all records
    organize_by_directory = True  # Set to True to organize files into folders based on file extension
    output_directory = os.path.expanduser("~/Desktop/Airtable Downloads")  # Specify the output directory

    # Prompt user to specify attachment fields
    attachment_fields_input = [""]  # Specify where your attachment fields are located in your Airtable table
    attachment_fields_string = ",".join(attachment_fields_input)  # Convert the list to a comma-separated string
    attachment_field_names = [field.strip() for field in attachment_fields_string.split(',') if field.strip()]

    if not attachment_field_names:
        print("No attachment fields specified. Please specify attachment fields.")
        return

    # Fetch records
    airtable_records = fetch_records_from_airtable(desired_view_names)

    # Process records and download attachments
    process_records(airtable_records, desired_file_types, desired_file_extensions, attachment_field_names, organize_by_directory, output_directory)

if __name__ == "__main__":
    main()
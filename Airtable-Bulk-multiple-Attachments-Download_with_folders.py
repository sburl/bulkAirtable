import requests
import json
import os

# Load environment variables from .env file -- MAKE YOUR OWN .env FILE TO USE THIS SCRIPT
load_dotenv()

base_id = os.getenv("BASE_ID")
table_id = os.getenv("TABLE_ID")
api_key = os.getenv("API_KEY")

# Options
desired_file_types = []  # e.g., ["application/pdf", "application/vnd.ms-powerpoint"], or empty list for all types
desired_file_extensions = []  # e.g., ["pdf", "pptx"], or empty list for all extensions
desired_view_name = None  # e.g., "MyViewName", or None

url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
headers = {"Authorization": f"Bearer {api_key}"}

# Initialize parameters
params = {}
if desired_view_name:
    params['view'] = desired_view_name

airtable_records = []
run = True

while run:
    response = requests.get(url, params=params, headers=headers)
    airtable_response = response.json()

    # Handle potential errors in the response
    if 'error' in airtable_response:
        print(f"Error: {airtable_response['error']['message']}")
        break

    airtable_records += airtable_response.get('records', [])

    # Ensure base directories exist
    os.makedirs('PPT', exist_ok=True)
    os.makedirs('PDF', exist_ok=True)

    for record in airtable_response.get('records', []):
        fields = record.get('fields', {})

        # Process 'PPT' attachments
        if attachments := fields.get("PPT"):
            filename_base = fields.get("Company Name", "untitled").replace(" ", "")
            print(f"Processing PPT attachments for {filename_base}")
            for attachment in attachments:
                attachment_url = attachment['url']
                attachment_filename = attachment['filename']
                attachment_type = attachment.get('type')
                filename_extension = attachment_filename.split('.')[-1].lower()

                # Check if the attachment matches the desired types and extensions
                type_match = not desired_file_types or attachment_type in desired_file_types
                extension_match = not desired_file_extensions or filename_extension in [ext.lower() for ext in desired_file_extensions]

                if type_match and extension_match:
                    print(f"Downloading {attachment_filename} from {attachment_url}")
                    response = requests.get(attachment_url)
                    path = os.path.join('PPT', filename_base)
                    os.makedirs(path, exist_ok=True)
                    with open(os.path.join(path, attachment_filename), "wb") as f:
                        f.write(response.content)
                else:
                    print(f"Skipping {attachment_filename} due to file type {attachment_type} or extension {filename_extension}")

        # Process 'PDF' attachments
        if attachments := fields.get("PDF"):
            filename_base = fields.get("Company Name", "untitled").replace(" ", "")
            print(f"Processing PDF attachments for {filename_base}")
            for attachment in attachments:
                attachment_url = attachment['url']
                attachment_filename = attachment['filename']
                attachment_type = attachment.get('type')
                filename_extension = attachment_filename.split('.')[-1].lower()

                # Check if the attachment matches the desired types and extensions
                type_match = not desired_file_types or attachment_type in desired_file_types
                extension_match = not desired_file_extensions or filename_extension in [ext.lower() for ext in desired_file_extensions]

                if type_match and extension_match:
                    print(f"Downloading {attachment_filename} from {attachment_url}")
                    response = requests.get(attachment_url)
                    path = os.path.join('PDF', filename_base)
                    os.makedirs(path, exist_ok=True)
                    with open(os.path.join(path, attachment_filename), "wb") as f:
                        f.write(response.content)
                else:
                    print(f"Skipping {attachment_filename} due to file type {attachment_type} or extension {filename_extension}")

    # Handle pagination
    if 'offset' in airtable_response:
        params['offset'] = airtable_response['offset']
    else:
        run = False
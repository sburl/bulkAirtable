import requests
import os

# Load environment variables from .env file -- MAKE YOUR OWN .env FILE TO USE THIS SCRIPT
load_dotenv()

base_id = os.getenv("BASE_ID")
table_id = os.getenv("TABLE_ID")
api_key = os.getenv("API_KEY")

# Options
desired_file_types = []  # e.g., ["image/jpeg", "application/pdf"], or empty list for all types
desired_file_extensions = []  # e.g., ["jpg", "pdf"], or empty list for all extensions
desired_view_name = None  # e.g., "MyViewName", or None for all records

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

    for record in airtable_response.get('records', []):
        fields = record.get('fields', {})
        attachments = fields.get('ss', [])
        for attachment in attachments:
            attachment_type = attachment.get('type')
            attachment_url = attachment.get('url')
            attachment_filename = attachment.get('filename')
            filename_extension = attachment_filename.split('.')[-1].lower()

            # Check if the attachment matches the desired types and extensions
            type_match = not desired_file_types or attachment_type in desired_file_types
            extension_match = not desired_file_extensions or filename_extension in [ext.lower() for ext in desired_file_extensions]

            if type_match and extension_match:
                filename_base = fields.get('Notes', 'untitled').replace(' ', '')
                filename = f"{filename_base}.{filename_extension}"
                print(f"Downloading {filename} from {attachment_url}")
                file_response = requests.get(attachment_url)
                with open(filename, 'wb') as f:
                    f.write(file_response.content)
            else:
                print(f"Skipping {attachment_filename} due to file type {attachment_type} or extension {filename_extension}")

    # Handle pagination
    if 'offset' in airtable_response:
        params['offset'] = airtable_response['offset']
    else:
        run = False
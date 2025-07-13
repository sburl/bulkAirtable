import requests
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Configuration
BASE_ID = os.getenv("BASE_ID")
TABLE_ID = os.getenv("TABLE_ID")
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")

# Verify that all variables are loaded
if not all([BASE_ID, TABLE_ID, AIRTABLE_TOKEN]):
    raise ValueError("One or more environment variables are missing.")

# Airtable API setup
headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}

def fetch_records_from_airtable(view_names):
    """
    Fetch records from Airtable based on the specified view names.
    Improved error handling: print raw response if not JSON, avoid TypeError.
    """
    airtable_records = []
    for view_name in view_names if view_names else [None]:
        params = {"view": view_name} if view_name else {}
        run = True
        while run:
            url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
            print(f"Calling URL: {url}")
            print(f"With params: {params}")
            response = requests.get(
                url,
                params=params,
                headers=headers
            )
            print(f"Response status code: {response.status_code}")
            try:
                airtable_response = response.json()
            except Exception as e:
                print("Error: Response is not valid JSON.")
                print("Raw response:", response.text)
                break

            # Handle potential errors in the response
            if isinstance(airtable_response, dict) and 'error' in airtable_response:
                error_val = airtable_response['error']
                if isinstance(error_val, dict):
                    print(f"Error fetching records: {error_val.get('message', error_val)}")
                else:
                    print(f"Error fetching records: {error_val}")
                break
            elif not isinstance(airtable_response, dict):
                print("Unexpected response type:", type(airtable_response))
                print("Raw response:", airtable_response)
                break

            airtable_records += airtable_response.get('records', [])
            offset = airtable_response.get('offset') if isinstance(airtable_response, dict) else None
            if offset:
                params['offset'] = offset
            else:
                run = False

    return airtable_records

def rename_file(old_path, new_filename):
    """
    Rename a file, handling potential filename conflicts.
    """
    directory = os.path.dirname(old_path)
    new_path = os.path.join(directory, new_filename)
    
    # Handle filename conflicts
    counter = 1
    while os.path.exists(new_path):
        name, ext = os.path.splitext(new_filename)
        new_path = os.path.join(directory, f"{name} ({counter}){ext}")
        counter += 1
    
    os.rename(old_path, new_path)
    return new_path

def process_records(airtable_records, desired_file_types, desired_file_extensions, attachment_field_names, organize_by_directory, output_directory, first, second):
    """
    Process records and download attachments based on specified file types and extensions.
    Rename files based on column information.
    """
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    for record in airtable_records:
        fields = record.get('fields', {})
        # Collect attachments from specified fields
        attachments = []
        for field_name in attachment_field_names:
            attachments.extend(fields.get(field_name, []))

        # Get file name information
        first_value = fields.get(first, '')
        second_value = fields.get(second, '')

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
                    folder_name = filename_extension.upper()
                    target_directory = os.path.join(output_directory, folder_name)
                    os.makedirs(target_directory, exist_ok=True)
                    download_path = os.path.join(target_directory, attachment_filename)
                else:
                    download_path = os.path.join(output_directory, attachment_filename)

                # Download the file
                download_attachment(attachment_url, download_path)

                # Rename the file only if fields are provided
                if first and second:
                    if first_value and second_value:
                        new_filename = f"{first_value} || {second_value}.{filename_extension}"
                    elif first_value:
                        new_filename = f"{first_value}.{filename_extension}"
                    else:
                        new_filename = attachment_filename
                    
                    if new_filename != attachment_filename:
                        new_path = rename_file(download_path, new_filename)
                        print(f"Renamed to: {os.path.basename(new_path)}")
                    else:
                        print(f"File name unchanged: {attachment_filename}")
                else:
                    print(f"File name unchanged: {attachment_filename}")
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

def ensure_valid_directory(path):
    """
    Ensure the given path is a valid directory.
    If it doesn't exist, create it.
    If it's not writable, try to find an alternative.
    """
    try:
        if not os.path.exists(path):
            os.makedirs(path)
        elif not os.path.isdir(path):
            raise NotADirectoryError(f"{path} is not a directory")
        
        # Check if the directory is writable
        test_file = os.path.join(path, 'test_write.tmp')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        
        return path
    except PermissionError:
        print(f"Warning: No write permission for {path}. Trying alternative location.")
        alt_path = os.path.join(os.path.expanduser('~'), 'Downloads', 'Airtable Downloads')
        return ensure_valid_directory(alt_path)
    except Exception as e:
        print(f"Error creating directory {path}: {str(e)}")
        return None

def main():
    """
    Main function to orchestrate the download of attachments from Airtable.
    """
    # Options
    desired_file_types = []  # e.g., ["application/pdf"], or empty list for all types
    desired_file_extensions = []  # e.g., ["pdf"], or empty list for all extensions
    desired_view_names = []  # e.g., ["MyViewName"], or empty list for all records
    organize_by_directory = True  # Set to True to organize files into folders based on file extension
    
    # Get current date in yy.mm.dd format
    current_date = datetime.now().strftime("%y.%m.%d")
    
    # Append current date to the download folder name
    base_output_directory = os.path.expanduser(f"~/Desktop/{current_date} Airtable Downloads")
    
    # Ensure the output directory is valid
    output_directory = ensure_valid_directory(base_output_directory)
    
    if not output_directory:
        print("ERROR - Could not create a valid output directory. Exiting.")
        return

    # Specify attachment fields
    attachment_field_names = ["File"]  # Specify where your attachment fields are located in your Airtable table

    # Specify fields for renaming files
    first_field = "Title"  # Enter the name of the Airtable column for the first part of the name (e.g., title)
    second_field = "Author"  # Enter the name of the Airtable column for the second part of the name (e.g., author)

    if not attachment_field_names:
        print("No attachment fields specified. Please specify attachment fields.")
        return

    # Fetch records
    airtable_records = fetch_records_from_airtable(desired_view_names)

    # Process records and download attachments
    process_records(airtable_records, desired_file_types, desired_file_extensions, attachment_field_names, organize_by_directory, output_directory, first_field, second_field)

if __name__ == "__main__":
    main()

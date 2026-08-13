"""
Module for downloading attachments from Airtable.
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Support both ``python -m bulkAirtable.bulkDownloadAirtable`` and executing
# this file directly from a source checkout.
if __package__:
    from .client import AirtableClient
else:
    from client import AirtableClient

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


class AirtableDownloader:
    """
    Class to handle downloading attachments from Airtable records.
    """
    
    def __init__(self, client: AirtableClient = None):
        """
        Initialize with an AirtableClient.
        """
        self.client = client or AirtableClient()
        
    def download_attachments(
        self,
        output_directory: str,
        attachment_field_names: list[str],
        view_names: list[str] = None,
        desired_file_types: list[str] = None,
        desired_file_extensions: list[str] = None,
        organize_by_directory: bool = True,
        rename_fields: tuple[str, str] = (None, None)
    ):
        """
        Download attachments from records.
        """
        print(f"Fetching records from base: {self.client.base_id}...")
        
        records = []
        if view_names:
            for view in view_names:
                print(f"Fetching from view: {view}")
                records.extend(self.client.fetch_records(view_name=view))
        else:
            records = self.client.fetch_records()
            
        print(f"Found {len(records)} records. Processing...")
        
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
            
        first_field, second_field = rename_fields
        
        for record in records:
            fields = record.get('fields', {})
            attachments = []
            for field_name in attachment_field_names:
                attachments.extend(fields.get(field_name, []) or [])
                
            first_value = fields.get(first_field, '') if first_field else ''
            second_value = fields.get(second_field, '') if second_field else ''
            
            for attachment in attachments:
                self._process_attachment(
                    attachment,
                    output_directory,
                    desired_file_types,
                    desired_file_extensions,
                    organize_by_directory,
                    first_value,
                    second_value
                )

    def _process_attachment(
        self,
        attachment,
        output_directory,
        desired_file_types,
        desired_file_extensions,
        organize_by_directory,
        first_value,
        second_value
    ):
        attachment_url = attachment.get('url')
        attachment_filename = attachment.get('filename')
        attachment_type = attachment.get('type')
        
        if not attachment_filename:
            return

        filename_extension = attachment_filename.split('.')[-1].lower()

        # Check filters
        type_match = not desired_file_types or attachment_type in desired_file_types
        extension_match = not desired_file_extensions or filename_extension in [ext.lower() for ext in desired_file_extensions]

        if type_match and extension_match:
            # Determine path
            if organize_by_directory:
                folder_name = filename_extension.upper()
                target_directory = os.path.join(output_directory, folder_name)
                os.makedirs(target_directory, exist_ok=True)
                download_path = os.path.join(target_directory, attachment_filename)
            else:
                download_path = os.path.join(output_directory, attachment_filename)

            # Download
            self._download_file(attachment_url, download_path)

            # Rename
            new_filename = attachment_filename
            if first_value or second_value:
                if first_value and second_value:
                    new_filename = f"{first_value} || {second_value}.{filename_extension}"
                elif first_value:
                    new_filename = f"{first_value}.{filename_extension}"
                
                if new_filename != attachment_filename:
                    new_path = rename_file(download_path, new_filename)
                    print(f"Renamed to: {os.path.basename(new_path)}")
        else:
            # print(f"Skipping {attachment_filename}...")
            pass

    def _download_file(self, url, path):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open(path, 'wb') as f:
                    f.write(response.content)
                print(f"Downloaded {os.path.basename(path)}")
            else:
                print(f"Failed to download {path}: {response.status_code}")
        except Exception as e:
            print(f"Error downloading {path}: {e}")


def main():
    load_dotenv()
    
    # Simple CLI interface
    if not all([os.getenv("BASE_ID"), os.getenv("TABLE_ID"), os.getenv("AIRTABLE_TOKEN")]):
        print("Error: environment variables BASE_ID, TABLE_ID, and AIRTABLE_TOKEN must be set.")
        return

    client = AirtableClient()
    downloader = AirtableDownloader(client)
    
    base_name = client.fetch_base_name()
    current_date = datetime.now().strftime("%y.%m.%d")
    base_output_directory = os.path.expanduser(f"~/Desktop/{current_date} Airtable {base_name} Downloads")
    output_directory = ensure_valid_directory(base_output_directory)
    
    if not output_directory:
        return

    # These could be args
    attachment_field_names = ["File"] 
    fields_to_rename = ("Title", "Author") 
    
    downloader.download_attachments(
        output_directory=output_directory,
        attachment_field_names=attachment_field_names,
        rename_fields=fields_to_rename
    )

if __name__ == "__main__":
    main()

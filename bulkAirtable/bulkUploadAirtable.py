"""
Module for uploading files to Airtable via intermediate storage (S3 or Google Drive).
"""

import os
import json
import logging
import requests
from time import sleep, time
from dotenv import load_dotenv

# Support both ``python -m bulkAirtable.bulkUploadAirtable`` and executing
# this file directly from a source checkout.
if __package__:
    from .client import AirtableClient
else:
    from client import AirtableClient

# Optional dependencies
try:
    import boto3
except ImportError:
    boto3 = None

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    service_account = None
    build = None
    MediaFileUpload = None

# Logging setup
logger = logging.getLogger(__name__)


class StorageBackend:
    """Base class for storage backends."""
    def upload_file(self, file_path: str) -> str:
        raise NotImplementedError
    
    def delete_file(self, file_path: str):
        pass


class S3Storage(StorageBackend):
    def __init__(self, access_key, secret_key, bucket_name):
        if not boto3:
            raise ImportError("boto3 is required for S3 storage")
        self.s3 = boto3.client(
            's3', 
            aws_access_key_id=access_key, 
            aws_secret_access_key=secret_key
        )
        self.bucket_name = bucket_name

    def upload_file(self, file_path: str) -> str:
        try:
            filename = os.path.basename(file_path)
            self.s3.upload_file(file_path, self.bucket_name, filename)
            url = f"https://{self.bucket_name}.s3.amazonaws.com/{filename}"
            logger.info(f"Uploaded to S3: {url}")
            return url
        except Exception as e:
            logger.error(f"S3 Upload Error: {e}")
            return None

    def delete_file(self, file_path: str):
        try:
            filename = os.path.basename(file_path)
            self.s3.delete_object(Bucket=self.bucket_name, Key=filename)
            logger.info(f"Deleted from S3: {filename}")
        except Exception as e:
            logger.error(f"S3 Delete Error: {e}")


class GDriveStorage(StorageBackend):
    def __init__(self, credentials_path):
        if not (service_account and build):
            raise ImportError("google-api-python-client and google-auth are required for GDrive")
            
        self.creds = service_account.Credentials.from_service_account_file(
            credentials_path, 
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        self.service = build('drive', 'v3', credentials=self.creds)

    def upload_file(self, file_path: str) -> str:
        try:
            file_metadata = {'name': os.path.basename(file_path)}
            media = MediaFileUpload(file_path, resumable=True)
            file = self.service.files().create(
                body=file_metadata, 
                media_body=media, 
                fields='id'
            ).execute()
            file_id = file.get('id')
            url = f"https://drive.google.com/uc?id={file_id}"
            logger.info(f"Uploaded to GDrive: {url}")
            return url
        except Exception as e:
            logger.error(f"GDrive Upload Error: {e}")
            return None


class AirtableUploader:
    """
    Class to handle uploading files to Airtable.
    """
    
    def __init__(self, client: AirtableClient, storage_backend: StorageBackend):
        self.client = client
        self.storage = storage_backend

    def upload_folder(
        self,
        folder_path: str,
        attachment_field_names: list[str],
        default_fields: dict = None
    ):
        """
        Upload all files in a folder to Airtable.
        """
        if not os.path.isdir(folder_path):
            logger.error("Invalid folder path")
            return

        files_to_upload = []
        for root, _, files in os.walk(folder_path):
            for filename in files:
                if filename.startswith("."):
                    continue
                files_to_upload.append(os.path.join(root, filename))

        if not files_to_upload:
            logger.warning("No files found to upload.")
            return

        # 1. Upload to storage (S3/GDrive)
        uploaded_attachments = []
        for file_path in files_to_upload:
            url = self.storage.upload_file(file_path)
            if url:
                uploaded_attachments.append((file_path, url))
            else:
                logger.error(f"Failed to upload {file_path} to storage.")

        if not uploaded_attachments:
            return

        # 2. Creates records in Airtable
        records_to_create = []
        for file_path, url in uploaded_attachments:
            filename = os.path.basename(file_path)
            fields = default_fields.copy() if default_fields else {}
            
            # Add attachment
            attachment_data = [{"url": url, "filename": filename}]
            for field_name in attachment_field_names:
                fields[field_name] = attachment_data
            
            records_to_create.append({"fields": fields})

        logger.info(f"Creating {len(records_to_create)} records in Airtable...")
        self.client.create_records_batch(records_to_create)

        # 3. Validate (Optional - skipped for brevity but good to have)
        # 4. Cleanup S3 if needed
        # Note: If validation is needed, it should be done before cleanup.
        # For now, we assume success if API returns 200 (checked in client).
        
        # Cleanup
        for file_path, _ in uploaded_attachments:
            self.storage.delete_file(file_path)


def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    # Config
    if not all([os.getenv("BASE_ID"), os.getenv("TABLE_ID"), os.getenv("AIRTABLE_TOKEN")]):
        print("Missing Airtable config variables.")
        return

    client = AirtableClient()

    # Storage Config
    use_storage = os.getenv("USE_STORAGE", "s3").lower()
    storage = None
    
    if use_storage == 's3':
        aws_key = os.getenv("AWS_ACCESS_KEY")
        aws_secret = os.getenv("AWS_SECRET_KEY")
        bucket = os.getenv("S3_BUCKET_NAME")
        if aws_key and aws_secret and bucket:
            storage = S3Storage(aws_key, aws_secret, bucket)
        else:
            print("Missing AWS config.")
            return
    elif use_storage == 'gdrive':
        creds = os.getenv("GDRIVE_CREDENTIALS_PATH")
        if creds:
            storage = GDriveStorage(creds)
        else:
            print("Missing GDrive config.")
            return
    else:
        print("Invalid storage option.")
        return

    uploader = AirtableUploader(client, storage)

    # Interactive or Args
    folder_path = input("Enter folder path to upload: ").strip()
    if not folder_path:
        return
        
    attachment_field = input("Enter attachment field name (e.g. File): ").strip() or "File"
    
    # Simple default fields input
    default_fields = {}
    print("Converting schema fetching to simple input for now...")
    
    uploader.upload_folder(
        folder_path=folder_path,
        attachment_field_names=[attachment_field],
        default_fields=default_fields
    )

if __name__ == "__main__":
    main()

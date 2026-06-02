"""
Module for uploading files to Airtable via intermediate storage (S3 or Google Drive).
"""

import os
import json
import uuid
import logging
import requests
from time import sleep, time
from dotenv import load_dotenv

from .client import AirtableClient

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
        # List of (file_path, s3_key) pairs. Using a list (rather than a dict
        # keyed by file_path) means that if the same file_path is uploaded more
        # than once (e.g. a retry loop) all resulting S3 objects are tracked and
        # can be cleaned up — a dict would silently overwrite the first entry
        # and orphan the first object.
        self._uploads: list[tuple[str, str]] = []

    def upload_file(self, file_path: str) -> str:
        try:
            filename = os.path.basename(file_path)
            # Unique object key: two files with the same basename in different
            # folders must not collide on (and overwrite) the same S3 key.
            key = f"{uuid.uuid4().hex}-{filename}"
            self.s3.upload_file(file_path, self.bucket_name, key)
            # Use (file_path, key) as the tracking key so that retrying the
            # same file_path in the same session doesn't silently overwrite the
            # first upload's key and orphan its S3 object.
            self._uploads.append((file_path, key))
            # Presigned GET URL (12h) instead of a public URL: lets Airtable
            # fetch the attachment after the batch create without making the
            # object publicly readable (no public-bucket requirement / footgun).
            # 1h was too short for large batches or slow Airtable ingestion
            # pipelines; 12h is the conventional safe minimum.
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=43200,
            )
            logger.info(f"Uploaded to S3 (presigned, 12h): {key}")
            return url
        except Exception as e:
            logger.error(f"S3 Upload Error: {e}")
            return None

    def delete_file(self, file_path: str):
        # Find all S3 keys associated with this file_path (there may be more
        # than one if the path was uploaded multiple times in the same session).
        matching = [(fp, k) for fp, k in self._uploads if fp == file_path]
        if not matching:
            logger.warning(f"No S3 key tracked for {file_path}; skipping delete.")
            return
        for fp, key in matching:
            try:
                self.s3.delete_object(Bucket=self.bucket_name, Key=key)
                self._uploads.remove((fp, key))
                logger.info(f"Deleted from S3: {key}")
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
        # Drive deletes by file id (not path), so remember the id from upload.
        self._file_ids = {}

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
            self._file_ids[file_path] = file_id
            url = f"https://drive.google.com/uc?id={file_id}"
            logger.info(f"Uploaded to GDrive: {url}")
            return url
        except Exception as e:
            logger.error(f"GDrive Upload Error: {e}")
            return None

    def delete_file(self, file_path: str):
        file_id = self._file_ids.get(file_path)
        if not file_id:
            logger.warning(f"No Drive file id tracked for {file_path}; skipping delete.")
            return
        try:
            self.service.files().delete(fileId=file_id).execute()
            self._file_ids.pop(file_path, None)
            logger.info(f"Deleted from GDrive: {file_id}")
        except Exception as e:
            logger.error(f"GDrive Delete Error: {e}")


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
        created_records = self.client.create_records_batch(records_to_create)

        # Clean up intermediate storage only when EVERY record was confirmed
        # created. records_to_create is built 1:1 and in order from
        # uploaded_attachments, and create_records_batch returns results in that
        # same order, so on full success we can map record[i] -> file[i]
        # positionally.
        #
        # We do NOT inspect attachment fields on the create response to decide
        # whether to delete: Airtable frequently returns attachment fields as
        # empty or omitted until it has asynchronously fetched the remote file,
        # so that check would be falsy for every record even on full success,
        # causing all intermediate files to be kept as false "orphans".
        #
        # The record count is the reliable gate: if Airtable accepted all
        # records it returns exactly len(uploaded_attachments) entries. Any
        # partial failure (failed batch, 200 with fewer records, or a whole
        # batch dropped) reduces the count and triggers the 'keep all' path.
        if len(created_records) == len(uploaded_attachments):
            for file_path, _ in uploaded_attachments:
                self.storage.delete_file(file_path)
        else:
            logger.warning(
                f"Only {len(created_records)} of {len(uploaded_attachments)} records "
                f"were created; keeping all intermediate files (cannot map records "
                f"to files safely)."
            )


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
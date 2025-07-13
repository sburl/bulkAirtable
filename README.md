# Airtable S3 and Google Drive Integration

This repository provides Python scripts for uploading and downloading files to/from Airtable using AWS S3 or Google Drive as intermediate storage. The scripts are designed to help manage attachments in Airtable by utilizing cloud storage for better handling and control.

## Overview

The project contains the following main scripts:

1. **bulkUploadAirtable.py**: Uploads multiple files from a local folder to Airtable, using AWS S3 or Google Drive as a storage service to host attachments.
2. **bulkDownloadAirtable.py**: Downloads attachments from Airtable records to a local folder, supporting AWS S3 and Google Drive integration for file storage.

The scripts support both AWS S3 and Google Drive, allowing you to select your preferred storage option. I have confirmed AWS works but there may be additional steps to get Google Drive working. They also include validation steps to ensure that files are properly uploaded to Airtable.

## Requirements

- Python 3.6+
- AWS Access Keys (for uploading to S3)
- Google Drive Service Account Credentials (for Google Drive integration)
- [Airtable Personal Access Token](https://airtable.com/create/tokens/new) (for interacting with Airtable)

Grant the following permissions to for the Airtable Personal Access Token: 
Data.records:read - To read records and download attachments
Data.records:write - To upload new records with attachments (if using the upload script)
Schema.bases:read - To read base and table structure
Scope to the Bases needed to maintain security

### Python Dependencies
The following libraries are required and can be installed using `pip`:

- `requests`
- `boto3`
- `google-api-python-client`
- `google-auth`
- `python-dotenv`

To install the dependencies, run:

```sh
pip install -r requirements.txt
```

## Configuration

### Environment Variables
The project relies on environment variables for configuration. These can be defined in a `.env` file in the root directory:

```
BASE_ID=your_airtable_base_id (from URL: app...)
TABLE_ID=your_airtable_table_id (from URL: tbl...)
AIRTABLE_TOKEN=your_airtable_api_token

AWS_ACCESS_KEY=your_aws_access_key
AWS_SECRET_KEY=your_aws_secret_key
S3_BUCKET_NAME=your_s3_bucket_name

GDRIVE_CREDENTIALS_PATH=path_to_your_google_drive_credentials_json
USE_STORAGE=s3  # Options: 's3' or 'gdrive'
```

### AWS S3 Bucket Policy

Create a new S3 bucket and set the bucket policy to allow public read access to the files. Consider creating an IAM user with the necessary permissions to manage the bucket and to limit access to your AWS account.

To do this, you must set the appropriate bucket policy and ensure the "Block Public Access" settings are configured properly:

1. **Bucket Policy**: Add a policy to your S3 bucket to allow public read access to the files:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "PublicReadGetObject",
         "Effect": "Allow",
         "Principal": "*",
         "Action": "s3:GetObject",
         "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
       }
     ]
   }
   ```

   Replace `YOUR_BUCKET_NAME` with the name of your S3 bucket.

2. **Block Public Access Settings**: Go to the "Permissions" tab in the S3 console, and disable the "Block all public access" option or adjust the settings to allow public access to objects.

### Google Drive Setup
To use Google Drive for storage, set up a service account in Google Cloud Console and download the credentials JSON file. Set the path to this file in the `.env` file (`GDRIVE_CREDENTIALS_PATH`).

## Usage

### Upload Files to Airtable
The `bulkUploadAirtable.py` script allows you to upload multiple files from a local folder to Airtable:

```sh
python bulkUploadAirtable.py
```

- **Folder Path**: Specify the folder containing files you wish to upload.
- **Attachment Fields**: Provide the Airtable attachment field names where the files should be uploaded.
- **Validation**: The script includes a validation process that checks if the files were successfully uploaded to Airtable, with a waiting period of up to 5 seconds per file.

### Download Attachments from Airtable
The `bulkDownloadAirtable.py` script allows you to download attachments from Airtable to a local folder:

```sh
python bulkDownloadAirtable.py
```

- **Destination Folder**: Specify the folder where the downloaded attachments should be saved.

## Notes

- The scripts automatically handle the deletion of uploaded files from S3 after they are confirmed to be uploaded to Airtable.
- Ensure that the S3 bucket is properly configured to allow public read access, as the attachment URLs are used for uploading to Airtable.
- The validation process in the upload script has been optimized to check if an attachment field has any value, instead of strictly matching filenames.

## License
This project is licensed under the MIT License.


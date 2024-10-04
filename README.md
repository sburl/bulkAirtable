# Airtable Bulk Attachments Download & Upload Tool

This repository provides Python scripts that allow you to bulk download and upload attachments to and from an Airtable base. It is designed to make it easy to collect files from records across multiple views, organize them locally, and upload new records to Airtable from a folder of files. The tool also supports uploading files to either Google Drive or AWS S3 before adding them as attachments to Airtable, ensuring compatibility with Airtable's requirement for publicly accessible URLs.

## Features

- **Bulk Download Attachments from Airtable**: Fetches all records from specified views in an Airtable base and downloads associated attachments.
- **Bulk Upload Attachments to Airtable**: Allows users to upload files from a local folder to Airtable as new records, with options to fill in default field values.
- **Integration with AWS S3 and Google Drive**: Supports uploading files to either Google Drive or AWS S3, then adding them as attachments to new records in Airtable.
- **Multiple File Types**: Allows you to specify desired file types (e.g., PDFs, images) and file extensions for downloads.
- **Organized Storage**: Optionally organizes downloaded files into folders based on their type or extension.
- **Handles Multiple Views**: Supports downloading attachments from multiple views in a single run.
- **Modular Design**: Each operation (fetch, download, upload) is encapsulated in its own function, making the script easy to extend and maintain.

## Prerequisites

- Python 3.7 or above
- Airtable API key
- Required Python libraries: `requests`, `python-dotenv`, `boto3`, `google-api-python-client`, `google-auth`
- AWS IAM user credentials (for S3 uploads)
- Google Drive Service Account credentials (for Google Drive uploads)

To install the required libraries, run:

```sh
pip install -r requirements.txt
```

## Setup

### Creating and Permissioning an Airtable API Key

1. **Log into Airtable**
   - Go to [https://airtable.com/](https://airtable.com/) and log in to your account.
2. **Navigate to Builder Hub**
   - Click on your profile picture in the top-right corner and select **Builder Hub**.
3. **Create a Personal Access Token**
   - Click on **Create token** to create a new personal access token.
   - Name your token appropriately (e.g., "Airtable Bulk Access Token").
4. **Set Permissions**
   - Add the following permissions to the token:
     - **data.records:read**: See the data in records.
     - **data.records:write**: Create, edit, and delete records.
     - **schema.bases:read**: See the structure of a base, like table names or field types.
5. **Specify Base Access**
   - You must specify which bases the token has access to. Select the bases you want to use with this script.
6. **Copy the Token**
   - Once the token is created, copy it for later use.

### Creating and Permissioning an IAM User for AWS S3

1. **Log in to AWS Console**.
2. **Create an IAM user** and attach the following permissions:
   - **AmazonS3FullAccess** (or create a custom policy that allows the specific actions needed).
3. **Generate Access Key and Secret Key** for the IAM user.
4. Add the following to your `.env` file:
   ```env
   AWS_ACCESS_KEY=<Your_AWS_Access_Key>
   AWS_SECRET_KEY=<Your_AWS_Secret_Key>
   S3_BUCKET_NAME=<Your_S3_Bucket_Name>
   ```

### Creating a Google Drive Service Account

1. **Go to the Google Cloud Console** and create a project.
2. **Enable the Google Drive API** for the project.
3. **Create a service account** and download the JSON credentials file.
4. Add the path to the credentials file to your `.env` file:
   ```env
   GDRIVE_CREDENTIALS_PATH=<Path_To_Google_Credentials_JSON>
   ```

### Environment Variables

Create a `.env` file in the project directory with the following variables:

```env
BASE_ID=<Your_Airtable_Base_ID>
TABLE_ID_OR_NAME=<Your_Table_ID_or_Name>
AIRTABLE_TOKEN=<Your_Airtable_API_Token>
AWS_ACCESS_KEY=<Your_AWS_Access_Key>
AWS_SECRET_KEY=<Your_AWS_Secret_Key>
S3_BUCKET_NAME=<Your_S3_Bucket_Name>
GDRIVE_CREDENTIALS_PATH=<Path_To_Google_Credentials_JSON>
USE_STORAGE=s3  # Options: 's3' or 'gdrive'
```
Replace the placeholders with your Airtable and cloud storage credentials.

## Configuration

- **Desired File Types**: Update the `desired_file_types` list in the script to specify which types of files you want to download (e.g., `application/pdf`, `image/jpeg`). Leave it empty to download all file types.
- **Desired File Extensions**: Update the `desired_file_extensions` list to specify file extensions you want to download (e.g., `pdf`, `jpg`). Leave it empty to download all extensions.
- **Desired View Names**: Update the `desired_view_names` list with the views you want to download attachments from (e.g., `View1`, `View2`). Leave it empty to download records from all views.
- **Attachment Fields**: Update the `attachment_field_names` variable to specify which attachment fields to use for both upload and download operations.
- **Organize by Directory**: Set the `organize_by_directory` variable to `True` if you want to organize downloaded files into folders based on their file extension.

## Usage

### Download Attachments from Airtable

To run the download script:

```sh
python bulkDownloadAirtable.py
```

The script will output log messages indicating the progress of fetching records and downloading attachments. Files will be saved in the current directory or in subfolders if the `organize_by_directory` option is enabled.

### Upload Files as Records to Airtable

To run the upload script:

```sh
python bulkUploadAirtable.py
```

- Files will be uploaded first to either Google Drive or AWS S3 based on your configuration (`USE_STORAGE` variable in `.env` file).
- The files will then be added to Airtable as new records with the specified attachment fields.

## Example

Suppose you have an Airtable base with multiple views and want to download all PDF and JPEG attachments from specific views, and you want them organized by file type. You would:

1. Set `desired_file_types = ["application/pdf", "image/jpeg"]`
2. Set `desired_file_extensions = ["pdf", "jpg"]`
3. Set `desired_view_names = ["Marketing", "Sales"]`
4. Set `organize_by_directory = True`

Running the script will create folders (`PDF`, `JPG`) and download the matching files into these folders.

To upload new files as records, simply run the upload script and follow the prompts.

## Error Handling

- **Download Script**: If there are any issues with the Airtable API (e.g., incorrect credentials), the script will stop and print the error response.
- **Upload Script**: The upload script will retry failed uploads up to three times with exponential backoff. Errors are logged for troubleshooting purposes.
- If there are issues with network connectivity, retry logic is included to handle transient errors.

## Notes

- Make sure your API key, IAM user, and Google service account have the necessary permissions to perform the required actions.
- For large Airtable bases, the script may take some time to fetch all records due to API rate limits.

## Contributing

If you'd like to contribute to improving this script, feel free to open a pull request or submit an issue.

## License

This project is licensed under the MIT License.
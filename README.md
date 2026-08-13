# Bulk Airtable

A simple, focused Python package for bulk uploading and downloading files with Airtable, using S3 or Google Drive as intermediate storage.

## Installation

### Local Development
```bash
git clone https://github.com/sburl/bulkAirtable.git
cd bulkAirtable
pip install -e .
```

### Install from GitHub
```bash
pip install "git+https://github.com/sburl/bulkAirtable.git#egg=bulkAirtable[upload]"
```

## Configuration

1. Create a `.env` file in the root directory:

```env
# Airtable Config
BASE_ID=appXXXXXX
TABLE_ID=tblXXXXXX
AIRTABLE_TOKEN=patXXXXXX

# Storage Config (Choose "s3" or "gdrive")
USE_STORAGE=s3

# If using S3
AWS_ACCESS_KEY=your_key
AWS_SECRET_KEY=your_secret
S3_BUCKET_NAME=your_bucket

# If using Google Drive
GDRIVE_CREDENTIALS_PATH=path/to/credentials.json
```

2. **Airtable Permissions**: Your Personal Access Token needs:
   - `data.records:read`
   - `data.records:write`
   - `schema.bases:read`

## Usage

Since this is a package, you can run the modules directly:

### 1. Upload Files
Uploads a local folder to Airtable's attachment field via S3/GDrive.

```bash
python -m bulkAirtable.bulkUploadAirtable
```

From a source checkout, this can also be run directly:

```bash
python bulkAirtable/bulkUploadAirtable.py
```

Upload safety notes:
- S3 uploads use unique object keys and presigned 12-hour GET URLs, so the bucket does not need public read access.
- Google Drive cleanup deletes the uploaded Drive file by its returned file ID, not by local filename.
- Intermediate S3/Drive files are cleaned up only after Airtable confirms every uploaded file has a created record. If a batch fails or Airtable returns fewer records than requested, cleanup is skipped so files are not deleted prematurely.

### 2. Download Attachments
Downloads attachments from Airtable to your local machine, organized by file type.

```bash
python -m bulkAirtable.bulkDownloadAirtable
```

From a source checkout, this can also be run directly:

```bash
python bulkAirtable/bulkDownloadAirtable.py
```

"""
bulkAirtable - A Python package for bulk operations with Airtable.

Provides utilities for fetching, updating, uploading, and downloading
records and attachments from Airtable.
"""

from .client import (
    AirtableClient,
    fetch_records,
    update_records_batch,
    get_table_schema,
)

from .bulkUploadAirtable import (
    AirtableUploader,
    StorageBackend,
    S3Storage,
    GDriveStorage,
)

from .bulkDownloadAirtable import (
    AirtableDownloader,
)

__version__ = "0.1.0"
__all__ = [
    "AirtableClient",
    "fetch_records",
    "update_records_batch",
    "get_table_schema",
    "AirtableUploader",
    "StorageBackend",
    "S3Storage",
    "GDriveStorage",
    "AirtableDownloader",
]

"""
Airtable client utilities for fetching and updating records.
"""

import os
import json
import logging
from time import sleep
from typing import Optional

import requests
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AirtableClient:
    """
    A client for interacting with the Airtable API.
    
    Handles authentication, fetching records, and batch updates.
    """
    
    def __init__(
        self,
        base_id: Optional[str] = None,
        table_id: Optional[str] = None,
        token: Optional[str] = None,
        load_env: bool = True,
    ):
        """
        Initialize the Airtable client.
        
        Args:
            base_id: Airtable base ID (or set BASE_ID env var)
            table_id: Airtable table ID (or set TABLE_ID env var)
            token: Airtable API token (or set AIRTABLE_TOKEN env var)
            load_env: Whether to load from .env file
        """
        if load_env:
            load_dotenv()
        
        self.base_id = base_id or os.getenv("BASE_ID")
        self.table_id = table_id or os.getenv("TABLE_ID")
        self.token = token or os.getenv("AIRTABLE_TOKEN")
        
        if not all([self.base_id, self.table_id, self.token]):
            raise ValueError(
                "Missing required configuration. Provide base_id, table_id, and token "
                "either as arguments or via environment variables."
            )
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}/{self.table_id}"
    
    def fetch_records(
        self,
        view_name: Optional[str] = None,
        fields: Optional[list[str]] = None,
        filter_formula: Optional[str] = None,
    ) -> list[dict]:
        """
        Fetch all records from the table, handling pagination.
        
        Args:
            view_name: Optional view to filter by
            fields: Optional list of field names to return
            filter_formula: Optional Airtable formula to filter records
            
        Returns:
            List of record dictionaries
        """
        records = []
        params = {}
        
        if view_name:
            params["view"] = view_name
        if fields:
            params["fields[]"] = fields
        if filter_formula:
            params["filterByFormula"] = filter_formula
        
        while True:
            logger.debug(f"Fetching records with params: {params}")
            response = requests.get(self.base_url, params=params, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Error fetching records: {response.status_code}")
                try:
                    error_data = response.json()
                    logger.error(f"Error details: {error_data}")
                except Exception:
                    logger.error(f"Raw response: {response.text}")
                break
            
            data = response.json()
            records.extend(data.get("records", []))
            
            offset = data.get("offset")
            if offset:
                params["offset"] = offset
            else:
                break
        
        logger.info(f"Fetched {len(records)} records")
        return records
    
    def update_records_batch(
        self,
        updates: list[dict],
        batch_size: int = 10,
        delay: float = 0.25,
    ) -> list[dict]:
        """
        Update multiple records in batches.
        
        Airtable allows up to 10 records per PATCH request.
        
        Args:
            updates: List of dicts with 'id' and 'fields' keys
            batch_size: Number of records per batch (max 10)
            delay: Delay between batches in seconds
            
        Returns:
            List of updated record responses
        """
        batch_size = min(batch_size, 10)  # Airtable max is 10
        results = []
        
        for i in range(0, len(updates), batch_size):
            batch = updates[i : i + batch_size]
            
            payload = {"records": batch}
            
            retries = 3
            for attempt in range(retries):
                response = requests.patch(
                    self.base_url,
                    headers=self.headers,
                    data=json.dumps(payload),
                )
                
                if response.status_code == 200:
                    results.extend(response.json().get("records", []))
                    logger.info(f"Updated batch {i // batch_size + 1} ({len(batch)} records)")
                    break
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited. Waiting {wait_time}s...")
                    sleep(wait_time)
                else:
                    logger.error(f"Error updating batch (attempt {attempt + 1}): {response.status_code}")
                    try:
                        logger.error(f"Details: {response.json()}")
                    except Exception:
                        logger.error(f"Raw: {response.text}")
                    
                    if attempt < retries - 1:
                        sleep(2 ** attempt)
                    else:
                        logger.error(f"Failed to update batch after {retries} attempts")
            
            # Delay between batches to respect rate limits
            if i + batch_size < len(updates):
                sleep(delay)
        
        return results
    
    def create_records_batch(
        self,
        records: list[dict],
        batch_size: int = 10,
        delay: float = 0.25,
    ) -> list[dict]:
        """
        Create multiple records in batches.
        
        Args:
            records: List of dicts with 'fields' key
            batch_size: Number of records per batch (max 10)
            delay: Delay between batches in seconds
            
        Returns:
            List of created record responses
        """
        batch_size = min(batch_size, 10)
        results = []
        
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            
            payload = {"records": batch}
            
            retries = 3
            for attempt in range(retries):
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    data=json.dumps(payload),
                )
                
                if response.status_code == 200:
                    results.extend(response.json().get("records", []))
                    logger.info(f"Created batch {i // batch_size + 1} ({len(batch)} records)")
                    break
                elif response.status_code == 429:
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited. Waiting {wait_time}s...")
                    sleep(wait_time)
                else:
                    logger.error(f"Error creating batch (attempt {attempt + 1}): {response.status_code}")
                    if attempt < retries - 1:
                        sleep(2 ** attempt)
                    else:
                        logger.error(f"Failed to create batch after {retries} attempts")
            
            if i + batch_size < len(records):
                sleep(delay)
        
        return results
    
    def get_table_schema(self) -> Optional[dict]:
        """
        Get the schema for the current table.
        
        Returns:
            Table schema dictionary or None if not found
        """
        url = f"https://api.airtable.com/v0/meta/bases/{self.base_id}/tables"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            tables = response.json().get("tables", [])
            for table in tables:
                if table["id"] == self.table_id or table["name"] == self.table_id:
                    return table
        else:
            logger.error(f"Error fetching schema: {response.status_code}")
        
        return None
    
    def fetch_base_name(self) -> str:
        """
        Fetch the base name from Airtable metadata.
        
        Returns:
            Base name string
        """
        url = f"https://api.airtable.com/v0/meta/bases/{self.base_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json().get("name", "Unknown Base")
        except Exception as e:
            logger.warning(f"Could not fetch base name: {e}")
        
        return "Unknown Base"


# Convenience functions that use environment variables
def fetch_records(
    view_name: Optional[str] = None,
    fields: Optional[list[str]] = None,
    filter_formula: Optional[str] = None,
) -> list[dict]:
    """
    Fetch records using environment variables for configuration.
    
    See AirtableClient.fetch_records for details.
    """
    client = AirtableClient()
    return client.fetch_records(view_name=view_name, fields=fields, filter_formula=filter_formula)


def update_records_batch(
    updates: list[dict],
    batch_size: int = 10,
    delay: float = 0.25,
) -> list[dict]:
    """
    Update records in batches using environment variables for configuration.
    
    See AirtableClient.update_records_batch for details.
    """
    client = AirtableClient()
    return client.update_records_batch(updates=updates, batch_size=batch_size, delay=delay)


def get_table_schema() -> Optional[dict]:
    """
    Get table schema using environment variables for configuration.
    
    See AirtableClient.get_table_schema for details.
    """
    client = AirtableClient()
    return client.get_table_schema()

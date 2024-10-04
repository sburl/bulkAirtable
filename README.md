# Airtable Bulk Attachments Download

This Python script allows you to bulk download attachments from an Airtable base. It is designed to make it easy to collect files from records across multiple views and organize them locally based on file types or extensions. The script is configurable, enabling users to specify multiple desired file types, extensions, and views, as well as choose whether to organize downloaded files into folders by type.

## Features

- **Bulk Download**: Fetches all records from specified views in an Airtable base and downloads associated attachments.
- **Multiple File Types**: Allows you to specify desired file types (e.g., PDFs, images, etc.) and file extensions.
- **Organized Storage**: Optionally organizes downloaded files into folders based on their type or extension.
- **Handles Multiple Views**: Supports downloading attachments from multiple views in a single run.

## Prerequisites

- Python 3.7 or above
- Airtable API key
- Required Python libraries: `requests`, `python-dotenv`

To install the required libraries, run:

```sh
pip install requests python-dotenv
```

## Setup

1. **Clone the Repository**

   ```sh
   git clone https://github.com/yourusername/airtable-bulk-download.git
   cd airtable-bulk-download
   ```

2. **Environment Variables**
   Create a `.env` file in the project directory with the following variables:

   ```env
   BASE_ID=your_base_id
   TABLE_ID=your_table_id
   API_KEY=your_airtable_api_key
   ```

   Replace `your_base_id`, `your_table_id`, and `your_airtable_api_key` with your Airtable information.

## Configuration

- **Desired File Types**: Update the `desired_file_types` list in the script to specify which types of files you want to download (e.g., `application/pdf`, `image/jpeg`). Leave it empty to download all file types.
- **Desired File Extensions**: Update the `desired_file_extensions` list to specify file extensions you want to download (e.g., `pdf`, `jpg`). Leave it empty to download all extensions.
- **Desired View Names**: Update the `desired_view_names` list with the views you want to download attachments from (e.g., `View1`, `View2`). Leave it empty to download records from all views.
- **Organize by Directory**: Set the `organize_by_directory` variable to `True` if you want to organize downloaded files into folders based on their file extension.

## How to Use

1. **Run the Script**
   After configuring the script, run it with:

   ```sh
   python Airtable-Bulk-Attachments-Download.py
   ```

2. **Download Progress**
   The script will output log messages indicating the progress of fetching records and downloading attachments. Files will be saved in the current directory or in subfolders if the `organize_by_directory` option is enabled.

## Example

Suppose you have an Airtable base with multiple views and want to download all PDF and JPEG attachments from specific views, and you want them organized by file type. You would:

1. Set `desired_file_types = ["application/pdf", "image/jpeg"]`
2. Set `desired_file_extensions = ["pdf", "jpg"]`
3. Set `desired_view_names = ["Marketing", "Sales"]`
4. Set `organize_by_directory = True`

Running the script will create folders (`PDF`, `JPG`) and download the matching files into these folders.

## Error Handling

- If there are any issues with the Airtable API (e.g., incorrect credentials), the script will stop and print the error response.
- If there are issues with network connectivity, consider adding retry logic to handle transient errors.

## Notes

- Make sure your API key has the necessary permissions to access the base and tables.
- For large Airtable bases, the script may take some time to fetch all records due to API rate limits.

## Contributing

If you'd like to contribute to improving this script, feel free to open a pull request or submit an issue.

## License

This project is licensed under the MIT License.

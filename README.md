# FileIndex
A fast and efficient file indexing and search tool using SQLite.

## Description
FileIndex is a lightweight Python utility that indexes files in a directory tree and provides fast keyword-based search capabilities. It tracks file modification times to efficiently update the index and uses SQLite for persistent storage.


## Features

- Fast indexing - Quickly scans directory trees and stores file metadata
- Keyword search - Search files by multiple keywords (AND logic)
- Smart updates - Only updates files that have been modified
- Automatic cleanup - Removes deleted files from the index
- Performance tracking - Shows indexing time and statistics
- SQLite storage - Reliable and efficient database backend
- Error handling - Comprehensive error handling for robustness

## Installation
### Requirements

- Python 3.6 or higher
- SQLite3 (included with Python)

### Setup

1. Clone the repository:

```bash
# Cloner le dépôt
git clone https://github.com/MDVAurelien/fileindex.git
cd fileindex
````

2. Create a config.json file:
```json
{
  "dataset_path": "/mnt/pool/tank",
  "db_path": "fileindex.db"
}
````
## Usage
### Index files
Index all files in the configured directory:
```bash
python3 fileindex.py index
````

### Output example:
```bash
Indexing complete. 4752113 files indexed, 0 files removed.
Time elapsed: 932.47 seconds
````

### Search files
Search for files containing specific keywords in their path:
```bash
python3 fileindex.py search keyword1 keyword2
````
Examples:
```bash
# Find all PDF contains keyword uscend and 2025 in filename
python3 fileindex.py search uscend 2025 .pdf

# Find Python files in src directory
python3 fileindex.py search src .py

# Find configuration files
python3 fileindex.py search config

````

## How It Works

1. **Indexing**: The program walks through the directory tree, storing each file's path and modification time in a SQLite database
2. **Smart updates**: On subsequent runs, only modified files are updated
3. **Search**: Uses SQL LIKE queries for fast keyword matching against file paths
4. **Cleanup**: Automatically removes entries for deleted files

## Performance

- Initial indexing: ~500-1000 files/second (depends on disk speed)
- Subsequent updates: Only scans and updates modified files
- Search: Near-instantaneous for most queries

## Error Handling
### The program handles common errors gracefully:

- Missing or invalid config.json
- Non-existent dataset paths
- File permission errors
- Database errors
- Invalid commands

## Exit Codes

- 0: Success
- 1: Error occurred

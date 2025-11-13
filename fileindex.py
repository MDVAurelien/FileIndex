"""
FileIndex - Fast file indexing and search tool
Version: 1.1.0
License: LGPL-3.0
"""

import os, sqlite3, json, sys, time, fnmatch

def load_config():
    """
    Load configuration from config.json.
    
    Returns:
        dict: Configuration dictionary with dataset_path and db_path
        
    Exits:
        If config file is missing, invalid, or missing required fields
    """
    try:
        # Open and parse the JSON configuration file
        with open("config.json") as f:
            config = json.load(f)
        
        # Validate that required fields are present
        if "dataset_path" not in config:
            print("Error: 'dataset_path' missing in config.json")
            sys.exit(1)
        if "db_path" not in config:
            print("Error: 'db_path' missing in config.json")
            sys.exit(1)
        
        # Set default for exclude_extensions if not present
        if "exclude_extensions" not in config:
            config["exclude_extensions"] = []
        
        # Set default for exclude_patterns if not present
        if "exclude_patterns" not in config:
            config["exclude_patterns"] = []
        
        # Set default for exclude_directories if not present
        if "exclude_directories" not in config:
            config["exclude_directories"] = []
        
        # Set default for enable_exclusions (disabled by default)
        if "enable_exclusions" not in config:
            config["enable_exclusions"] = False
        
        return config
    except FileNotFoundError:
        print("Error: config.json file not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: config.json is not valid JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading config.json: {e}")
        sys.exit(1)


def index_files(dataset_path, db_name, exclude_extensions=None, exclude_patterns=None, exclude_directories=None, enable_exclusions=False):
    """
    Index all files from dataset_path into the database.
    Updates modified files and removes deleted files.
    
    Args:
        dataset_path (str): Root directory to scan for files
        db_name (str): Path to the SQLite database file
        exclude_extensions (list): List of file extensions to exclude (e.g., ['.tmp', '.log', '.pyc'])
        exclude_patterns (list): List of glob patterns to exclude files (e.g., ['*.tmp', 'backup_*'])
        exclude_directories (list): List of directory names/patterns to skip (e.g., ['__pycache__', '.git', 'node_modules'])
        enable_exclusions (bool): If False, ignore all exclusion rules and index everything
        
    Returns:
        bool: True if indexing succeeded, False otherwise
    """
    # Set default empty list if none provided
    if exclude_extensions is None:
        exclude_extensions = []
    if exclude_patterns is None:
        exclude_patterns = []
    if exclude_directories is None:
        exclude_directories = []
    
    # If exclusions are disabled, clear the exclusion lists
    if not enable_exclusions:
        exclude_extensions = []
        exclude_patterns = []
        exclude_directories = []
    
    # Normalize extensions to lowercase with leading dot
    exclude_extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                         for ext in exclude_extensions]
    # Validate that the dataset path exists
    if not os.path.exists(dataset_path):
        print(f"Error: Path '{dataset_path}' does not exist.")
        return False
    
    # Validate that the dataset path is a directory
    if not os.path.isdir(dataset_path):
        print(f"Error: '{dataset_path}' is not a directory.")
        return False

    try:
        # Record start time for performance measurement
        start_time = time.time()
        
        # Connect to SQLite database (creates it if it doesn't exist)
        db = sqlite3.connect(db_name)
        c = db.cursor()

        # Create table if it doesn't exist
        # path: full file path (primary key)
        # mtime: modification time (timestamp)
        c.execute("CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, mtime REAL)")

        # Retrieve all existing files from database
        # Build a dictionary for quick lookup: {path: mtime}
        c.execute("SELECT path, mtime FROM files")
        existing = {row[0]: row[1] for row in c.fetchall()}

        # Scan filesystem and update database
        scanned = set()  # Track all files found during scan
        errors = []      # Collect any errors encountered
        excluded = 0     # Count excluded files
        
        # Walk through all directories and subdirectories
        for root, dirs, files in os.walk(dataset_path):
            # Filter out excluded directories (modifies dirs in-place to prevent os.walk from descending)
            # Keep only directories that do NOT match any exclusion pattern
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pattern) for pattern in exclude_directories)]
            
            for f in files:
                # Build full path to file
                path = os.path.join(root, f)
                
                # Check if file extension should be excluded
                _, ext = os.path.splitext(path)
                if ext.lower() in exclude_extensions:
                    excluded += 1
                    continue
                
                # Check if filename matches any exclusion pattern
                # Use basename to match only the filename, not the full path
                if any(fnmatch.fnmatch(f, pattern) for pattern in exclude_patterns):
                    excluded += 1
                    continue
                
                try:
                    # Get file modification time
                    mtime = os.path.getmtime(path)
                    scanned.add(path)
                    
                    # Check if file already exists in database
                    if path in existing:
                        # Update only if modification time changed
                        if existing[path] != mtime:
                            c.execute("UPDATE files SET mtime=? WHERE path=?", (mtime, path))
                    else:
                        # Insert new file into database
                        c.execute("INSERT INTO files VALUES (?, ?)", (path, mtime))
                except OSError as e:
                    # Handle file access errors (permissions, etc.)
                    errors.append(f"Cannot access {path}: {e}")
                except Exception as e:
                    # Handle any other unexpected errors
                    errors.append(f"Error with {path}: {e}")

        # Remove files from database that no longer exist on filesystem
        deleted = 0
        for path in existing:
            if path not in scanned:
                c.execute("DELETE FROM files WHERE path=?", (path,))
                deleted += 1

        # Commit all changes to database
        db.commit()
        db.close()
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        # Display summary of indexing operation with timing
        print(f"Indexing complete. {len(scanned)} files indexed, {deleted} files removed.")
        if excluded > 0:
            print(f"Excluded {excluded} files based on extension/pattern filters.")
        print(f"Time elapsed: {elapsed_time:.2f} seconds")
        
        # Report any errors encountered during scan
        if errors:
            print(f"\n{len(errors)} error(s) encountered:")
            for error in errors[:10]:  # Show max 10 errors to avoid clutter
                print(f"  - {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")
        
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error during indexing: {e}")
        return False


def find_files(keywords, db_name):
    """
    Search for files containing all keywords in their path.
    All keywords must be present (AND operator).
    
    Args:
        keywords (list): List of keywords to search for
        db_name (str): Path to the SQLite database file
        
    Returns:
        list: List of tuples containing matching file paths, or None on error
    """
    try:
        # Connect to SQLite database
        db = sqlite3.connect(db_name)
        c = db.cursor()

        # Build WHERE clause dynamically with one LIKE condition per keyword
        # Example with 2 keywords: "path LIKE ? AND path LIKE ?"
        where_clause = " AND ".join(["path LIKE ?" for _ in keywords])

        # Add wildcard % around each keyword for partial matching
        # Example: "report" becomes "%report%"
        params = [f"%{kw}%" for kw in keywords]

        # Execute SQL query with all keywords
        # All keywords must match (AND logic)
        query = f"SELECT path FROM files WHERE {where_clause}"
        c.execute(query, params)
        results = c.fetchall()

        db.close()
        return results
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"Error during search: {e}")
        return None


if __name__ == "__main__":
    # Check that at least one command was provided
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 fileindex.py index                              # Index files")
        print("  python3 fileindex.py search [keyword1] [keyword2] ...   # Search files")
        sys.exit(1)

    # Get command (index or search) and convert to lowercase
    command = sys.argv[1].lower()
    
    # Load configuration from config.json
    config = load_config()
    dataset_path = config["dataset_path"]
    db_name = config["db_path"]
    exclude_extensions = config.get("exclude_extensions", [])
    exclude_patterns = config.get("exclude_patterns", [])
    exclude_directories = config.get("exclude_directories", [])
    enable_exclusions = config.get("enable_exclusions", False)

    # Handle "index" command
    if command == "index":
        success = index_files(dataset_path, db_name, exclude_extensions, exclude_patterns, exclude_directories, enable_exclusions)
        # Exit with appropriate code (0 = success, 1 = failure)
        sys.exit(0 if success else 1)
    
    # Handle "search" command
    elif command == "search":
        # Verify that at least one keyword was provided
        if len(sys.argv) < 3:
            print("Usage: python3 fileindex.py search [keyword1] [keyword2] ...")
            sys.exit(1)
        
        # Extract all keywords from command line arguments
        keywords = sys.argv[2:]
        matches = find_files(keywords, db_name)

        # Handle search results
        if matches is None:
            # Error occurred during search
            sys.exit(1)
        elif matches:
            # Display all matching file paths
            for (path,) in matches:
                print(path)
        else:
            # No files found matching the criteria
            print("No files found.")
    
    # Handle unknown commands
    else:
        print(f"Unknown command: {command}")
        print("Use 'index' or 'search'")
        sys.exit(1)

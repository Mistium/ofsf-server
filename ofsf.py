"""Legacy OFSF file format utilities.

This module provides utilities for working with the legacy .ofsf file format.
Note: The current server implementation uses FSAdapter instead of these functions.
This module is kept for compatibility and potential migration purposes.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

def handle_ofsf_update(name: str, updates: Union[str, List[Dict[str, Any]]]) -> Dict[str, str]:
    """Handle OFSF format updates (legacy function).
    
    Args:
        name: Username
        updates: List of update operations or JSON string
        
    Returns:
        Dictionary with operation result
        
    Note:
        This is a legacy function. New code should use FSAdapter instead.
    """
    if not name or not name.strip():
        return {"payload": "Invalid user name"}
        
    try:
        if isinstance(updates, str):
            updates = json.loads(updates)
        
        if not isinstance(updates, list) or not updates:
            return {"payload": "Invalid update format or empty updates"}
            
        sender_name = name.strip()
        update_files = load_files_as_uuid_object_for_user(sender_name)
        print(f"\033[92m[+] OFSF\033[0m | {sender_name} processing {len(updates)} file updates")
        
        errors = []
        processed = 0
        
        for i, change in enumerate(updates):
            try:
                if isinstance(change, str):
                    change = json.loads(change)
                    
                if not isinstance(change, dict):
                    errors.append(f"Update {i}: Invalid format")
                    continue
                
                command = change.get("command", "")
                uuid = change.get("uuid", "")
                
                if command == "UUIDa":
                    data = change.get("dta")
                    if not isinstance(data, list) or len(data) != 14:
                        errors.append(f"Update {i}: Invalid data format for add operation")
                        continue
                        
                    print(f"\033[92m[+] OFSF\033[0m | Adding file {uuid}")
                    update_files[uuid] = data
                    processed += 1
                
                elif command == "UUIDr":
                    if uuid not in update_files:
                        errors.append(f"Update {i}: UUID {uuid} not found")
                        continue
                        
                    idx = change.get("idx")
                    dta = change.get("dta")
                    
                    if idx is None or dta is None:
                        errors.append(f"Update {i}: Missing index or data")
                        continue
                        
                    try:
                        idx = int(idx)
                        if idx < 0 or idx >= len(update_files[uuid]):
                            errors.append(f"Update {i}: Index {idx} out of range")
                            continue
                            
                        if not isinstance(dta, (str, int, float, bool, type(None))):
                            dta = json.dumps(dta)
                            
                        print(f"\033[93m[~] OFSF\033[0m | Updating file {uuid} chunk {idx}")
                        update_files[uuid][idx] = dta
                        processed += 1
                    except (ValueError, IndexError) as e:
                        errors.append(f"Update {i}: {e}")
                
                elif command == "UUIDd":
                    if uuid in update_files:
                        print(f"\033[93m[~] OFSF\033[0m | Deleting file {uuid}")
                        del update_files[uuid]
                        processed += 1
                    else:
                        errors.append(f"Update {i}: UUID {uuid} not found for deletion")
                        
                else:
                    errors.append(f"Update {i}: Unknown command '{command}'")
                    
            except json.JSONDecodeError as e:
                errors.append(f"Update {i}: JSON decode error - {e}")
            except Exception as e:
                errors.append(f"Update {i}: Unexpected error - {e}")
        
        flattened = [item for sublist in update_files.values() for item in sublist]
        result_data = json.dumps(flattened)
        
        if update_user_file_system(sender_name.lower(), result_data):
            print(f"\033[92m[+] OFSF\033[0m | Updated {sender_name} ({processed} operations, {len(errors)} errors)")
            result = {"payload": "Successfully Updated Origin Files"}
            if errors:
                result["errors"] = errors
                result["processed"] = processed
            return result
        else:
            return {"payload": "Failed to save file system"}
    
    except Exception as e:
        print(f"\033[91m[-] OFSF Error\033[0m | Error in handle_ofsf_update: {e}")
        return {"payload": "Error processing update"}


def create_file_system(name: str) -> bool:
    """Create a new OFSF file system for a user.
    
    Args:
        name: Username
        
    Returns:
        True if created successfully, False if already exists
    """
    if not name or not name.strip():
        return False
        
    file_path = Path(f"./files/{name.strip().lower()}.ofsf")
    
    if file_path.exists():
        return False
        
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return True
    except Exception as e:
        print(f"Error creating file system for {name}: {e}")
        return False

def load_files_as_uuid_object_for_user(name: str) -> Dict[str, List[Any]]:
    """Load user files from OFSF format into UUID-indexed dictionary.
    
    Args:
        name: Username
        
    Returns:
        Dictionary mapping UUIDs to file chunk arrays
    """
    if not name or not name.strip():
        return {}
        
    file_path = Path(f"./files/{name.strip().lower()}.ofsf")
    result = {}
    
    try:
        if not file_path.exists():
            print(f"\033[93m[~] OFSF\033[0m | No file system found for {name}, creating empty one")
            return {}

        with open(file_path, 'r', encoding='utf-8') as f:
            file_data = f.read().strip()

        if not file_data:
            return {}

        files_list = json.loads(file_data)
        if not isinstance(files_list, list):
            print(f"\033[91m[-] OFSF Error\033[0m | Invalid file format for {name}")
            return {}
            
        file_count = len(files_list) // 14
        print(f"\033[93m[~] OFSF\033[0m | Loaded {file_count} files for {name}")
            
        for i in range(0, len(files_list), 14):
            file_entry = files_list[i:i + 14]
            if len(file_entry) != 14:
                print(f"\033[91m[-] OFSF Warning\033[0m | Skipping malformed file entry at index {i}")
                continue
                
            uuid = file_entry[13]
            if not uuid:
                print(f"\033[91m[-] OFSF Warning\033[0m | Skipping file entry with empty UUID at index {i}")
                continue
                
            result[uuid] = file_entry
            
    except json.JSONDecodeError as e:
        print(f"\033[91m[-] OFSF Error\033[0m | JSON decode error for user {name}: {e}")
    except Exception as e:
        print(f"\033[91m[-] OFSF Error\033[0m | Error loading files for user {name}: {e}")
    
    return result

def update_user_file_system(name: str, data: str) -> bool:
    """Update user's OFSF file system with new data.
    
    Args:
        name: Username
        data: JSON string containing file system data
        
    Returns:
        True if update successful, False otherwise
    """
    if not name or not name.strip():
        return False
        
    if not isinstance(data, str):
        return False
        
    file_path = Path(f"./files/{name.strip().lower()}.ofsf")
    
    try:
        json.loads(data)
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(data)
        return True
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON data for user {name}: {e}")
        return False
    except Exception as e:
        print(f"Error updating files for user {name}: {e}")
        return False
    
def delete_user_file_system(name: str) -> bool:
    """Delete user's OFSF file system.
    
    Args:
        name: Username
        
    Returns:
        True if deletion successful or file didn't exist, False on error
    """
    if not name or not name.strip():
        return False
        
    file_path = Path(f"./files/{name.strip().lower()}.ofsf")
    
    if not file_path.exists():
        print(f"No files found for user {name} to delete")
        return True  # Consider non-existent file as successful deletion
        
    try:
        file_path.unlink()
        print(f"Successfully deleted files for user {name}")
        return True
    except Exception as e:
        print(f"Error deleting files for user {name}: {e}")
        return False
    
def get_user_file_size(name: str) -> Optional[str]:
    """Get formatted file size for user's OFSF file system.
    
    Args:
        name: Username
        
    Returns:
        Formatted file size string or None if file doesn't exist
    """
    if not name or not name.strip():
        return None
        
    file_path = Path(f"./files/{name.strip().lower()}.ofsf")
    
    if not file_path.exists():
        return None
        
    try:
        size_bytes = file_path.stat().st_size
        
        if size_bytes >= 1 << 30:  # >= 1 GB
            return f"{size_bytes / (1 << 30):.2f} GB"
        elif size_bytes >= 1 << 20:  # >= 1 MB
            return f"{size_bytes / (1 << 20):.2f} MB"
        elif size_bytes >= 1 << 10:  # >= 1 KB
            return f"{size_bytes / (1 << 10):.2f} KB"
        else:
            return f"{size_bytes} bytes"
            
    except Exception as e:
        print(f"Error reading file size for user {name}: {e}")
        return "0 bytes"
    
def exists_user_file_system(name: str) -> bool:
    """Check if user's OFSF file system exists.
    
    Args:
        name: Username
        
    Returns:
        True if file system exists, False otherwise
    """
    if not name or not name.strip():
        return False
        
    file_path = Path(f"./files/{name.strip().lower()}.ofsf")
    return file_path.exists()

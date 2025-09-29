import json
import os

def handleOFSFupdate(name, updates):
    try:
        if isinstance(updates, str):
            updates = json.loads(updates)
        
        update_list = []

        update_list = list(updates.get("payload", []))
        
        offset = updates.get("offset", "")
        
        if len(update_list) > 0 and isinstance(update_list, list) and offset.upper() == "UUID":
            sender_name = name
            update_files = load_files_as_uuid_object_for_user(sender_name)
            print(f"\033[92m[+] OFSF\033[0m | {sender_name} processing {len(update_list)} file updates")
            
            while update_list:
                try:
                    change = update_list[0]
                    if isinstance(change, str):
                        change = json.loads(change)
                    
                    command = change.get("command", "")
                    
                    if command == "UUIDa":
                        uuid = change.get('uuid', 'Unknown')
                        print(f"\033[92m[+] OFSF\033[0m | Adding file {uuid}")
                        if isinstance(change.get("dta"), list) and len(change.get("dta", [])) > 13:
                            update_files[change["dta"][13]] = change.get("dta", "")
                    
                    elif command == "UUIDr":
                        idx = change.get("idx")
                        if isinstance(idx, str):
                            idx = int(idx)
                        
                        dta = change.get("dta")
                        if not isinstance(dta, (str, int, float, bool, type(None))):
                            dta = json.dumps(dta)
                        
                        uuid = change.get("uuid")
                        if uuid in update_files:
                            idx = max(0, idx - 1) if idx is not None else 0
                            update_files[uuid][idx] = dta
                    
                    elif command == "UUIDd":
                        if change.get("uuid") in update_files:
                            print(f"\033[93m[~] OFSF\033[0m | Deleting file {change.get('uuid')}")
                            del update_files[change.get("uuid")]
                except Exception as e:
                    print(f"\033[91m[-] OFSF Error\033[0m | Error processing change: {e}")
                update_list.pop(0)
            
            flattened = [item for sublist in update_files.values() for item in sublist]
            result_data = json.dumps(flattened)

            update_user_file_system(sender_name.lower(), result_data)
            print(f"\033[92m[+] OFSF\033[0m | Updated {sender_name}")
            return {"payload": "Successfully Updated Origin Files"}
        else:
            return {"payload": "Invalid update format or not logged in"}
    
    except Exception as e:
        print(f"\033[91m[-] OFSF Error\033[0m | Error in handleOFSFupdate: {e}")
        return {"payload": "Error processing update"}


def create_file_system(name):
    file_path = f"./files/{name}.ofsf"
    
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            f.write("[]")
        return True
    else:
        return False

def load_files_as_uuid_object_for_user(name):  
    file_path = f"./files/{name}.ofsf"
    result = {}
    
    try:
        if not os.path.exists(file_path):
            create_file_system(name)

        with open(file_path, 'r') as f:
            file_data = f.read()

        if file_data:
            files_list = json.loads(file_data)
            file_count = len(files_list)//14
            print(f"\033[93m[~] OFSF\033[0m | Loaded {file_count} files for {name}")
            
            for i in range(0, len(files_list), 14):
                file_entry = files_list[i:i + 14]
                if len(file_entry) == 14:
                    uuid = file_entry[13]
                    result[uuid] = file_entry
    except Exception as e:
        print(f"\033[91m[-] OFSF Error\033[0m | Error loading files for user {name}: {e}")
    
    return result

def update_user_file_system(name, data):
    file_path = f"./files/{name}.ofsf"
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    try:
        with open(file_path, 'w') as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"Error updating files for user {name}: {e}")
        return False
    
def delete_user_file_system(name):
    file_path = f"./files/{name}.ofsf"
    
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"Successfully deleted files for user {name}")
            return True
        except Exception as e:
            print(f"Error deleting files for user {name}: {e}")
            return False
    else:
        print(f"No files found for user {name} to delete")
        return False
    
def get_user_file_size(name):
    file_path = f"./files/{name}.ofsf"
    
    if os.path.exists(file_path):
        try:
            size_bytes = os.path.getsize(file_path)
            if size_bytes >= 1 << 30:
                usage_data = f"{size_bytes / (1 << 30):.4f} GB"
            elif size_bytes >= 1 << 20:
                usage_data = f"{size_bytes / (1 << 20):.2f} MB"
            elif size_bytes >= 1 << 10:
                usage_data = f"{size_bytes / (1 << 10):.2f} KB"
            else:
                usage_data = f"{size_bytes} bytes"
            return usage_data
        except Exception as e:
            print(f"Error reading file size for user {name}: {e}")
            return "0 bytes"
    else:
        print(f"No files found for user {name}")
        return None
    
def exists_user_file_system(name):
    file_path = f"./files/{name}.ofsf"
    
    if os.path.exists(file_path):
        return True
    else:
        return False
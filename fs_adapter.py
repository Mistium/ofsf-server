import json
import os
from pathlib import Path, PurePosixPath
from typing import Dict, List, Any, Optional, Tuple, Union
from uuid import uuid4

class FSAdapter:
    """File system adapter for managing user files and folders with UUID-based indexing."""
    
    CHUNK_SIZE = 14
    
    def __init__(self, user_name: str) -> None:
        """Initialize FSAdapter for a specific user.
        
        Args:
            user_name: Username (will be converted to lowercase)
        """
        if not user_name or not user_name.strip():
            raise ValueError("User name cannot be empty")
            
        self.user_name = user_name.lower().strip()
        self.root_path = Path("./files")
        self.root_path.mkdir(parents=True, exist_ok=True)
        self.base_path = self.root_path / self.user_name
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root_path / f"{self.user_name}.json"

        legacy_index = self.base_path / "index.json"
        if not self.index_path.exists():
            if legacy_index.exists():
                try:
                    with open(legacy_index, 'r', encoding='utf-8') as legacy_file:
                        legacy_data = json.load(legacy_file)
                    with open(self.index_path, 'w', encoding='utf-8') as new_index:
                        json.dump(legacy_data, new_index, indent=2)
                except Exception as exc:
                    print(f"Warning: Failed to migrate legacy index for {self.user_name}: {exc}")
                    self._save_index({})
                else:
                    try:
                        legacy_index.unlink()
                    except OSError:
                        pass
            else:
                self._save_index({})
    
    def _load_index(self) -> Dict[str, Dict[str, str]]:
        """Load the file index from disk.
        
        Returns:
            Dictionary mapping UUIDs to file metadata
        """
        try:
            with open(self.index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load index, creating new one: {e}")
            return {}
    
    def _save_index(self, index: Dict[str, Dict[str, str]]) -> None:
        """Save the file index to disk.
        
        Args:
            index: Dictionary mapping UUIDs to file metadata
        """
        try:
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save index: {e}")
    
    def _sanitize_relative_path_str(self, value: Optional[str]) -> str:
        """Normalize path string to a relative form without leading slashes."""
        if not value:
            return ""

        sanitized = value.replace("\\", "/").strip()
        while sanitized.startswith("/"):
            sanitized = sanitized[1:]

        if sanitized in ("", "."):
            return ""

        # Prevent traversal components
        pure_path = PurePosixPath(sanitized)
        components: List[str] = []
        for part in pure_path.parts:
            if part in ("", "."):
                continue
            if part == "..":
                raise ValueError("Path traversal is not allowed")
            components.append(part)

        return "/".join(components)

    def _normalize_subpath(self, subpath: Optional[str]) -> Tuple[Path, str]:
        """Normalize client-provided subpath to ensure it stays within the user base path."""
        relative_str = self._sanitize_relative_path_str(subpath)

        if not relative_str:
            return self.base_path, ""

        pure_path = PurePosixPath(relative_str)
        parts: List[str] = []
        for part in pure_path.parts:
            if part in ("", "."):
                continue
            parts.append(part)

        relative_path = "/".join(parts)
        target_path = self.base_path.joinpath(*parts)

        try:
            target_path.relative_to(self.base_path)
        except ValueError as exc:
            raise ValueError("Invalid path outside user directory") from exc

        target_path.mkdir(parents=True, exist_ok=True)
        return target_path, relative_path

    def _get_unique_name(self, base_path: Path, name: str, is_folder: bool = False) -> str:
        """Generate a unique name by appending counter if needed.
        
        Args:
            base_path: Directory where the item will be created
            name: Desired name
            is_folder: Whether this is a folder (affects path checking)
            
        Returns:
            Unique name that doesn't conflict with existing items
        """
        if is_folder:
            target_path = base_path / name
            if not target_path.exists():
                return name
        else:
            if not any(f.stem == Path(name).stem for f in base_path.glob(f"{Path(name).stem}*") if f.is_file()):
                return name
        
        base_name = name
        counter = 1
        while True:
            new_name = f"{base_name} ({counter})"
            if is_folder:
                if not (base_path / new_name).exists():
                    return new_name
            else:
                stem = Path(new_name).stem
                if not any(f.stem == stem for f in base_path.glob(f"{stem}*") if f.is_file()):
                    return new_name
            counter += 1
    
    def add_file(self, uuid: str, chunks: List[Any]) -> Dict[str, str]:
        """Add a file or folder to the filesystem.
        
        Args:
            uuid: Unique identifier for the file
            chunks: List of file data chunks (must be exactly 14 items)
            
        Returns:
            Dictionary with actual_name and actual_path of created item
            
        Raises:
            ValueError: If chunks format is invalid
            RuntimeError: If file creation fails
        """
        if not uuid or not isinstance(uuid, str):
            raise ValueError("UUID must be a non-empty string")
            
        if not isinstance(chunks, list) or len(chunks) != self.CHUNK_SIZE:
            raise ValueError(f"File must have exactly {self.CHUNK_SIZE} chunks")
            
        index = self._load_index()
        if uuid in index:
            raise ValueError(f"UUID {uuid} already exists")
        file_type = chunks[0] or ""
        name = chunks[1] or "untitled"
        path = chunks[2] or ""

        target_dir, relative_path = self._normalize_subpath(path)

        try:
            if file_type == ".folder":
                return self._create_folder(uuid, name, target_dir, relative_path, chunks, index)
            else:
                return self._create_file(uuid, name, file_type, target_dir, relative_path, chunks, index)
        except Exception as e:
            raise RuntimeError(f"Failed to create {'folder' if file_type == '.folder' else 'file'}: {e}")

    def _create_folder(
        self,
        uuid: str,
        name: str,
        target_dir: Path,
        parent_relative_path: str,
        chunks: List[Any],
        index: Dict[str, Dict[str, str]]
    ) -> Dict[str, str]:
        """Create a folder with unique name."""
        unique_name = self._get_unique_name(target_dir, name, is_folder=True)
        folder_path = target_dir / unique_name

        folder_path.mkdir(exist_ok=False)

        updated_chunks = chunks.copy()
        updated_chunks[1] = unique_name
        updated_chunks[2] = parent_relative_path

        metadata_path = folder_path / ".folder.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(updated_chunks, f, indent=2)

        index[uuid] = {
            "type": "folder",
            "path": str(metadata_path),
            "dir_path": str(folder_path),
            "name": unique_name,
            "parent_path": parent_relative_path
        }
        self._save_index(index)

        components = [comp for comp in parent_relative_path.split("/") if comp]
        components.append(unique_name)
        folder_relative = "/".join(components)

        return {
            "actual_name": unique_name,
            "actual_path": folder_relative
        }

    def _create_file(
        self,
        uuid: str,
        name: str,
        file_type: str,
        target_dir: Path,
        parent_relative_path: str,
        chunks: List[Any],
        index: Dict[str, Dict[str, str]]
    ) -> Dict[str, str]:
        """Create a file with unique name."""
        filename = f"{name}{file_type}" if file_type else name
        unique_filename = self._get_unique_name(target_dir, filename, is_folder=False)

        if file_type:
            unique_name = unique_filename.replace(file_type, "")
        else:
            unique_name = Path(unique_filename).stem
            
        file_path = target_dir / unique_filename

        updated_chunks = chunks.copy()
        updated_chunks[1] = unique_name
        updated_chunks[2] = parent_relative_path

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(updated_chunks, f, indent=2)

        index[uuid] = {
            "type": "file",
            "path": str(file_path),
            "name": unique_filename,
            "parent_path": parent_relative_path
        }
        self._save_index(index)
        
        return {
            "actual_name": unique_filename,
            "actual_path": parent_relative_path
        }
    
    def update_chunk(self, uuid: str, chunk_idx: int, new_data: Any) -> bool:
        """Update a specific chunk of a file.
        
        Args:
            uuid: File UUID
            chunk_idx: Index of chunk to update (1-based as provided by client)
            new_data: New data for the chunk
            
        Returns:
            True if update successful, False otherwise
        """
        if not uuid or not isinstance(uuid, str):
            return False
            
        if not isinstance(chunk_idx, int) or chunk_idx < 0:
            return False
            
        index = self._load_index()
        if uuid not in index:
            return False

        entry = index[uuid]
        entry_type = entry.get("type")
        metadata_path = Path(entry.get("path", ""))

        if entry_type == "folder":
            if not metadata_path.exists():
                return False
        elif entry_type == "file":
            if not metadata_path.exists():
                return False
        else:
            return False
            
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
                
            adjusted_idx = chunk_idx - 1 if chunk_idx > 0 else chunk_idx
            if adjusted_idx < 0 or adjusted_idx >= len(chunks):
                return False
                
            if adjusted_idx == 2:
                try:
                    sanitized = self._sanitize_relative_path_str(str(new_data))
                except ValueError as exc:
                    print(f"Invalid path update for {uuid}: {exc}")
                    return False
                chunks[adjusted_idx] = sanitized
            else:
                chunks[adjusted_idx] = new_data
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error updating chunk: {e}")
            return False
    
    def delete_file(self, uuid: str) -> bool:
        """Delete a file or folder.
        
        Args:
            uuid: UUID of item to delete
        
        Returns:
            True if deletion successful, False otherwise
        """
        if not uuid or not isinstance(uuid, str):
            return False
        
        index = self._load_index()
        if uuid not in index:
            return False
        
        entry = index[uuid]
        entry_type = entry.get("type")
        metadata_path = Path(entry.get("path", "")) if entry.get("path") else None
        dir_path_str = entry.get("dir_path")
        dir_path = Path(dir_path_str) if dir_path_str else (metadata_path.parent if metadata_path else None)
        
        try:
            if entry_type == "file":
                if metadata_path and metadata_path.exists():
                    metadata_path.unlink()
            elif entry_type == "folder":
                if dir_path and dir_path.exists():
                    import shutil
                    shutil.rmtree(dir_path)
                elif metadata_path and metadata_path.exists():
                    metadata_path.unlink()
                else:
                    # If the file/folder doesn't exist, just remove the index entry
                    del index[uuid]
                    self._save_index(index)
                    return True

            del index[uuid]
            self._save_index(index)
            return True
        except Exception as e:
            print(f"Error deleting item: {e}")
    
    def get_ofsf(self) -> str:
        """Get all files in OFSF format.
        
        Returns:
            JSON string containing flattened file data
        """
        index = self._load_index()
        ofsf_data: List[Any] = []

        for uuid, entry in index.items():
            try:
                entry_type = entry.get("type")
                metadata_path_str = entry.get("path", "")
                metadata_path = Path(metadata_path_str) if metadata_path_str else None
                chunks: Optional[List[Any]] = None

                if metadata_path and metadata_path.exists():
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        loaded = json.load(f)
                    if isinstance(loaded, list) and len(loaded) == self.CHUNK_SIZE:
                        chunks = loaded
                        chunks[2] = self._sanitize_relative_path_str(chunks[2])

                if entry_type == "folder":
                    if chunks:
                        ofsf_data.extend(chunks)
                        continue

                    folder_name = entry.get("name", "")
                    parent_path = self._sanitize_relative_path_str(entry.get("parent_path")) if entry.get("parent_path") else ""

                    dir_path_str = entry.get("dir_path", "")
                    folder_path = Path(dir_path_str) if dir_path_str else None
                    if folder_path and folder_path.exists():
                        relative_path = folder_path.relative_to(self.base_path)
                        folder_name = folder_name or relative_path.name if str(relative_path) != "." else folder_path.name
                        parent_rel = relative_path.parent
                        parent_path = parent_path or ("" if str(parent_rel) == "." else str(parent_rel))
                    elif metadata_path and metadata_path.parent.exists():
                        folder_name = folder_name or metadata_path.parent.name
                        relative_parent = metadata_path.parent.relative_to(self.base_path)
                        parent_path = parent_path or ("" if str(relative_parent.parent) == "." else str(relative_parent.parent))

                    ofsf_data.extend([
                        ".folder",
                        folder_name,
                        parent_path,
                        "", "", "", "", "", "", "", "", "",
                        uuid
                    ])
                else:
                    if not chunks and metadata_path and metadata_path.exists():
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            loaded = json.load(f)
                        if isinstance(loaded, list) and len(loaded) == self.CHUNK_SIZE:
                            chunks = loaded
                            chunks[2] = self._sanitize_relative_path_str(chunks[2])
                    if chunks:
                        ofsf_data.extend(chunks)
            except Exception as e:
                print(f"Error processing {uuid}: {e}")
                continue

        return json.dumps(ofsf_data)

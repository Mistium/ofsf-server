# OFSF Server

A file system management API server that provides REST endpoints for managing user file systems with UUID-based operations.

## Features

- **File Management**: Create, update, and delete files and folders
- **UUID-based Operations**: Each file/folder has a unique identifier
- **Path Management**: Automatic handling of duplicate names and path construction
- **Error Handling**: Comprehensive error handling with detailed responses
- **Type Safety**: Full type hints throughout the codebase

## API Endpoints

### GET /files/{username}
Get user's file system in OFSF format.

**Response:**
```json
{
  "status": "success",
  "data": [...],
  "user": "username"
}
```

### POST /files/{username}
Update user's file system with batch operations.

**Request Body:**
```json
[
  {
    "command": "UUIDa",
    "uuid": "file-uuid",
    "dta": [14-element array]
  },
  {
    "command": "UUIDr", 
    "uuid": "file-uuid",
    "idx": 0,
    "dta": "new data"
  },
  {
    "command": "UUIDd",
    "uuid": "file-uuid"
  }
]
```

**Commands:**
- `UUIDa`: Add file/folder
- `UUIDr`: Update file chunk
- `UUIDd`: Delete file/folder

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python server.py
```

The server will start on `http://0.0.0.0:8080`

## File Structure

- `server.py`: Main Flask application with API endpoints
- `fs_adapter.py`: File system adapter for managing files and folders
- `ofsf.py`: Legacy OFSF format utilities (for compatibility)
- `files/`: Directory where user files are stored

## Architecture

The server uses a two-tier storage system:

1. **FSAdapter**: Modern file system adapter that stores files individually with JSON metadata
2. **Legacy OFSF**: Older format that stores all files in a single JSON array (kept for compatibility)

Each user gets their own directory under `files/{username}/` with an `index.json` file tracking all their files and folders.

## Error Handling

The API returns consistent error responses:

```json
{
  "error": "Error description",
  "status": "error"
}
```

HTTP status codes:
- `200`: Success
- `207`: Partial success (some operations failed)
- `400`: Bad request
- `404`: Not found
- `405`: Method not allowed
- `500`: Internal server error

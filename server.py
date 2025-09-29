"""OFSF Server - File system management API.

Provides REST endpoints for managing user file systems with UUID-based operations.
Supports file/folder creation, updates, and deletion with proper error handling.
"""

import json
from typing import Dict, Any, List, Union

import flask
import flask_cors

import fs_adapter

app = flask.Flask(__name__)
cors = flask_cors.CORS(app)

# Standard error responses
ERROR_RESPONSES = {
    'invalid_request': {'error': 'Invalid request format', 'status': 'error'},
    'user_not_found': {'error': 'User not found', 'status': 'error'},
    'processing_error': {'error': 'Error processing request', 'status': 'error'},
    'file_system_error': {'error': 'File system operation failed', 'status': 'error'}
}

@app.route('/files/<name>', methods=['GET'])
def get_user_file_system(name: str) -> flask.Response:
    """Get user's file system in OFSF format.
    
    Args:
        name: Username
        
    Returns:
        JSON response with file system data or error
    """
    if not name or not name.strip():
        return flask.jsonify(ERROR_RESPONSES['invalid_request']), 400
        
    try:
        adapter = fs_adapter.FSAdapter(name.strip())
        ofsf_data = json.loads(adapter.get_ofsf())
        return flask.jsonify(ofsf_data)
    except ValueError as e:
        print(f"\033[91m[-] FS Error\033[0m | Invalid user name '{name}': {e}")
        return flask.jsonify(ERROR_RESPONSES['invalid_request']), 400
    except Exception as e:
        print(f"\033[91m[-] FS Error\033[0m | Error in get_user_file_system for '{name}': {e}")
        return flask.jsonify(ERROR_RESPONSES['processing_error']), 500

@app.route('/files/<name>', methods=['POST'])
def update_user_file_system(name: str) -> flask.Response:
    """Update user's file system with batch operations.
    
    Args:
        name: Username
        
    Returns:
        JSON response with operation results or error
    """
    if not name or not name.strip():
        return flask.jsonify(ERROR_RESPONSES['invalid_request']), 400
        
    try:
        updates = flask.request.get_json()
        if not updates:
            return flask.jsonify(ERROR_RESPONSES['invalid_request']), 400
            
        if not isinstance(updates, list):
            return flask.jsonify({
                'error': 'Updates must be a list of operations',
                'status': 'error'
            }), 400

        adapter = fs_adapter.FSAdapter(name.strip())
        response_data = []
        errors = []

        for i, change in enumerate(updates):
            try:
                if isinstance(change, str):
                    change = json.loads(change)
                    
                if not isinstance(change, dict):
                    errors.append(f"Operation {i}: Invalid format, expected object")
                    continue

                command = change.get("command", "")
                uuid = change.get("uuid", "")
                
                if not uuid:
                    errors.append(f"Operation {i}: Missing UUID")
                    continue

                if command == "UUIDa":
                    dta = change.get("dta")
                    if not dta:
                        errors.append(f"Operation {i}: Missing data for add operation")
                        continue
                        
                    result = adapter.add_file(uuid, dta)
                    response_data.append({
                        "operation": "add",
                        "uuid": uuid,
                        "actual_name": result["actual_name"],
                        "actual_path": result["actual_path"],
                        "status": "success"
                    })
                    
                elif command == "UUIDr":
                    idx = change.get("idx")
                    dta = change.get("dta")
                    
                    if idx is None or dta is None:
                        errors.append(f"Operation {i}: Missing index or data for update operation")
                        continue
                        
                    success = adapter.update_chunk(uuid, int(idx), dta)
                    response_data.append({
                        "operation": "update",
                        "uuid": uuid,
                        "chunk_index": int(idx),
                        "status": "success" if success else "failed"
                    })
                    
                    if not success:
                        errors.append(f"Operation {i}: Failed to update chunk {idx} for UUID {uuid}")
                        
                elif command == "UUIDd":
                    success = adapter.delete_file(uuid)
                    response_data.append({
                        "operation": "delete",
                        "uuid": uuid,
                        "status": "success" if success else "failed"
                    })
                    
                    if not success:
                        errors.append(f"Operation {i}: Failed to delete UUID {uuid}")
                        
                else:
                    errors.append(f"Operation {i}: Unknown command '{command}'")
                    
            except json.JSONDecodeError as e:
                errors.append(f"Operation {i}: Invalid JSON format - {e}")
            except ValueError as e:
                errors.append(f"Operation {i}: {e}")
            except Exception as e:
                errors.append(f"Operation {i}: Unexpected error - {e}")

        # Prepare response
        response = {
            "status": "success" if not errors else "partial_success" if response_data else "error",
            "message": "File system updated successfully",
            "operations_completed": len(response_data),
            "operations_failed": len(errors),
            "details": response_data,
            "user": name.strip().lower()
        }
        
        if errors:
            response["errors"] = errors
            
        status_code = 200 if not errors else 207 if response_data else 400
        return flask.jsonify(response), status_code
        
    except ValueError as e:
        print(f"\033[91m[-] FS Error\033[0m | Invalid user name '{name}': {e}")
        return flask.jsonify(ERROR_RESPONSES['invalid_request']), 400
    except Exception as e:
        print(f"\033[91m[-] FS Error\033[0m | Error in update_user_file_system for '{name}': {e}")
        return flask.jsonify(ERROR_RESPONSES['processing_error']), 500

@app.errorhandler(404)
def not_found(error) -> flask.Response:
    """Handle 404 errors."""
    return flask.jsonify({
        'error': 'Endpoint not found',
        'status': 'error',
        'message': 'The requested resource was not found'
    }), 404

@app.errorhandler(405)
def method_not_allowed(error) -> flask.Response:
    """Handle 405 errors."""
    return flask.jsonify({
        'error': 'Method not allowed',
        'status': 'error',
        'message': 'The requested method is not allowed for this endpoint'
    }), 405

@app.errorhandler(500)
def internal_error(error) -> flask.Response:
    """Handle 500 errors."""
    return flask.jsonify(ERROR_RESPONSES['processing_error']), 500

if __name__ == '__main__':
    print("\033[92m[+] Server\033[0m | Starting OFSF server on http://0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080, debug=True)

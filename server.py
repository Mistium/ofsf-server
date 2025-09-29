import ofsf, flask, flask_cors

app = flask.Flask(__name__)

cors = flask_cors.CORS(app)

@app.route('/files/<name>', methods=['GET'])
def get_user_file_system(name):
    try:
        if ofsf.exists_user_file_system(name):
            return flask.send_from_directory('./files', f"{name}.ofsf")
        else:
            return flask.jsonify({"payload": "No files found"})
    except Exception as e:
        print(f"\033[91m[-] OFSF Error\033[0m | Error in get_user_file_system: {e}")
        return flask.jsonify({"payload": "Error processing request"})
    
@app.route('/files/<name>', methods=['POST'])
def update_user_file_system(name):
    try:
        data = flask.request.get_json()
        if data:
            updates = data.get("updates", "")
            
            if name and updates:
                result = ofsf.handleOFSFupdate(name, updates)
                return flask.jsonify(result)
            else:
                return flask.jsonify({"payload": "Invalid request"})
        else:
            return flask.jsonify({"payload": "Invalid request"})
    except Exception as e:
        print(f"\033[91m[-] OFSF Error\033[0m | Error in update_user_file_system: {e}")
        return flask.jsonify({"payload": "Error processing request"})
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
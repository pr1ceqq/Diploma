from flask import Flask, request, jsonify
from db import init_db
from recognition import recognize_plate
from db import add_plate, delete_plate, list_plates, get_log, log_barrier_status, get_barrier_log

app = Flask(__name__)

# Initialize the database
init_db()

barrier_status = {'state': 'lowered'}

@app.route('/recognize', methods=['POST'])
def recognize():
    return recognize_plate(request)

@app.route('/add_plate', methods=['POST'])
def add():
    return add_plate(request)

@app.route('/delete_plate', methods=['POST'])
def delete():
    return delete_plate(request)

@app.route('/list_plates', methods=['GET'])
def list_allowed():
    return list_plates()

@app.route('/log', methods=['GET'])
def log():
    return get_log()

@app.route('/barrier_status', methods=['GET'])
def get_barrier_status():
    return jsonify({'status': barrier_status['state']})

@app.route('/set_barrier', methods=['POST'])
def set_barrier():
    data = request.get_json()
    state = data.get('state')
    if state not in ['raised', 'lowered']:
        return jsonify({'error': 'Invalid state'}), 400
    barrier_status['state'] = state
    log_barrier_status(state)
    return jsonify({'status': barrier_status['state']})

@app.route('/barrier_log', methods=['GET'])
def barrier_log():
    return get_barrier_log()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 
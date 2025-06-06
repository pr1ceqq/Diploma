import sqlite3
from flask import jsonify

def init_db():
    with sqlite3.connect("allowed_plates.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS allowed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT UNIQUE
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS access_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT,
            status TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS barrier_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()

def log_access(plate, status):
    with sqlite3.connect("allowed_plates.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO access_log (plate, status) VALUES (?, ?)", (plate, status))
        conn.commit()

def log_barrier_status(status):
    with sqlite3.connect("allowed_plates.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO barrier_log (status) VALUES (?)", (status,))
        conn.commit()

def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def is_fuzzy_match(plate, allowed_plate, max_dist=1):
    return levenshtein(plate, allowed_plate) <= max_dist

def is_plate_allowed(plate):
    plate = plate.replace(" ", "").upper()
    with sqlite3.connect("allowed_plates.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT plate FROM allowed")
        allowed = [row[0] for row in cursor.fetchall()]
        for allowed_plate in allowed:
            if plate == allowed_plate or is_fuzzy_match(plate, allowed_plate):
                return True, allowed_plate
    return False, plate

def add_plate(request):
    data = request.get_json()
    plate = data.get("plate", "").replace(" ", "").upper()
    if not plate:
        return jsonify({'error': 'plate is required'}), 400
    try:
        with sqlite3.connect("allowed_plates.db") as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO allowed (plate) VALUES (?)", (plate,))
            conn.commit()
        return jsonify({'status': 'added', 'plate': plate})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def delete_plate(request):
    data = request.get_json()
    plate = data.get("plate", "").replace(" ", "").upper()
    if not plate:
        return jsonify({'error': 'plate is required'}), 400
    with sqlite3.connect("allowed_plates.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM allowed WHERE plate = ?", (plate,))
        conn.commit()
    return jsonify({'status': 'deleted', 'plate': plate})

def list_plates():
    with sqlite3.connect("allowed_plates.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT plate FROM allowed")
        plates = [row[0] for row in cursor.fetchall()]
    return jsonify({'plates': plates})

def get_log():
    with sqlite3.connect("allowed_plates.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT plate, status, timestamp FROM access_log ORDER BY timestamp DESC LIMIT 100")
        rows = cursor.fetchall()
    return jsonify({'log': rows})

def get_barrier_log():
    with sqlite3.connect("allowed_plates.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, timestamp FROM barrier_log ORDER BY timestamp DESC LIMIT 100")
        rows = cursor.fetchall()
    return jsonify({'log': rows}) 
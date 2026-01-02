#!/usr/bin/env python3
"""
CheckUser Flask Server - Compatible con formato Android
"""
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from pathlib import Path

app = Flask(__name__)

CONFIG_DIR = Path.home() / '.moratech'
USERS_FILE = CONFIG_DIR / 'users.json'
LOG_FILE = CONFIG_DIR / 'checkuser.log'

def log_request(user, result):
    """Registrar petición"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] User: {user} -> Result: {result}\n")

@app.route('/')
def home():
    return "CheckUser MoraTech funcionando!", 200

@app.route('/checkUser', methods=['GET'])
def check_user_info():
    return "CheckUser MoraTech - Use POST method with JSON: {'user': 'username'}", 200

@app.route('/checkUser', methods=['POST'])
def check_user():
    try:
        # Leer datos del request
        data = request.get_json()
        username = data.get('user', '').strip()
        
        print(f"[CheckUser] Consultando: {username}")
        log_request(username, "Query")
        
        if not username:
            log_request(username, "Not exist - Empty user")
            return jsonify("Not exist"), 200
        
        # Leer usuarios
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        
        if username not in users:
            log_request(username, "Not exist")
            return jsonify("Not exist"), 200
        
        user_data = users[username]
        expires = user_data.get('expires')
        
        if not expires:
            # Usuario sin expiración
            log_request(username, "No expiry")
            return jsonify("Not exist"), 200
        
        # Parsear fecha de expiración
        expire_date = datetime.fromisoformat(expires)
        
        # ⚠️ IMPORTANTE: Sumar 1 día para compatibilidad con Android
        # El sistema Android resta 1 día, así que enviamos +1
        expire_date_adjusted = expire_date + timedelta(days=1)
        
        # Formato: ddmmyyyy (sin separadores)
        result = expire_date_adjusted.strftime('%d%m%Y')
        
        print(f"[CheckUser] Usuario {username} -> {result}")
        log_request(username, result)
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[CheckUser] Error: {e}")
        log_request("ERROR", str(e))
        return jsonify("Not exist"), 500

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
    app.run(host='0.0.0.0', port=port, debug=False)
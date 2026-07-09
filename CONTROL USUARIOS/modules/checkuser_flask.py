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
    return "CheckUser MoraTech funcionando!", 200

@app.route('/checkUser', methods=['POST'])
def check_user():
    try:
        # Leer datos del request
        data = request.get_json()
        username = data.get('user', '').strip()
        
        print(f"[CheckUser] Consultando: {username}")
        log_request(username, "Consulta recibida")
        
        if not username:
            log_request(username, "Sin usuario")
            return "Not exist", 200  # ← SIN jsonify
        
        # Leer usuarios
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        
        if username not in users:
            log_request(username, "No existe en lista")
            return "Not exist", 200  # ← SIN jsonify
        
        user_data = users[username]
        expires_str = user_data.get('expires', 'N/A')
        
        # Calcular días restantes
        if expires_str != 'N/A':
            try:
                expires = datetime.fromisoformat(expires_str)
                now = datetime.now()
                
                # Manejar timezone-aware vs naive
                if expires.tzinfo is not None:
                    now = now.replace(tzinfo=expires.tzinfo)
                
                remaining = (expires - now).days
                
                if remaining < 0:
                    log_request(username, f"Expirado (expiró hace {abs(remaining)} días)")
                    return "Not exist", 200  # ← SIN jsonify
                    
                log_request(username, f"Válido - {remaining} días restantes")
                return f"{remaining}|{expires_str}", 200  # ← SIN jsonify
            except:
                pass
        
        log_request(username, "Válido (sin fecha expiración)")
        return "Ilimitado", 200  # ← SIN jsonify
        
    except Exception as e:
        log_request(username, f"Error: {str(e)}")
        return "Not exist", 200

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
    app.run(host='0.0.0.0', port=port, debug=False)

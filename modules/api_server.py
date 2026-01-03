#!/usr/bin/env python3
"""
API REST Server - Gestión de usuarios sin Telegram
Llama a funciones de users.py para evitar duplicación
"""
import json
import sys
import os
from datetime import datetime
from flask import Flask, request, jsonify
from pathlib import Path
from functools import wraps

# Agregar path de módulos
sys.path.insert(0, '/usr/local/lib/moratech/modules')

# Importar funciones de users
from users import (
    load_users, 
    save_users, 
    load_token_config, 
    save_token_config
)

app = Flask(__name__)

# Clave secreta fija
SECRET_KEY = "moratech-key"

CONFIG_DIR = Path.home() / '.moratech'
API_LOG_FILE = CONFIG_DIR / 'api.log'

def log_api_request(endpoint, data, result):
    """Registrar petición API"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = {
        'timestamp': timestamp,
        'endpoint': endpoint,
        'data': data,
        'result': result,
        'auth': 'valid' if request.headers.get('X-Auth-Key') == SECRET_KEY else 'invalid'
    }
    
    with open(API_LOG_FILE, 'a') as f:
        f.write(json.dumps(log_entry) + "\n")

def require_auth(f):
    """Decorator para validar clave secreta"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_key = request.headers.get('X-Auth-Key')
        
        if not auth_key:
            log_api_request(request.path, {}, "Missing Auth Key")
            return jsonify({'error': 'Auth Key required'}), 401
        
        if auth_key != SECRET_KEY:
            log_api_request(request.path, {}, "Invalid Auth Key")
            return jsonify({'error': 'Invalid Auth Key'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

# ==================== ENDPOINTS ====================

@app.route('/')
def home():
    return "MORATECH API - Sistema de gestión de usuarios", 200

@app.route('/api/status', methods=['GET'])
@require_auth
def api_status():
    """Estado del sistema"""
    users = load_users()
    
    result = {
        'status': 'online',
        'total_users': len(users),
        'timestamp': datetime.now().isoformat()
    }
    
    log_api_request('/api/status', {}, 'OK')
    return jsonify(result), 200

@app.route('/api/agregar', methods=['POST'])
@require_auth
def api_agregar_ssh():
    """Agregar usuario SSH - Usa lógica de users.py"""
    try:
        from datetime import timedelta
        
        data = request.get_json()
        username = data.get('user')
        password = data.get('password')
        max_conn = data.get('limite', 1)
        days = data.get('dias', 0)
        
        if not username or not password:
            log_api_request('/api/agregar', data, 'Missing parameters')
            return jsonify({'error': 'user y password requeridos'}), 400
        
        users = load_users()
        
        if username in users:
            log_api_request('/api/agregar', data, 'User exists')
            return jsonify({'error': 'Usuario ya existe'}), 400
        
        # Calcular expiración a las 6pm (igual que add_ssh_user)
        if days >= 0:
            expire_date = (datetime.now().date() + timedelta(days=days))
            expires = datetime.combine(expire_date, datetime.min.time()).replace(
                hour=18, minute=0, second=0
            ).isoformat()
        else:
            expires = None
        
        users[username] = {
            "password": password,
            "role": "user",
            "type": "ssh",
            "created": datetime.now().isoformat(),
            "expires": expires,
            "max_connections": int(max_conn),
            "enabled": True
        }
        
        new_user = {username: users[username]}
        if save_users(new_user, full_database=users):
            result = {
                'success': True,
                'user': username,
                'dias': days,
                'expira': expires
            }
            log_api_request('/api/agregar', data, 'OK')
            return jsonify(result), 200
        else:
            log_api_request('/api/agregar', data, 'Save failed')
            return jsonify({'error': 'Error guardando usuario'}), 500
        
    except Exception as e:
        log_api_request('/api/agregar', data, f'Error: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/token', methods=['POST'])
@require_auth
def api_agregar_token():
    """Agregar usuario TOKEN - Usa lógica de users.py"""
    try:
        from datetime import timedelta
        
        data = request.get_json()
        nombre = data.get('nombre')
        token = data.get('token')
        days = data.get('dias', 0)
        
        if not nombre or not token:
            log_api_request('/api/token', data, 'Missing parameters')
            return jsonify({'error': 'nombre y token requeridos'}), 400
        
        users = load_users()
        token_config = load_token_config()
        
        if token in users:
            log_api_request('/api/token', data, 'Token exists')
            return jsonify({'error': 'Token ya existe'}), 400
        
        if not token_config.get('token_password'):
            log_api_request('/api/token', data, 'No master password')
            return jsonify({'error': 'No hay contraseña maestra configurada'}), 400
        
        # Calcular expiración a las 6pm (igual que add_token_user)
        if days >= 0:
            expire_date = (datetime.now().date() + timedelta(days=days))
            expires = datetime.combine(expire_date, datetime.min.time()).replace(
                hour=18, minute=0, second=0
            ).isoformat()
        else:
            expires = None
        
        users[token] = {
            "password": token_config['token_password'],
            "role": "user",
            "type": "token",
            "display_name": nombre,
            "created": datetime.now().isoformat(),
            "expires": expires,
            "max_connections": 1,
            "enabled": True,
            "original_token": token
        }
        
        new_token = {token: users[token]}
        if save_users(new_token, full_database=users):
            result = {
                'success': True,
                'nombre': nombre,
                'token': token,
                'dias': days,
                'expira': expires
            }
            log_api_request('/api/token', data, 'OK')
            return jsonify(result), 200
        else:
            log_api_request('/api/token', data, 'Save failed')
            return jsonify({'error': 'Error guardando usuario'}), 500
        
    except Exception as e:
        log_api_request('/api/token', data, f'Error: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/renovar', methods=['POST'])
@require_auth
def api_renovar():
    """Renovar usuario - Usa lógica de edit_user opción 1"""
    try:
        from datetime import timedelta
        
        data = request.get_json()
        username = data.get('user')
        days = data.get('dias', 0)
        
        if not username:
            log_api_request('/api/renovar', data, 'Missing user')
            return jsonify({'error': 'user requerido'}), 400
        
        users = load_users()
        
        if username not in users:
            log_api_request('/api/renovar', data, 'User not found')
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        user_data = users[username]
        
        # Lógica igual que edit_user opción 1
        if user_data.get('expires'):
            current_expire = datetime.fromisoformat(user_data['expires'])
            if datetime.now() > current_expire:
                expire_date = (datetime.now().date() + timedelta(days=days))
                new_expire = datetime.combine(expire_date, datetime.min.time()).replace(
                    hour=18, minute=0, second=0
                )
            else:
                new_expire = current_expire + timedelta(days=days)
        else:
            expire_date = (datetime.now().date() + timedelta(days=days))
            new_expire = datetime.combine(expire_date, datetime.min.time()).replace(
                hour=18, minute=0, second=0
            )
        
        users[username]['expires'] = new_expire.isoformat()
        
        updated_user = {username: users[username]}
        if save_users(updated_user, full_database=users):
            new_days = (new_expire - datetime.now()).days
            result = {
                'success': True,
                'user': username,
                'dias_sumados': days,
                'dias_totales': new_days,
                'expira': new_expire.isoformat()
            }
            log_api_request('/api/renovar', data, 'OK')
            return jsonify(result), 200
        else:
            log_api_request('/api/renovar', data, 'Save failed')
            return jsonify({'error': 'Error guardando cambios'}), 500
        
    except Exception as e:
        log_api_request('/api/renovar', data, f'Error: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/reiniciar', methods=['POST'])
@require_auth
def api_reiniciar():
    """Reiniciar días - Usa lógica de edit_user opción 2"""
    try:
        from datetime import timedelta
        
        data = request.get_json()
        username = data.get('user')
        days = data.get('dias', 0)
        
        if not username:
            log_api_request('/api/reiniciar', data, 'Missing user')
            return jsonify({'error': 'user requerido'}), 400
        
        users = load_users()
        
        if username not in users:
            log_api_request('/api/reiniciar', data, 'User not found')
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        # Lógica igual que edit_user opción 2
        if days >= 0:
            expire_date = (datetime.now().date() + timedelta(days=days))
            new_expire = datetime.combine(expire_date, datetime.min.time()).replace(
                hour=18, minute=0, second=0
            )
            users[username]['expires'] = new_expire.isoformat()
        else:
            users[username]['expires'] = None
        
        updated_user = {username: users[username]}
        if save_users(updated_user, full_database=users):
            result = {
                'success': True,
                'user': username,
                'dias_nuevos': days,
                'expira': new_expire.isoformat() if days >= 0 else None
            }
            log_api_request('/api/reiniciar', data, 'OK')
            return jsonify(result), 200
        else:
            log_api_request('/api/reiniciar', data, 'Save failed')
            return jsonify({'error': 'Error guardando cambios'}), 500
        
    except Exception as e:
        log_api_request('/api/reiniciar', data, f'Error: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/borrar', methods=['POST'])
@require_auth
def api_borrar():
    """Eliminar usuario - Usa lógica de delete_specific_user"""
    try:
        import subprocess
        
        data = request.get_json()
        username = data.get('user')
        
        if not username:
            log_api_request('/api/borrar', data, 'Missing user')
            return jsonify({'error': 'user requerido'}), 400
        
        users = load_users()
        
        if username not in users:
            log_api_request('/api/borrar', data, 'User not found')
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        del users[username]
        # Aquí pasamos diccionario vacío porque ya lo eliminamos
        if save_users({}, full_database=users):
            # Desconectar usuario (igual que delete_specific_user)
            subprocess.run(['pkill', '-u', username], stderr=subprocess.DEVNULL)
            
            result = {
                'success': True,
                'user': username,
                'action': 'deleted',
                'disconnected': True
            }
            log_api_request('/api/borrar', data, 'OK')
            return jsonify(result), 200
        else:
            log_api_request('/api/borrar', data, 'Save failed')
            return jsonify({'error': 'Error guardando cambios'}), 500
        
    except Exception as e:
        log_api_request('/api/borrar', data, f'Error: {e}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    app.run(host='0.0.0.0', port=port, debug=False)
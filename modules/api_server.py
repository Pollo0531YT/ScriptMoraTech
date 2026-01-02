#!/usr/bin/env python3
"""
API REST Server - Gestión de usuarios sin Telegram
"""
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from pathlib import Path
from functools import wraps

app = Flask(__name__)

# Clave secreta fija
SECRET_KEY = "moratech-key"

CONFIG_DIR = Path.home() / '.moratech'
USERS_FILE = CONFIG_DIR / 'users.json'
API_LOG_FILE = CONFIG_DIR / 'api.log'
TOKEN_CONFIG_FILE = CONFIG_DIR / 'token_config.json'

def log_api_request(endpoint, data, result, api_key=""):
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


def load_users():
    """Cargar usuarios"""
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    """Guardar usuarios - Versión simplificada para API"""
    import tempfile
    import shutil
    import subprocess
    
    try:
        # Sincronizar con sistema
        result = subprocess.run(['cut', '-d:', '-f1', '/etc/passwd'], 
                              capture_output=True, text=True)
        system_users = result.stdout.strip().split('\n')
        
        for username, data in users.items():
            if username not in system_users:
                subprocess.run(['useradd', '-M', '-s', '/bin/false', username], 
                             capture_output=True, text=True)
            
            password = str(data.get('password', ''))
            subprocess.run(['chpasswd'], 
                         input=f"{username}:{password}\n".encode('utf-8'),
                         capture_output=True)
        
        moratech_users = list(users.keys())
        for sys_user in system_users:
            if sys_user.startswith('token_') or sys_user in moratech_users:
                if sys_user not in moratech_users:
                    subprocess.run(['userdel', '-f', sys_user], 
                                 capture_output=True, text=True)
        
        # Guardar JSON
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, dir=CONFIG_DIR)
        json.dump(users, temp_file, indent=4)
        temp_file.close()
        shutil.move(temp_file.name, USERS_FILE)
        
        return True
    except Exception as e:
        print(f"Error save_users: {e}")
        return False

def load_token_config():
    """Cargar config de tokens"""
    if not TOKEN_CONFIG_FILE.exists():
        return {}
    with open(TOKEN_CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_token_config(config):
    """Guardar config de tokens"""
    with open(TOKEN_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def require_auth(f):
    """Decorator para validar clave secreta"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_key = request.headers.get('X-Auth-Key')
        
        if not auth_key:
            log_api_request(request.path, {}, "Missing Auth Key", "")
            return jsonify({'error': 'Auth Key required'}), 401
        
        if auth_key != SECRET_KEY:
            log_api_request(request.path, {}, "Invalid Auth Key", auth_key)
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
    
    log_api_request('/api/status', {}, 'OK', request.headers.get('X-API-Key'))
    return jsonify(result), 200

@app.route('/api/agregar', methods=['POST'])
@require_auth  
def api_agregar_ssh():
    """Agregar usuario SSH"""
    try:
        data = request.get_json()
        username = data.get('user')
        password = data.get('password')
        max_conn = data.get('limite', 1)
        days = data.get('dias', 0)
        
        if not username or not password:
            log_api_request('/api/agregar', data, 'Missing parameters', request.headers.get('X-API-Key'))
            return jsonify({'error': 'user y password requeridos'}), 400
        
        users = load_users()
        
        if username in users:
            log_api_request('/api/agregar', data, 'User exists', request.headers.get('X-API-Key'))
            return jsonify({'error': 'Usuario ya existe'}), 400
        
        # Calcular expiración a las 6pm
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
        
        if save_users(users):
            result = {
                'success': True,
                'user': username,
                'dias': days,
                'expira': expires
            }
            log_api_request('/api/agregar', data, 'OK', request.headers.get('X-API-Key'))
            return jsonify(result), 200
        else:
            log_api_request('/api/agregar', data, 'Save failed', request.headers.get('X-API-Key'))
            return jsonify({'error': 'Error guardando usuario'}), 500
        
    except Exception as e:
        log_api_request('/api/agregar', data, f'Error: {e}', request.headers.get('X-API-Key'))
        return jsonify({'error': str(e)}), 500

@app.route('/api/token', methods=['POST'])
@require_auth  
def api_agregar_token():
    """Agregar usuario TOKEN"""
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        token = data.get('token')
        days = data.get('dias', 0)
        
        if not nombre or not token:
            log_api_request('/api/token', data, 'Missing parameters', request.headers.get('X-API-Key'))
            return jsonify({'error': 'nombre y token requeridos'}), 400
        
        users = load_users()
        token_config = load_token_config()
        
        if token in users:
            log_api_request('/api/token', data, 'Token exists', request.headers.get('X-API-Key'))
            return jsonify({'error': 'Token ya existe'}), 400
        
        # Verificar contraseña maestra
        if not token_config.get('token_password'):
            log_api_request('/api/token', data, 'No master password', request.headers.get('X-API-Key'))
            return jsonify({'error': 'No hay contraseña maestra configurada'}), 400
        
        # Calcular expiración a las 6pm
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
        
        if save_users(users):
            result = {
                'success': True,
                'nombre': nombre,
                'token': token,
                'dias': days,
                'expira': expires
            }
            log_api_request('/api/token', data, 'OK', request.headers.get('X-API-Key'))
            return jsonify(result), 200
        else:
            log_api_request('/api/token', data, 'Save failed', request.headers.get('X-API-Key'))
            return jsonify({'error': 'Error guardando usuario'}), 500
        
    except Exception as e:
        log_api_request('/api/token', data, f'Error: {e}', request.headers.get('X-API-Key'))
        return jsonify({'error': str(e)}), 500

@app.route('/api/renovar', methods=['POST'])
@require_auth  
def api_renovar():
    """Renovar usuario (sumar días)"""
    try:
        data = request.get_json()
        username = data.get('user')
        days = data.get('dias', 0)
        
        if not username:
            log_api_request('/api/renovar', data, 'Missing user', request.headers.get('X-API-Key'))
            return jsonify({'error': 'user requerido'}), 400
        
        users = load_users()
        
        if username not in users:
            log_api_request('/api/renovar', data, 'User not found', request.headers.get('X-API-Key'))
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        user_data = users[username]
        
        if user_data.get('expires'):
            current_expire = datetime.fromisoformat(user_data['expires'])
            if datetime.now() > current_expire:
                # Expirado: sumar desde hoy a las 6pm
                expire_date = (datetime.now().date() + timedelta(days=days))
                new_expire = datetime.combine(expire_date, datetime.min.time()).replace(
                    hour=18, minute=0, second=0
                )
            else:
                # No expirado: sumar días manteniendo hora
                new_expire = current_expire + timedelta(days=days)
        else:
            # Sin expiración: crear desde hoy a las 6pm
            expire_date = (datetime.now().date() + timedelta(days=days))
            new_expire = datetime.combine(expire_date, datetime.min.time()).replace(
                hour=18, minute=0, second=0
            )
        
        users[username]['expires'] = new_expire.isoformat()
        
        if save_users(users):
            new_days = (new_expire - datetime.now()).days
            result = {
                'success': True,
                'user': username,
                'dias_sumados': days,
                'dias_totales': new_days,
                'expira': new_expire.isoformat()
            }
            log_api_request('/api/renovar', data, 'OK', request.headers.get('X-API-Key'))
            return jsonify(result), 200
        else:
            log_api_request('/api/renovar', data, 'Save failed', request.headers.get('X-API-Key'))
            return jsonify({'error': 'Error guardando cambios'}), 500
        
    except Exception as e:
        log_api_request('/api/renovar', data, f'Error: {e}', request.headers.get('X-API-Key'))
        return jsonify({'error': str(e)}), 500

@app.route('/api/reiniciar', methods=['POST'])
@require_auth  
def api_reiniciar():
    """Reiniciar días de usuario"""
    try:
        data = request.get_json()
        username = data.get('user')
        days = data.get('dias', 0)
        
        if not username:
            log_api_request('/api/reiniciar', data, 'Missing user', request.headers.get('X-API-Key'))
            return jsonify({'error': 'user requerido'}), 400
        
        users = load_users()
        
        if username not in users:
            log_api_request('/api/reiniciar', data, 'User not found', request.headers.get('X-API-Key'))
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        # Reiniciar a días exactos desde hoy a las 6pm
        if days >= 0:
            expire_date = (datetime.now().date() + timedelta(days=days))
            new_expire = datetime.combine(expire_date, datetime.min.time()).replace(
                hour=18, minute=0, second=0
            )
            users[username]['expires'] = new_expire.isoformat()
        else:
            users[username]['expires'] = None
        
        if save_users(users):
            result = {
                'success': True,
                'user': username,
                'dias_nuevos': days,
                'expira': new_expire.isoformat() if days >= 0 else None
            }
            log_api_request('/api/reiniciar', data, 'OK', request.headers.get('X-API-Key'))
            return jsonify(result), 200
        else:
            log_api_request('/api/reiniciar', data, 'Save failed', request.headers.get('X-API-Key'))
            return jsonify({'error': 'Error guardando cambios'}), 500
        
    except Exception as e:
        log_api_request('/api/reiniciar', data, f'Error: {e}', request.headers.get('X-API-Key'))
        return jsonify({'error': str(e)}), 500

@app.route('/api/borrar', methods=['POST'])
@require_auth  
def api_borrar():
    """Eliminar usuario"""
    try:
        data = request.get_json()
        username = data.get('user')
        
        if not username:
            log_api_request('/api/borrar', data, 'Missing user', request.headers.get('X-API-Key'))
            return jsonify({'error': 'user requerido'}), 400
        
        users = load_users()
        
        if username not in users:
            log_api_request('/api/borrar', data, 'User not found', request.headers.get('X-API-Key'))
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        del users[username]
        
        if save_users(users):
            result = {
                'success': True,
                'user': username,
                'action': 'deleted'
            }
            log_api_request('/api/borrar', data, 'OK', request.headers.get('X-API-Key'))
            return jsonify(result), 200
        else:
            log_api_request('/api/borrar', data, 'Save failed', request.headers.get('X-API-Key'))
            return jsonify({'error': 'Error guardando cambios'}), 500
        
    except Exception as e:
        log_api_request('/api/borrar', data, f'Error: {e}', request.headers.get('X-API-Key'))
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    app.run(host='0.0.0.0', port=port, debug=False)
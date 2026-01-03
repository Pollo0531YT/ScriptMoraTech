#!/usr/bin/env python3
"""
API REST Server - Gestión de usuarios sin Telegram
Llama a funciones de users.py para evitar duplicación
"""
import json
import sys
import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, redirect
from pathlib import Path
from functools import wraps

from activaciones import registrar_activacion, obtener_activaciones, obtener_estadisticas
from users import ejecutar_borrado_fisico, ejecutar_creacion_usuario, ejecutar_reinicio_dias, ejecutar_renovacion_dias

# Agregar path de módulos
sys.path.insert(0, '/usr/local/lib/moratech')

template_dir = os.path.join(os.path.dirname(__file__), 'templates')

# Importar funciones de users
from users import (
    load_users, 
    save_users, 
    load_token_config, 
)

app = Flask(__name__, template_folder=template_dir)

app.secret_key = 'moratech-key'
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

#MEJORADO
@app.route('/api/agregar', methods=['POST'])
@require_auth
def api_agregar_ssh():
    """Agregar usuario SSH - Usa lógica centralizada con registro de activaciones"""
    try:
        data = request.get_json()
        username = data.get('user')
        password = data.get('password')
        days = data.get('dias', 0)
        max_conn = data.get('limite', 1)
        referencia = data.get('referencia', '')
        origen = data.get('origen', 'api')

        if not username or not password:
            log_api_request('/api/agregar', data, 'Missing parameters')
            registrar_activacion('agregar_ssh', username, username, days, referencia, origen, False, 'Faltan datos')
            return jsonify({'error': 'user y password requeridos'}), 400

        # LLAMADA A LA FUNCIÓN MAESTRA (Creación técnica en Linux y JSON)
        success, msg, expires = ejecutar_creacion_usuario(
            username, 
            password, 
            days, 
            user_type="ssh", 
            max_conn=max_conn
        )
        
        if success:
            # ✅ REGISTRO DE ACTIVACIÓN EXITOSA
            registrar_activacion('agregar_ssh', username, username, days, referencia, origen, True)
            
            result = {
                'success': True, 
                'user': username, 
                'dias': days,
                'expira': expires
            }
            log_api_request('/api/agregar', data, 'OK')
            return jsonify(result), 200
        else:
            # ✅ REGISTRO DE FALLO (ej: usuario ya existe)
            registrar_activacion('agregar_ssh', username, username, days, referencia, origen, False, msg)
            log_api_request('/api/agregar', data, f'Failed: {msg}')
            return jsonify({'error': msg}), 400

    except Exception as e:
        log_api_request('/api/agregar', data, f'Error: {e}')
        return jsonify({'error': str(e)}), 500

#MEJORADO
@app.route('/api/token', methods=['POST'])
@require_auth
def api_agregar_token():
    """Agregar usuario TOKEN - Usa lógica centralizada pero mantiene sus logs"""
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        token = data.get('token')
        days = data.get('dias', 0)
        referencia = data.get('referencia', '')  
        origen = data.get('origen', 'api') # Marcamos que viene de la API
        
        if not nombre or not token:
            log_api_request('/api/token', data, 'Missing parameters')
            registrar_activacion('agregar_token', token, nombre, days, referencia, origen, False, 'Parámetros faltantes')
            return jsonify({'error': 'nombre y token requeridos'}), 400
        
        token_config = load_token_config()
        if not token_config.get('token_password'):
            log_api_request('/api/token', data, 'No master password')
            registrar_activacion('agregar_token', token, nombre, days, referencia, origen, False, 'Sin contraseña maestra')
            return jsonify({'error': 'No hay contraseña maestra configurada'}), 400

        # LLAMADA A LA FUNCIÓN MAESTRA (Solo para la creación técnica)
        # Pasamos display_name para que guarde el nombre visual en el JSON
        success, msg, expires = ejecutar_creacion_usuario(
            token, 
            token_config['token_password'], 
            days, 
            user_type="token", 
            display_name=nombre
        )
        
        if success:
            # ✅ TU REGISTRO DE ACTIVACIÓN (Tal cual lo tenías)
            registrar_activacion('agregar_token', token, nombre, days, referencia, origen, True)
            
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
            # ✅ REGISTRO DE FALLO SI LA FUNCIÓN MAESTRA DIJO QUE NO
            registrar_activacion('agregar_token', token, nombre, days, referencia, origen, False, msg)
            log_api_request('/api/token', data, f'Failed: {msg}')
            return jsonify({'error': msg}), 500
        
    except Exception as e:
        # ✅ REGISTRO DE ERROR CRÍTICO
        registrar_activacion('agregar_token', token if 'token' in locals() else 'unknown', 
                           nombre if 'nombre' in locals() else 'unknown', 
                           days if 'days' in locals() else 0, 
                           referencia if 'referencia' in locals() else '', 
                           origen if 'origen' in locals() else 'api', 
                           False, str(e))
        log_api_request('/api/token', data, f'Error: {e}')
        return jsonify({'error': str(e)}), 500
    
# MEJORADO
@app.route('/api/renovar', methods=['POST'])
@require_auth
def api_renovar():
    """Renovar usuario - Registra la activación y usa lógica centralizada"""
    try:
        data = request.get_json()
        username = data.get('user')
        days = data.get('dias', 0)
        referencia = data.get('referencia', '')
        origen = data.get('origen', 'api') 

        if not username:
            log_api_request('/api/renovar', data, 'Missing user')
            # Registramos el fallo por falta de usuario
            registrar_activacion('renovar', 'unknown', 'unknown', days, referencia, origen, False, 'Usuario no especificado')
            return jsonify({'error': 'user requerido'}), 400

        # LLAMADA A LA LÓGICA ÚNICA (users.py)
        success, message, new_date = ejecutar_renovacion_dias(username, days, referencia, origen)

        if success:
            # ✅ REGISTRO DE ACTIVACIÓN EXITOSA (Fundamental para tus ventas)
            registrar_activacion('renovar', username, username, days, referencia, origen, True)
            
            total_days = (new_date - datetime.now()).days
            result = {
                'success': True,
                'user': username,
                'dias_sumados': days,
                'dias_totales': total_days,
                'expira': new_date.isoformat()
            }
            log_api_request('/api/renovar', data, 'OK')
            return jsonify(result), 200
        else:
            # ✅ REGISTRO DE FALLO (ej: usuario no existe)
            registrar_activacion('renovar', username, username, days, referencia, origen, False, message)
            log_api_request('/api/renovar', data, f'Failed: {message}')
            return jsonify({'error': message}), 404

    except Exception as e:
        # ✅ REGISTRO DE ERROR CRÍTICO DEL SISTEMA
        registrar_activacion('renovar', 
                           username if 'username' in locals() else 'unknown', 
                           username if 'username' in locals() else 'unknown', 
                           days if 'days' in locals() else 0, 
                           referencia if 'referencia' in locals() else '', 
                           origen if 'origen' in locals() else 'api', 
                           False, str(e))
        log_api_request('/api/renovar', data, f'Error: {e}')
        return jsonify({'error': str(e)}), 500
    
# MEJORADO
@app.route('/api/reiniciar', methods=['POST'])
@require_auth
def api_reiniciar():
    """Reiniciar días de un usuario y registrar la operación"""
    try:
        data = request.get_json()
        username = data.get('user')
        days = data.get('dias', 0)
        referencia = data.get('referencia', 'RESET')
        origen = data.get('origen', 'api')
        
        if not username:
            registrar_activacion('reiniciar', 'unknown', 'unknown', days, referencia, origen, False, 'Usuario requerido')
            return jsonify({'error': 'user requerido'}), 400
        
        # LLAMADA A LA FUNCIÓN MAESTRA
        success, message, new_date = ejecutar_reinicio_dias(username, days)
        
        if success:
            # ✅ AHORA SÍ SE REGISTRA
            registrar_activacion('reiniciar', username, username, days, referencia, origen, True)
            
            result = {
                'success': True,
                'user': username,
                'dias_nuevos': days,
                'expira': new_date.isoformat() if new_date else None
            }
            log_api_request('/api/reiniciar', data, 'OK')
            return jsonify(result), 200
        else:
            registrar_activacion('reiniciar', username, username, days, referencia, origen, False, message)
            return jsonify({'error': message}), 404
            
    except Exception as e:
        log_api_request('/api/reiniciar', data, f'Error: {e}')
        return jsonify({'error': str(e)}), 500
    
# MEJORADO
@app.route('/api/borrar', methods=['POST'])
@require_auth
def api_borrar():
    """Eliminar usuario y registrar quién realizó la purga"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se enviaron datos'}), 400
        
        username = data.get('user')
        origen = data.get('origen', 'api')
        
        if not username:
            return jsonify({'error': 'user requerido'}), 400
        
        # LLAMADA A LA FUNCIÓN ÚNICA
        success, message = ejecutar_borrado_fisico(username)

        if success:
            # ✅ REGISTRO DE BORRADO
            registrar_activacion('borrar', username, username, 0, 'SISTEMA', origen, True)
            log_api_request('/api/borrar', data, f'OK - {message}')
            return jsonify({
                'success': True,
                'user': username,
                'message': message
            }), 200
        else:
            # ❌ REGISTRO DE FALLO REAL
            registrar_activacion('borrar', username, username, 0, 'FALLO', origen, False, message)
            log_api_request('/api/borrar', data, f'ERROR - {message}')
            return jsonify({'error': message}), 404
           
    except Exception as e:
        log_api_request('/api/borrar', data, f'CRITICAL ERROR: {e}')
        return jsonify({'error': f"Error interno: {str(e)}"}), 500
    
#trae las activaciones
@app.route('/api/sync-activaciones', methods=['GET'])
@require_auth
def api_sync_activaciones():
    """Endpoint para sincronización - Devuelve TODAS las activaciones"""
    # Leer nombre de VPS desde archivo
    vps_name_file = CONFIG_DIR / 'vps_name.txt'
    
    if vps_name_file.exists():
        with open(vps_name_file, 'r') as f:
            vps_name = f.read().strip()
    else:
        # Si no tiene nombre, usar IP pública
        try:
            import subprocess
            ip_result = subprocess.run(['curl', '-s', '-4', 'ifconfig.me'], 
                                     capture_output=True, text=True, timeout=3)
            ip = ip_result.stdout.strip()
            vps_name = f'vps-{ip}' if ip else 'vps-sin-ip'
        except:
            vps_name = 'vps-desconocida'
    
    activaciones = obtener_activaciones(limite=300)
    
    return jsonify({
        'vps_nombre': vps_name,
        'total': len(activaciones),
        'activaciones': activaciones
    }), 200

# para web
@app.route('/dashboard')
def dashboard():
    """Dashboard web de activaciones"""
    # Verificar si está autenticado
    if not session.get('authenticated'):
        return redirect('/login')
    
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login para dashboard"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == SECRET_KEY:
            session['authenticated'] = True
            return redirect('/dashboard')
        else:
            return render_template('login.html', error='Contraseña incorrecta')
    
    return render_template('login.html')


@app.route('/api/activaciones', methods=['GET'])
@require_auth
def api_activaciones():
    """Obtener lista de activaciones con filtros"""
    origen = request.args.get('origen', '')
    usuario = request.args.get('usuario', '')
    referencia = request.args.get('referencia', '')
    
    activaciones = obtener_activaciones(
        limite=200,
        filtro_origen=origen if origen else None,
        filtro_usuario=usuario if usuario else None,
        filtro_referencia=referencia if referencia else None
    )
    
    return jsonify(activaciones), 200


@app.route('/api/estadisticas', methods=['GET'])
@require_auth
def api_estadisticas():
    """Obtener estadísticas de activaciones"""
    stats = obtener_estadisticas()
    return jsonify(stats), 200


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    app.run(host='0.0.0.0', port=port, debug=False)
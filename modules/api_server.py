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

from activaciones import registrar_activacion, obtener_activaciones, obtener_estadisticas

# Agregar path de módulos
sys.path.insert(0, '/usr/local/lib/moratech')

# Importar funciones de users
from users import (
    load_users, 
    save_users, 
    load_token_config, 
    save_token_config
)

app = Flask(__name__)

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
        referencia = data.get('referencia', '')  
        origen = data.get('origen', 'manual') 
        
        if not nombre or not token:
            log_api_request('/api/token', data, 'Missing parameters')
            registrar_activacion('agregar_token', token, nombre, days, referencia, origen, False, 'Parámetros faltantes')
            return jsonify({'error': 'nombre y token requeridos'}), 400
        
        users = load_users()
        token_config = load_token_config()
        
        if token in users:
            log_api_request('/api/token', data, 'Token exists')
            registrar_activacion('agregar_token', token, nombre, days, referencia, origen, False, 'Token ya existe')
            return jsonify({'error': 'Token ya existe'}), 400
        
        if not token_config.get('token_password'):
            log_api_request('/api/token', data, 'No master password')
            registrar_activacion('agregar_token', token, nombre, days, referencia, origen, False, 'Sin contraseña maestra')
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
        
        new_token = {token: users[token]}
        if save_users(new_token, full_database=users):
            # ✅ REGISTRAR ACTIVACIÓN EXITOSA
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
            registrar_activacion('agregar_token', token, nombre, days, referencia, origen, False, 'Error guardando usuario')
            log_api_request('/api/token', data, 'Save failed')
            return jsonify({'error': 'Error guardando usuario'}), 500
        
    except Exception as e:
        registrar_activacion('agregar_token', token if 'token' in locals() else 'unknown', 
                           nombre if 'nombre' in locals() else 'unknown', 
                           days if 'days' in locals() else 0, 
                           referencia if 'referencia' in locals() else '', 
                           origen if 'origen' in locals() else 'manual', 
                           False, str(e))
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
        referencia = data.get('referencia', '')
        origen = data.get('origen', 'manual')
        
        if not username:
            log_api_request('/api/renovar', data, 'Missing user')
            registrar_activacion('renovar', username, '', days, referencia, origen, False, 'Usuario no especificado')
            return jsonify({'error': 'user requerido'}), 400
        
        users = load_users()
        
        if username not in users:
            log_api_request('/api/renovar', data, 'User not found')
            registrar_activacion('renovar', username, '', days, referencia, origen, False, 'Usuario no encontrado')
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        user_data = users[username]
        nombre_display = user_data.get('display_name', username)
        
        # Lógica de renovación
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
            # ✅ REGISTRAR ACTIVACIÓN EXITOSA
            registrar_activacion('renovar', username, nombre_display, days, referencia, origen, True)
            
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
            registrar_activacion('renovar', username, nombre_display, days, referencia, origen, False, 'Error guardando cambios')
            log_api_request('/api/renovar', data, 'Save failed')
            return jsonify({'error': 'Error guardando cambios'}), 500
        
    except Exception as e:
        registrar_activacion('renovar', username if 'username' in locals() else 'unknown',
                           nombre_display if 'nombre_display' in locals() else '',
                           days if 'days' in locals() else 0,
                           referencia if 'referencia' in locals() else '',
                           origen if 'origen' in locals() else 'manual',
                           False, str(e))
        log_api_request('/api/renovar', data, f'Error: {e}')
        return jsonify({'error': str(e)}), 500
    
#estos no usara automatico
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

# para web
@app.route('/dashboard')
def dashboard():
    """Dashboard web de activaciones"""
    from flask import session, redirect

    # Verificar si está autenticado
    if not session.get('authenticated'):
        return redirect('/login')

    html = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MORATECH - Dashboard de Activaciones</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 { 
            color: #667eea; 
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .subtitle { 
            color: #666; 
            margin-bottom: 30px; 
            font-size: 1.1em;
        }
        
        /* Estadísticas */
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-number { font-size: 2.5em; font-weight: bold; }
        .stat-label { opacity: 0.9; margin-top: 5px; }
        
        /* Filtros */
        .filters {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .filter-group {
            flex: 1;
            min-width: 200px;
        }
        .filter-group label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: 500;
        }
        .filter-group input, .filter-group select {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        .filter-group input:focus, .filter-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        /* Tabla */
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
        }
        th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }
        td {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }
        tr:hover { background: #f5f5f5; }
        
        .badge {
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .badge-success { background: #10b981; color: white; }
        .badge-error { background: #ef4444; color: white; }
        .badge-whatsapp { background: #25D366; color: white; }
        .badge-deposito { background: #3b82f6; color: white; }
        .badge-web { background: #8b5cf6; color: white; }
        .badge-manual { background: #6b7280; color: white; }
        
        .no-data {
            text-align: center;
            padding: 40px;
            color: #999;
            font-size: 1.2em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 MORATECH Dashboard</h1>
        <p class="subtitle">Registro de Activaciones del Sistema</p>
        
        <div class="stats" id="stats"></div>
        
        <div class="filters">
            <div class="filter-group">
                <label>Origen</label>
                <select id="filterOrigen" onchange="filtrar()">
                    <option value="">Todos</option>
                    <option value="whatsapp">WhatsApp</option>
                    <option value="deposito">Depósito</option>
                    <option value="web">Web</option>
                    <option value="manual">Manual</option>
                </select>
            </div>
            <div class="filter-group">
                <label>Buscar Usuario/Token</label>
                <input type="text" id="filterUsuario" placeholder="Nombre o token..." onkeyup="filtrar()">
            </div>
            <div class="filter-group">
                <label>Referencia Bancaria</label>
                <input type="text" id="filterReferencia" placeholder="REF-..." onkeyup="filtrar()">
            </div>
        </div>
        
        <div id="tabla"></div>
    </div>
    
    <script>
        let activaciones = [];
        
        async function cargarDatos() {
            const params = new URLSearchParams({
                origen: document.getElementById('filterOrigen').value,
                usuario: document.getElementById('filterUsuario').value,
                referencia: document.getElementById('filterReferencia').value
            });
            
            const response = await fetch('/api/activaciones?' + params, {
                headers: { 'X-Auth-Key': 'moratech-key' }
            });
            activaciones = await response.json();
            
            // Cargar estadísticas
            const statsResponse = await fetch('/api/estadisticas', {
                headers: { 'X-Auth-Key': 'moratech-key' }
            });
            const stats = await statsResponse.json();
            
            mostrarEstadisticas(stats);
            mostrarTabla();
        }
        
        function mostrarEstadisticas(stats) {
            const html = `
                <div class="stat-card">
                    <div class="stat-number">${stats.total}</div>
                    <div class="stat-label">Total Activaciones</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.exitosas}</div>
                    <div class="stat-label">Exitosas</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.fallidas}</div>
                    <div class="stat-label">Fallidas</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.ultimas_24h}</div>
                    <div class="stat-label">Últimas 24h</div>
                </div>
            `;
            document.getElementById('stats').innerHTML = html;
        }
        
        function mostrarTabla() {
            if (activaciones.length === 0) {
                document.getElementById('tabla').innerHTML = '<div class="no-data">📭 No hay activaciones registradas</div>';
                return;
            }
            
            let html = '<table><thead><tr>';
            html += '<th>ID</th><th>Fecha/Hora</th><th>Operación</th><th>Usuario</th>';
            html += '<th>Nombre</th><th>Días</th><th>Referencia</th><th>Origen</th><th>Estado</th>';
            html += '</tr></thead><tbody>';
            
            activaciones.forEach(a => {
                const origenBadge = `badge-${a.origen}`;
                const estadoBadge = a.success ? 'badge-success' : 'badge-error';
                const estadoText = a.success ? '✓ Exitoso' : '✗ Fallido';
                
                html += `<tr>
                    <td>${a.id}</td>
                    <td>${a.timestamp}</td>
                    <td>${a.operacion}</td>
                    <td><code>${a.usuario}</code></td>
                    <td>${a.nombre}</td>
                    <td>${a.dias}</td>
                    <td>${a.referencia || '-'}</td>
                    <td><span class="badge ${origenBadge}">${a.origen}</span></td>
                    <td><span class="badge ${estadoBadge}">${estadoText}</span></td>
                </tr>`;
            });
            
            html += '</tbody></table>';
            document.getElementById('tabla').innerHTML = html;
        }
        
        function filtrar() {
            cargarDatos();
        }
        
        // Cargar datos iniciales
        cargarDatos();
        
        // Actualizar cada 30 segundos
        setInterval(cargarDatos, 30000);
    </script>
</body>
</html>
    '''
    return html


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

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login para dashboard"""
    from flask import session, redirect
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == SECRET_KEY:
            session['authenticated'] = True
            return redirect('/dashboard')
        else:
            return '''
            <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: red;">Contraseña incorrecta</h1>
                <a href="/login">Volver</a>
            </body>
            </html>
            '''
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>MORATECH Login</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .login-box {
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                text-align: center;
            }
            h1 { color: #667eea; margin-bottom: 30px; }
            input {
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
            }
            button {
                width: 100%;
                padding: 12px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 10px;
            }
            button:hover { opacity: 0.9; }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h1>🚀 MORATECH</h1>
            <form method="POST">
                <input type="password" name="password" placeholder="Contraseña" required autofocus>
                <button type="submit">Acceder al Dashboard</button>
            </form>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    app.run(host='0.0.0.0', port=port, debug=False)
#!/usr/bin/env python3
"""
API REST Server - Gestión de usuarios sin Telegram
Llama a funciones de users.py para evitar duplicación
"""
import json
import sys
import os
from datetime import datetime, timedelta, time, timezone
from flask import Flask, request, jsonify, render_template, session, redirect
from pathlib import Path
from functools import wraps

# Agregar path de módulos PRIMERO
sys.path.insert(0, '/usr/local/lib/moratech')

# Ahora sí importar
from modules.activaciones import registrar_activacion, obtener_activaciones, obtener_estadisticas
from modules.users import (
    ejecutar_borrado_fisico, 
    sincronizar_usuario,
    load_users,
    load_token_config
)

# 3. Configuración
CR_TZ = timezone(timedelta(hours=-6))
template_dir = os.path.join(os.path.dirname(__file__), 'templates')

app = Flask(__name__, template_folder=template_dir)
app.secret_key = 'moratech-key'
SECRET_KEY = "moratech-key"

CONFIG_DIR = Path.home() / '.moratech'
API_LOG_FILE = CONFIG_DIR / 'api.log'

def log_api_request(endpoint, data, result):
    """Registrar petición API con timestamp en CR_TZ."""
    timestamp = _now_iso_cr()
    log_entry = {
        'timestamp': timestamp,
        'endpoint': endpoint,
        'data': data,
        'result': result,
        'auth': 'valid' if request.headers.get('X-Auth-Key') == SECRET_KEY else 'invalid'
    }

    CONFIG_DIR.mkdir(exist_ok=True)
    with open(API_LOG_FILE, 'a') as f:
        f.write(json.dumps(log_entry) + "\n")

def _now_iso_cr():
    try:
        return datetime.now(CR_TZ).isoformat()
    except Exception:
        return datetime.now().isoformat()

def require_auth_hybrid(f):
    """Decorator para validar X-Auth-Key O sesión web"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        key = request.headers.get('X-Auth-Key')
        is_authenticated = session.get('authenticated')
        
        if not (key == SECRET_KEY or is_authenticated):
            log_api_request(request.path, {}, "Unauthorized")
            return jsonify({'error': 'No autorizado'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function
# ==================== ENDPOINTS ====================

@app.route('/')
def home():
    return "MORATECH API - Sistema de gestión de usuarios", 200

@app.route('/api/status', methods=['GET'])
@require_auth_hybrid
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
@require_auth_hybrid
def api_agregar_ssh():
    try:
        data = request.get_json()
        username = data.get('user')
        password = data.get('password')
        days = data.get('dias', 0)
        max_conn = data.get('limite', 1)
        referencia = data.get('referencia', '')
        origen = data.get('origen', 'api')
        
        if not username or not password:
            registrar_activacion('agregar_ssh', username, username, days, referencia, origen, False, 'Faltan datos')
            return jsonify({'error': 'user y password requeridos'}), 400
        
        success, msg, expires = sincronizar_usuario(
            username=username,
            password=password,
            dias=days,
            operacion='crear',
            user_type='ssh',
            max_conn=max_conn
        )
        
        if success:
            registrar_activacion('agregar_ssh', username, username, days, referencia, origen, True)
            return jsonify({
                'success': True,
                'user': username,
                'dias': days,
                'expira': expires.isoformat()
            }), 200
        else:
            registrar_activacion('agregar_ssh', username, username, days, referencia, origen, False, msg)
            return jsonify({'error': msg}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
#MEJORADO
@app.route('/api/token', methods=['POST'])
@require_auth_hybrid
def api_agregar_token():
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        token = data.get('token')
        days = data.get('dias', 0)
        referencia = data.get('referencia', '')
        origen = data.get('origen', 'api')
        
        if not nombre or not token:
            registrar_activacion('agregar_token', token, nombre, days, referencia, origen, False, 'Parámetros faltantes')
            return jsonify({'error': 'nombre y token requeridos'}), 400
        
        token_config = load_token_config()
        if not token_config.get('token_password'):
            registrar_activacion('agregar_token', token, nombre, days, referencia, origen, False, 'Sin contraseña maestra')
            return jsonify({'error': 'No hay contraseña maestra'}), 400
        
        success, msg, expires = sincronizar_usuario(
            username=token,
            password=token_config['token_password'],
            dias=days,
            operacion='crear',
            user_type='token',
            display_name=nombre
        )
        
        if success:
            registrar_activacion('agregar_token', token, nombre, days, referencia, origen, True)

            # Notificar a telegram
            enviar_notificacion_telegram('token_creado', {
                'nombre': nombre,
                'token': token,
                'dias': days + 1,  # Visual +1
                'expira': expires.strftime('%d/%m/%Y'),
                'origen': origen
            })

            return jsonify({
                'success': True,
                'nombre': nombre,
                'token': token,
                'dias': days,
                'expira': expires.isoformat()
            }), 200
        else:
            registrar_activacion('agregar_token', token, nombre, days, referencia, origen, False, msg)
            return jsonify({'error': msg}), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
       
# MEJORADO
@app.route('/api/renovar', methods=['POST'])
@require_auth_hybrid
def api_renovar():
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        token = data.get('token')
        dias = data.get('dias', 0)
        referencia = data.get('referencia', '')
        origen = data.get('origen', 'api')
        
        if not token:
            return jsonify({'error': 'token requerido'}), 400
        
        success, msg, new_date = sincronizar_usuario(
            username=token,
            dias=dias,
            operacion='renovar'
        )
        
        if success:
            now_cr = datetime.now(CR_TZ)
            diff = new_date - now_cr
            total_days = diff.days if diff.days >= 0 else 0
            
            registrar_activacion('renovar', token, nombre, dias, referencia, origen, True)

            # notificar a telegram
            enviar_notificacion_telegram('token_renovado', {
                'token': token,
                'dias_totales': total_days + 1,  # Visual +1
                'expira': new_date.strftime('%d/%m/%Y'),
                'origen': origen
            })
            
            return jsonify({
                'success': True,
                'user': token,
                'dias_sumados': dias,
                'dias_totales': total_days,
                'expira': new_date.isoformat()
            }), 200
        else:
            registrar_activacion('renovar', token, nombre, dias, referencia, origen, False, msg)
            return jsonify({'error': msg}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# MEJORADO
@app.route('/api/reiniciar', methods=['POST'])
@require_auth_hybrid
def api_reiniciar():
    try:
        data = request.get_json()
        username = data.get('user')
        days = data.get('dias', 0)
        
        if not username:
            return jsonify({'error': 'user requerido'}), 400
        
        success, msg, new_date = sincronizar_usuario(
            username=username,
            dias=days,
            operacion='reiniciar'
        )
        
        if success:
            registrar_activacion('reiniciar', username, username, days, 'RESET', 'api', True)
            return jsonify({
                'success': True,
                'user': username,
                'dias_nuevos': days,
                'expira': new_date.isoformat()
            }), 200
        else:
            return jsonify({'error': msg}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
         
# MEJORADO
@app.route('/api/borrar', methods=['POST'])
@require_auth_hybrid
def api_borrar():
    """Eliminar usuario vía API"""

    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No se enviaron datos'}), 400
        
        username = data.get('user')
        origen = data.get('origen', 'api')
        
        if not username:
            log_api_request('/api/borrar', data, 'Missing user')
            return jsonify({'error': 'user requerido'}), 400
        
        # LLAMAR A LA FUNCIÓN MAESTRA
        success, message = ejecutar_borrado_fisico(username)
        
        if success:
            # Registrar en activaciones
            registrar_activacion('borrar', username, username, 0, 'Borrar-user', origen, True)
            log_api_request('/api/borrar', data, f'OK - {message}')

             # notificar a telegram
            enviar_notificacion_telegram('usuario_borrado', {
                'usuario': username,
                'origen': origen
            })
            
            return jsonify({
                'success': True,
                'user': username,
                'message': message,
                'purged': True
            }), 200
        else:
            # Registrar fallo
            registrar_activacion('borrar', username, username, 0, 'Borrar-user', origen, False, message)
            log_api_request('/api/borrar', data, f'ERROR - {message}')
            
            return jsonify({
                'success': False,
                'error': message
            }), 404
        
    except Exception as e:
        log_api_request('/api/borrar', data if 'data' in locals() else {}, f'Exception: {e}')
        return jsonify({'error': f'Error interno: {str(e)}'}), 500
      
#trae las activaciones
@app.route('/api/sync-activaciones', methods=['GET'])
@require_auth_hybrid
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

#LIMPIAR LAS ACTICACIONES CON ADVERTENCIA
@app.route('/api/limpiar-activaciones', methods=['POST'])
@require_auth_hybrid
def api_limpiar_activaciones():
    """Limpiar todas las activaciones - ADVERTENCIA: Borra todo el historial"""
    try:
        activaciones_file = CONFIG_DIR / 'activaciones.json'
        
        # Verificar cuántas activaciones hay
        if activaciones_file.exists():
            with open(activaciones_file, 'r') as f:
                data = json.load(f)
                total = len(data.get('activaciones', []))
        else:
            total = 0
        
        # Vaciar archivo
        with open(activaciones_file, 'w') as f:
            json.dump({'activaciones': []}, f, indent=4)
        
        # También limpiar api.log
        api_log = CONFIG_DIR / 'api.log'
        if api_log.exists():
            with open(api_log, 'w') as f:
                f.write('')
        
        return jsonify({
            'success': True,
            'message': f'Se eliminaron {total} activaciones',
            'total_eliminadas': total
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
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
@require_auth_hybrid
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
@require_auth_hybrid
def api_estadisticas():
    """Obtener estadísticas de activaciones"""
    stats = obtener_estadisticas()
    return jsonify(stats), 200

def enviar_notificacion_telegram(tipo: str, datos: dict):
    """Enviar notificación al bot de Telegram vía webhook"""
    try:
        # Formatear mensaje según tipo
        if tipo == 'token_creado':
            mensaje = (
                f"✅ **Token creado**\n\n"
                f"👤 Nombre: `{datos['nombre']}`\n"
                f"🔑 Token: `{datos['token']}`\n"
                f"⏰ Días: `{datos['dias']}`\n"
                f"📅 Expira: `{datos['expira']}`\n"
                f"🌐 Origen: `{datos['origen']}`"
            )
        elif tipo == 'token_renovado':
            mensaje = (
                f"🔄 **Token renovado**\n\n"
                f"🔑 Token: `{datos['token']}`\n"
                f"⏰ Días: `{datos['dias']}`\n"
                f"📅 Expira: `{datos['expira']}`\n"
                f"🌐 Origen: `{datos['origen']}`"
            )
        elif tipo == 'ssh_creado':
            mensaje = (
                f"✅ **Usuario SSH creado**\n\n"
                f"👤 Usuario: `{datos['usuario']}`\n"
                f"⏰ Días: `{datos['dias']}`\n"
                f"📅 Expira: `{datos['expira']}`\n"
                f"🌐 Origen: `{datos['origen']}`"
            )
        elif tipo == 'usuario_borrado':
            mensaje = (
                f"🗑️ **Usuario eliminado**\n\n"
                f"🔑 Usuario: `{datos['usuario']}`\n"
                f"🌐 Origen: `{datos['origen']}`"
            )
        else:
            return
        
        # Enviar al webhook del bot
        import requests
        requests.post(
            'http://localhost:9999/notify',
            json={'mensaje': mensaje},
            timeout=2
        )
    except Exception as e:
        # Si falla, no pasa nada (el API sigue funcionando)
        print(f"No se pudo enviar notificación: {e}")


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    app.run(host='0.0.0.0', port=port, debug=False)
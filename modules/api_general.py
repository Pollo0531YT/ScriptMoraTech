#!/usr/bin/env python3
"""
API GENERAL - Sistema centralizado para gestionar múltiples VPS
VPS BOT - Dashboard Global y Panel de Control
"""


import json
import sys
import os
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, redirect
from pathlib import Path
from functools import wraps

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
app = Flask(__name__, template_folder=template_dir)
app.secret_key = 'moratech-general-key-2026'

SECRET_KEY = "moratech-key"
CONFIG_DIR = Path.home() / '.moratech'
VPS_CONFIG_FILE = CONFIG_DIR / 'vps_config.json'

# ==================== GESTIÓN DE VPS ====================

def load_vps_config():
    """Cargar configuración de VPS"""
    if not VPS_CONFIG_FILE.exists():
        return {'vps_list': []}
    
    with open(VPS_CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_vps_config(config):
    """Guardar configuración de VPS"""
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(VPS_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def require_auth(f):
    """Decorator para validar autenticación"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

# ==================== ENDPOINTS WEB ====================

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login para dashboard global"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == SECRET_KEY:
            session['authenticated'] = True
            return redirect('/dashboard-global')
        else:
            return render_template('login.html', error='Contraseña incorrecta')
    
    return render_template('login.html')

@app.route('/dashboard-global')
@require_auth
def dashboard_global():
    """Dashboard global - Vista de todas las VPS"""
    return render_template('dashboard_global.html')

@app.route('/panel-control')
@require_auth
def panel_control():
    """Panel de control - Activar en VPS"""
    return render_template('panel_control.html')

# ==================== API ENDPOINTS ====================

@app.route('/api/vps-list', methods=['GET'])
def api_vps_list():
    """Obtener lista de VPS configuradas"""
    config = load_vps_config()
    return jsonify(config['vps_list']), 200

@app.route('/api/vps-add', methods=['POST'])
@require_auth
def api_vps_add():
    """Agregar una VPS"""
    data = request.get_json()
    nombre = data.get('nombre')
    domain = data.get('domain')  # ej: directo2.moratech.work
    port_api = data.get('port_api', '9000')
    port_check = data.get('port_check', '8888')
    
    if not nombre or not domain:
        return jsonify({'error': 'Nombre y dominio requeridos'}), 400
    
    config = load_vps_config()
    
    # Generar ID
    max_id = max([v['id'] for v in config['vps_list']], default=0)
    
    # Construir URLs completas
    nueva_vps = {
        'id': max_id + 1,
        'nombre': nombre,
        'domain': domain,
        'url_api': f'http://{domain}:{port_api}',
        'url_checkuser': f'http://{domain}:{port_check}/checkUser',
        'activo': True
    }
    
    config['vps_list'].append(nueva_vps)
    save_vps_config(config)
    
    return jsonify({'success': True, 'vps': nueva_vps}), 200


# MEJORADO + full para recibir de todo lado
@app.route('/api/gestionar-token', methods=['POST'])
def api_gestionar_token():

    # --- NUEVA SEGURIDAD HÍBRIDA ---
    key = request.headers.get('X-Auth-Key')
    is_authenticated = session.get('authenticated')

    # Si no tiene Key Y no está logueado en la web -> Bloquear
    if not (key == SECRET_KEY or is_authenticated):
        return jsonify({'error': 'Acceso denegado'}), 401
    # -------------------------------
    
    data = request.get_json() or {}
    nombre = data.get('nombre')
    token = data.get('token')
    dias = data.get('dias', 30)
    referencia = data.get('referencia', '')
    accion_forzada = data.get('accion')  # "crear" o "renovar"
    vps_ids = data.get('vps_ids', [])
    origen_solicitud = data.get('origen', 'general')

    if not token:
        return jsonify({'error': 'token requerido'}), 400
    
    # Solo exigir nombre si sabemos que vamos a crear
    if not nombre and accion_forzada == 'crear':
        return jsonify({'error': 'nombre requerido para crear'}), 400

    config = load_vps_config()
    
    # --- LÓGICA DE COMPATIBILIDAD ---
    # Si vps_ids está vacío (viene del Bot), usamos todas las activas
    # Si vps_ids tiene datos (viene del JS), filtramos por esos IDs
    todas_activas = [v for v in config.get('vps_list', []) if v.get('activo')]
    
    if vps_ids and len(vps_ids) > 0:
        targets = [v for v in todas_activas if v.get('id') in vps_ids]
    else:
        targets = todas_activas

    if not targets:
        return jsonify({'error': 'No hay VPS disponibles para procesar'}), 404

    resultados = []
    headers = {'Content-Type': 'application/json', 'X-Auth-Key': SECRET_KEY}

    for v in targets:
        vps_name = v.get('nombre')
        vps_id = v.get('id')

        try:
            # Determinamos qué acción tomar para esta VPS específica
            if accion_forzada in ('crear', 'renovar'):
                act = accion_forzada
            else:
                # Fallback: consultar checkuser
                status = check_token_status(v.get('url_checkuser'), token)
                if status == 'not_exist':
                    act = 'crear'
                elif status == 'exists':
                    act = 'renovar'
                else:
                    resultados.append({'vps_nombre': vps_name, 'success': False, 'error': 'Status desconocido'})
                    continue

            # Construir endpoint y payload según la acción
            if act == 'crear':
                endpoint = f"{v.get('url_api')}/api/token"
                payload = {'nombre': nombre, 'token': token, 'dias': dias, 'referencia': referencia, 'origen': origen_solicitud}
            else:
                endpoint = f"{v.get('url_api')}/api/renovar"
                payload = {'nombre': nombre, 'token': token, 'dias': dias, 'referencia': referencia, 'origen': origen_solicitud}

            resp = requests.post(endpoint, headers=headers, json=payload, timeout=10)
            
            try:
                res_json = resp.json()
            except:
                res_json = {'success': resp.status_code < 300, 'error': 'Respuesta no JSON'}

            res_json.update({'vps_nombre': vps_name, 'vps_id': vps_id})
            resultados.append(res_json)

        except Exception as e:
            resultados.append({'vps_nombre': vps_name, 'vps_id': vps_id, 'success': False, 'error': str(e)})

    return jsonify({
        'token': token,
        'nombre': nombre,
        'total_targets': len(targets),
        'resultados': resultados,
        'exitosos': len([r for r in resultados if r.get('success')])
    }), 200


@app.route('/api/borrar-token', methods=['POST'])
@require_auth
def api_borrar_token():
    """Borrar token de VPS seleccionadas (verifica con checkUser antes de borrar)"""
    data = request.get_json() or {}
    token = data.get('token')
    vps_ids = data.get('vps_ids', [])
    origen = data.get('origen')

    if not token:
        return jsonify({'error': 'Token requerido'}), 400

    config = load_vps_config()
    resultados = []

    # si no vienen vps_ids, seleccionar todas activas
    if not vps_ids:
        vps_ids = [v['id'] for v in config['vps_list'] if v.get('activo')]

    for vps in config['vps_list']:
        if vps['id'] not in vps_ids or not vps.get('activo'):
            continue

        vps_name = vps.get('nombre')
        vps_id = vps.get('id')

        try:
            # 1) preguntar al checkuser si existe el token
            status = check_token_status(vps.get('url_checkuser'), token)

            if status == 'not_exist':
                resultados.append({
                    'vps_nombre': vps_name,
                    'vps_id': vps_id,
                    'success': False,
                    'accion': 'no_exist',
                    'error': 'Token no existe en esta VPS'
                })
                continue

            if status == 'error':
                resultados.append({
                    'vps_nombre': vps_name,
                    'vps_id': vps_id,
                    'success': False,
                    'accion': 'check_error',
                    'error': 'CheckUser no respondió correctamente'
                })
                continue

            # 2) si existe -> llamar al endpoint /api/borrar del VPS
            response = requests.post(
                f"{vps['url_api']}/api/borrar",
                headers={
                    'Content-Type': 'application/json',
                    'X-Auth-Key': SECRET_KEY
                },
                json={'user': token, 'origen': origen},
                timeout=10
            )

            # intentar parsear JSON de respuesta
            try:
                result = response.json()
            except Exception:
                result = {
                    'success': response.status_code in (200, 201),
                    'raw_status': response.status_code,
                    'raw_text': response.text[:500]
                }

            # enriquecer resultado con metadatos y accion
            result['vps_nombre'] = vps_name
            result['vps_id'] = vps_id
            result['accion'] = 'borrado' if result.get('success') else 'error'
            resultados.append(result)

        except requests.exceptions.RequestException as e:
            resultados.append({
                'vps_nombre': vps_name,
                'vps_id': vps_id,
                'success': False,
                'accion': 'error',
                'error': f'Request error: {str(e)}'
            })
        except Exception as e:
            resultados.append({
                'vps_nombre': vps_name,
                'vps_id': vps_id,
                'success': False,
                'accion': 'error',
                'error': str(e)
            })

    return jsonify({
        'token': token,
        'resultados': resultados,
        'total': len(resultados),
        'exitosos': len([r for r in resultados if r.get('success')])
    }), 200

#check tken
def check_token_status(vps_url_checkuser, token):
    """
    Consultar CheckUser para saber si el token existe
    Returns:
        - 'exists' si devuelve fecha (ej: "11012026")
        - 'not_exist' si devuelve "Not exist"
        - 'error' si no puede conectar
    """
    try:
        response = requests.post(
            vps_url_checkuser,
            json={'user': token},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.text.strip()
            
            # CheckUser devuelve texto plano, no JSON
            if result == "Not exist":
                return 'not_exist'
            elif len(result) == 8 and result.isdigit():  # Formato ddmmyyyy
                return 'exists'
            else:
                return 'error'
        else:
            return 'error'
    
    except Exception as e:
        return 'error'


#funciones que parecieran son directamente del panel
@app.route('/api/vps-remove/<int:vps_id>', methods=['DELETE'])
@require_auth
def api_vps_remove(vps_id):
    """Eliminar una VPS"""
    config = load_vps_config()
    config['vps_list'] = [v for v in config['vps_list'] if v['id'] != vps_id]
    save_vps_config(config)
    
    return jsonify({'success': True}), 200

@app.route('/api/vps-toggle/<int:vps_id>', methods=['POST'])
@require_auth
def api_vps_toggle(vps_id):
    """Activar/Desactivar una VPS"""
    config = load_vps_config()
    
    for vps in config['vps_list']:
        if vps['id'] == vps_id:
            vps['activo'] = not vps['activo']
            break
    
    save_vps_config(config)
    return jsonify({'success': True}), 200

@app.route('/api/sync-all', methods=['GET'])
def api_sync_all():
    """Sincronizar activaciones de TODAS las VPS"""
    config = load_vps_config()
    resultados = []
    
    for vps in config['vps_list']:
        if not vps['activo']:
            continue
        
        try:
            response = requests.get(
                f"{vps['url_api']}/api/sync-activaciones",
                headers={'X-Auth-Key': SECRET_KEY},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Agregar nombre de VPS a cada activación
                for act in data['activaciones']:
                    act['vps_nombre'] = vps['nombre']
                    act['vps_id'] = vps['id']
                
                resultados.extend(data['activaciones'])
            else:
                # VPS respondió pero con error
                resultados.append({
                    'vps_nombre': vps['nombre'],
                    'vps_id': vps['id'],
                    'error': f'Error {response.status_code}',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'success': False
                })
        
        except requests.exceptions.RequestException as e:
            # VPS offline o no responde
            resultados.append({
                'vps_nombre': vps['nombre'],
                'vps_id': vps['id'],
                'error': 'VPS Offline',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'success': False
            })
    
    # Ordenar por timestamp descendente
    resultados.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return jsonify(resultados), 200


# ==================== ENDPOINT PARA BOT Y CURL (SIN REDIRECT) ====================

@app.route('/api/bot-gestionar', methods=['POST'])
def api_bot_gestionar():
    """
    Ruta especial para el Bot y CURL que no requiere sesión de navegador.
    Valida mediante el header X-Auth-Key.
    """
    # 1. Validar la llave de seguridad
    key = request.headers.get('X-Auth-Key')
    if not key or key != SECRET_KEY:
        return jsonify({'error': 'No autorizado - Key incorrecta'}), 401

    # 2. Si la llave es correcta, llamamos a la lógica de gestionar_token
    # Nota: No usamos el decorador aquí, llamamos directamente a la función interna
    return api_gestionar_token()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9100
    app.run(host='0.0.0.0', port=port, debug=False)
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

@app.route('/api/gestionar-token', methods=['POST'])
@require_auth
def api_gestionar_token():
    """
    Gestionar token en VPS seleccionadas
    - Si existe en CheckUser → RENOVAR
    - Si no existe → CREAR NUEVO
    """
    data = request.get_json()
    
    nombre = data.get('nombre')
    token = data.get('token')
    dias = data.get('dias', 30)
    referencia = data.get('referencia', '')
    origen = data.get('origen', 'web')
    vps_ids = data.get('vps_ids', [])
    
    if not nombre or not token:
        return jsonify({'error': 'Nombre y token requeridos'}), 400
    
    config = load_vps_config()
    resultados = []
    
    # Si no hay VPS seleccionadas, usar todas activas
    if not vps_ids:
        vps_ids = [v['id'] for v in config['vps_list'] if v['activo']]
    
    for vps in config['vps_list']:
        if vps['id'] not in vps_ids or not vps['activo']:
            continue
        
        try:
            # 1. Consultar CheckUser para saber si existe
            status = check_token_status(vps['url_checkuser'], token)
            
            if status == 'not_exist':
                # CREAR NUEVO
                endpoint = f"{vps['url_api']}/api/token"
                payload = {
                    'nombre': nombre,
                    'token': token,
                    'dias': dias,
                    'referencia': referencia,
                    'origen': origen
                }
                accion = 'creado'
            
            elif status == 'exists':
                # RENOVAR
                endpoint = f"{vps['url_api']}/api/renovar"
                payload = {
                    'user': token,
                    'dias': dias,
                    'referencia': referencia,
                    'origen': origen
                }
                accion = 'renovado'
            
            else:
                # ERROR en CheckUser
                resultados.append({
                    'vps_nombre': vps['nombre'],
                    'vps_id': vps['id'],
                    'success': False,
                    'error': 'CheckUser no responde'
                })
                continue
            
            # 2. Ejecutar acción (crear o renovar)
            response = requests.post(
                endpoint,
                headers={
                    'Content-Type': 'application/json',
                    'X-Auth-Key': SECRET_KEY
                },
                json=payload,
                timeout=10
            )
            
            result = response.json()
            result['vps_nombre'] = vps['nombre']
            result['vps_id'] = vps['id']
            result['accion'] = accion
            resultados.append(result)
        
        except Exception as e:
            resultados.append({
                'vps_nombre': vps['nombre'],
                'vps_id': vps['id'],
                'success': False,
                'error': str(e)
            })
    
    return jsonify({
        'resultados': resultados,
        'total': len(resultados),
        'exitosos': len([r for r in resultados if r.get('success')])
    }), 200

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


@app.route('/api/borrar-token', methods=['POST'])
@require_auth
def api_borrar_token():
    """Borrar token de VPS seleccionadas"""
    data = request.get_json()
    
    token = data.get('token')
    vps_ids = data.get('vps_ids', [])
    
    if not token:
        return jsonify({'error': 'Token requerido'}), 400
    
    config = load_vps_config()
    resultados = []
    
    if not vps_ids:
        vps_ids = [v['id'] for v in config['vps_list'] if v['activo']]
    
    for vps in config['vps_list']:
        if vps['id'] not in vps_ids or not vps['activo']:
            continue
        
        try:
            response = requests.post(
                f"{vps['url_api']}/api/borrar",
                headers={
                    'Content-Type': 'application/json',
                    'X-Auth-Key': SECRET_KEY
                },
                json={'user': token},
                timeout=10
            )
            
            result = response.json()
            result['vps_nombre'] = vps['nombre']
            result['vps_id'] = vps['id']
            resultados.append(result)
        
        except Exception as e:
            resultados.append({
                'vps_nombre': vps['nombre'],
                'vps_id': vps['id'],
                'success': False,
                'error': str(e)
            })
    
    return jsonify({
        'resultados': resultados,
        'total': len(resultados),
        'exitosos': len([r for r in resultados if r.get('success')])
    }), 200

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
                f"{vps['url']}/api/sync-activaciones",
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

@app.route('/api/activar-token', methods=['POST'])
@require_auth
def api_activar_token():
    """Activar token en VPS seleccionadas"""
    data = request.get_json()
    
    nombre = data.get('nombre')
    token = data.get('token')
    dias = data.get('dias', 30)
    referencia = data.get('referencia', '')
    origen = data.get('origen', 'manual')
    vps_ids = data.get('vps_ids', [])  # Lista de IDs de VPS
    
    if not nombre or not token:
        return jsonify({'error': 'Nombre y token requeridos'}), 400
    
    config = load_vps_config()
    resultados = []
    
    # Si vps_ids está vacío, activar en TODAS
    if not vps_ids:
        vps_ids = [v['id'] for v in config['vps_list'] if v['activo']]
    
    for vps in config['vps_list']:
        if vps['id'] not in vps_ids or not vps['activo']:
            continue
        
        try:
            response = requests.post(
                f"{vps['url']}/api/token",
                headers={
                    'Content-Type': 'application/json',
                    'X-Auth-Key': SECRET_KEY
                },
                json={
                    'nombre': nombre,
                    'token': token,
                    'dias': dias,
                    'referencia': referencia,
                    'origen': origen
                },
                timeout=10
            )
            
            result = response.json()
            result['vps_nombre'] = vps['nombre']
            result['vps_id'] = vps['id']
            resultados.append(result)
        
        except Exception as e:
            resultados.append({
                'vps_nombre': vps['nombre'],
                'vps_id': vps['id'],
                'success': False,
                'error': str(e)
            })
    
    return jsonify({
        'resultados': resultados,
        'total': len(resultados),
        'exitosos': len([r for r in resultados if r.get('success')])
    }), 200

@app.route('/api/renovar-token', methods=['POST'])
@require_auth
def api_renovar_token():
    """Renovar token en VPS seleccionadas"""
    data = request.get_json()
    
    token = data.get('token')
    dias = data.get('dias', 30)
    referencia = data.get('referencia', '')
    origen = data.get('origen', 'manual')
    vps_ids = data.get('vps_ids', [])
    
    if not token:
        return jsonify({'error': 'Token requerido'}), 400
    
    config = load_vps_config()
    resultados = []
    
    if not vps_ids:
        vps_ids = [v['id'] for v in config['vps_list'] if v['activo']]
    
    for vps in config['vps_list']:
        if vps['id'] not in vps_ids or not vps['activo']:
            continue
        
        try:
            response = requests.post(
                f"{vps['url']}/api/renovar",
                headers={
                    'Content-Type': 'application/json',
                    'X-Auth-Key': SECRET_KEY
                },
                json={
                    'user': token,
                    'dias': dias,
                    'referencia': referencia,
                    'origen': origen
                },
                timeout=10
            )
            
            result = response.json()
            result['vps_nombre'] = vps['nombre']
            result['vps_id'] = vps['id']
            resultados.append(result)
        
        except Exception as e:
            resultados.append({
                'vps_nombre': vps['nombre'],
                'vps_id': vps['id'],
                'success': False,
                'error': str(e)
            })
    
    return jsonify({
        'resultados': resultados,
        'total': len(resultados),
        'exitosos': len([r for r in resultados if r.get('success')])
    }), 200

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9100
    app.run(host='0.0.0.0', port=port, debug=False)
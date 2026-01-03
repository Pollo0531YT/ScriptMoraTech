#!/usr/bin/env python3
"""
Sistema de registro de activaciones
Registra todas las operaciones del API para auditoría
"""
import json
from datetime import datetime
from pathlib import Path

CONFIG_DIR = Path.home() / '.moratech'
ACTIVACIONES_FILE = CONFIG_DIR / 'activaciones.json'

def init_activaciones():
    """Inicializar archivo de activaciones si no existe"""
    if not ACTIVACIONES_FILE.exists():
        with open(ACTIVACIONES_FILE, 'w') as f:
            json.dump({'activaciones': []}, f, indent=4)

def registrar_activacion(operacion, usuario, nombre, dias, referencia='', origen='manual', success=True, error_msg=''):
    """
    Registrar una activación en el historial
    
    Args:
        operacion: agregar_token, renovar, reiniciar, borrar
        usuario: username o token
        nombre: display name del usuario
        dias: días agregados/renovados
        referencia: referencia bancaria (opcional)
        origen: whatsapp, deposito, web, manual, etc
        success: True si fue exitoso
        error_msg: mensaje de error si falló
    """
    init_activaciones()
    
    try:
        with open(ACTIVACIONES_FILE, 'r') as f:
            data = json.load(f)
        
        # Generar ID autoincremental
        last_id = data['activaciones'][-1]['id'] if data['activaciones'] else 0
        
        activacion = {
            'id': last_id + 1,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'operacion': operacion,
            'usuario': usuario,
            'nombre': nombre,
            'dias': dias,
            'referencia': referencia,
            'origen': origen,
            'success': success,
            'error_msg': error_msg
        }
        
        data['activaciones'].append(activacion)
        
        # Guardar con límite de 1000 registros (para no crecer infinitamente)
        if len(data['activaciones']) > 1000:
            data['activaciones'] = data['activaciones'][-1000:]
        
        with open(ACTIVACIONES_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        
        return True
    except Exception as e:
        print(f"Error registrando activación: {e}")
        return False

def obtener_activaciones(limite=100, filtro_origen=None, filtro_usuario=None, filtro_referencia=None):
    """
    Obtener activaciones con filtros opcionales
    
    Args:
        limite: número máximo de registros a devolver
        filtro_origen: filtrar por origen (whatsapp, deposito, etc)
        filtro_usuario: filtrar por usuario/token
        filtro_referencia: buscar por referencia bancaria
    
    Returns:
        Lista de activaciones ordenadas por fecha descendente
    """
    init_activaciones()
    
    try:
        with open(ACTIVACIONES_FILE, 'r') as f:
            data = json.load(f)
        
        activaciones = data['activaciones']
        
        # Aplicar filtros
        if filtro_origen:
            activaciones = [a for a in activaciones if a['origen'] == filtro_origen]
        
        if filtro_usuario:
            activaciones = [a for a in activaciones if filtro_usuario.lower() in a['usuario'].lower() or filtro_usuario.lower() in a['nombre'].lower()]
        
        if filtro_referencia:
            activaciones = [a for a in activaciones if filtro_referencia in a.get('referencia', '')]
        
        # Ordenar por fecha descendente (más recientes primero)
        activaciones.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Limitar resultados
        return activaciones[:limite]
    
    except Exception as e:
        print(f"Error obteniendo activaciones: {e}")
        return []

def obtener_estadisticas():
    """Obtener estadísticas generales de activaciones"""
    init_activaciones()
    
    try:
        with open(ACTIVACIONES_FILE, 'r') as f:
            data = json.load(f)
        
        activaciones = data['activaciones']
        total = len(activaciones)
        exitosas = len([a for a in activaciones if a['success']])
        fallidas = total - exitosas
        
        # Contar por origen
        origenes = {}
        for a in activaciones:
            origen = a.get('origen', 'manual')
            origenes[origen] = origenes.get(origen, 0) + 1
        
        # Últimas 24 horas
        from datetime import timedelta
        ahora = datetime.now()
        hace_24h = ahora - timedelta(hours=24)
        recientes = [a for a in activaciones 
                    if datetime.strptime(a['timestamp'], '%Y-%m-%d %H:%M:%S') > hace_24h]
        
        return {
            'total': total,
            'exitosas': exitosas,
            'fallidas': fallidas,
            'ultimas_24h': len(recientes),
            'por_origen': origenes
        }
    
    except Exception as e:
        print(f"Error obteniendo estadísticas: {e}")
        return {
            'total': 0,
            'exitosas': 0,
            'fallidas': 0,
            'ultimas_24h': 0,
            'por_origen': {}
        }
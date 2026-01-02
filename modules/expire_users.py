#!/usr/bin/env python3
"""
Sistema de expiración automática de usuarios
Se ejecuta diariamente a las 6pm para bloquear usuarios expirados
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path

CONFIG_DIR = Path.home() / '.moratech'
USERS_FILE = CONFIG_DIR / 'users.json'
EXPIRE_LOG_FILE = CONFIG_DIR / 'expire.log'

def log_expire(message):
    """Registrar acción de expiración"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(EXPIRE_LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")

def expire_users():
    """Bloquear y desconectar usuarios expirados"""
    try:
        # Leer usuarios
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        
        now = datetime.now()
        expired_count = 0
        
        log_expire("=== Iniciando verificación de expiración ===")
        
        for username, data in users.items():
            expires = data.get('expires')
            
            if not expires:
                continue  # Usuario sin expiración
            
            try:
                expire_date = datetime.fromisoformat(expires)
                
                # Si ya expiró
                if now >= expire_date:
                    user_type = data.get('type', 'ssh')
                    display_name = data.get('display_name', username) if user_type == 'token' else username
                    
                    # 1. Bloquear cuenta en el sistema
                    result = subprocess.run(['usermod', '-L', username], 
                                          capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        log_expire(f"✓ Cuenta bloqueada: {display_name} ({username})")
                        
                        # 2. Matar todas las conexiones del usuario
                        kill_result = subprocess.run(['pkill', '-u', username], 
                                                   capture_output=True, text=True)
                        
                        if kill_result.returncode == 0:
                            log_expire(f"✓ Conexiones cerradas: {display_name}")
                        
                        # 3. Marcar como deshabilitado en JSON
                        users[username]['enabled'] = False
                        
                        expired_count += 1
                    else:
                        log_expire(f"✗ Error bloqueando: {display_name} - {result.stderr}")
                
            except Exception as e:
                log_expire(f"✗ Error procesando {username}: {e}")
        
        # Guardar cambios en JSON
        if expired_count > 0:
            with open(USERS_FILE, 'w') as f:
                json.dump(users, f, indent=4)
        
        log_expire(f"=== Verificación completada: {expired_count} usuarios expirados ===")
        
        return expired_count
        
    except Exception as e:
        log_expire(f"✗ Error crítico: {e}")
        return 0

if __name__ == '__main__':
    expire_users()
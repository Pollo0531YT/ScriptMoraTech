#!/usr/bin/env python3
"""
Configuración del sistema de expiración automática
"""
import subprocess
from pathlib import Path

def setup_expire_system():
    """Configura el sistema de expiración automática al instalar MORATECH"""
    try:
        # 1. Crear script ejecutable
        expire_script = '/usr/local/bin/moratech-expire'
        
        if not Path(expire_script).exists():
            script_content = '''#!/bin/bash
# Script para expirar usuarios - Ejecutado por cron a las 6pm
cd /usr/local/lib/moratech/modules
python3 expire_users.py
'''
            
            with open(expire_script, 'w') as f:
                f.write(script_content)
            
            subprocess.run(['chmod', '+x', expire_script], stderr=subprocess.DEVNULL)
            print("✓ Script de expiración creado")
        
        # 2. Configurar cron si no existe
        check_cron = subprocess.run(['crontab', '-l'], 
                                   capture_output=True, text=True)
        
        if check_cron.returncode == 0:
            cron_content = check_cron.stdout
        else:
            cron_content = ""
        
        # Agregar si no existe
        if 'moratech-expire' not in cron_content:
            new_cron = cron_content + "\n# MORATECH - Expiración automática de usuarios a las 6pm\n"
            new_cron += "0 18 * * * /usr/local/bin/moratech-expire\n"
            
            process = subprocess.Popen(['crontab', '-'], 
                                      stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
            
            process.communicate(input=new_cron.encode())
            print("✓ Cron configurado: Expiración diaria a las 6pm")
        else:
            print("✓ Sistema de expiración ya configurado")
        
        return True
    
    except Exception as e:
        print(f"⚠️  Advertencia: No se pudo configurar expiración automática: {e}")
        return False
#!/usr/bin/env python3
"""
MORATECH - Panel de Administración VPS
Sistema de gestión de usuarios SSH y protocolos
"""

import os
import sys
import json
import hashlib
import subprocess
import socket
from datetime import datetime, timedelta
from pathlib import Path

# Colores para terminal
class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

# Configuración
CONFIG_DIR = Path.home() / '.moratech'
CONFIG_FILE = CONFIG_DIR / 'config.json'
USERS_FILE = CONFIG_DIR / 'users.json'
LOGS_FILE = CONFIG_DIR / 'logs.json'
TOKEN_CONFIG_FILE = CONFIG_DIR / 'token_config.json'
CONNECTIONS_FILE = CONFIG_DIR / 'connections.json'
PROTOCOLS_FILE = CONFIG_DIR / 'protocols.json'

def clear_screen():
    """Limpia la pantalla"""
    os.system('clear')

def print_line():
    """Imprime línea decorativa"""
    print(f"{Color.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Color.END}")

def print_banner():
    """Muestra el banner de Moratech"""
    banner = f"""
{Color.PURPLE}{Color.BOLD}
    ███╗   ███╗ ██████╗ ██████╗  █████╗ ████████╗███████╗
    ████╗ ████║██╔═══██╗██╔══██╗██╔══██╗╚══██╔══╝██╔════╝
    ██╔████╔██║██║   ██║██████╔╝███████║   ██║   █████╗  
    ██║╚██╔╝██║██║   ██║██╔══██╗██╔══██║   ██║   ██╔══╝  
    ██║ ╚═╝ ██║╚██████╔╝██║  ██║██║  ██║   ██║   ███████╗
    ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝
{Color.END}"""
    print(banner)

def get_system_info():
    """Obtiene información del sistema"""
    info = {}
    try:
        # Sistema Operativo
        with open('/etc/os-release') as f:
            for line in f:
                if line.startswith('PRETTY_NAME'):
                    info['os'] = line.split('=')[1].strip().strip('"')
                    break
        
        # Arquitectura
        info['arch'] = subprocess.check_output("uname -m", shell=True).decode().strip()
        
        # CPUs
        info['cpus'] = subprocess.check_output("nproc", shell=True).decode().strip()
        
        # IP Pública
        try:
            info['ip'] = subprocess.check_output("curl -s ifconfig.me", shell=True, timeout=3).decode().strip()
        except:
            info['ip'] = "No disponible"
        
        # Fecha actual
        info['date'] = datetime.now().strftime("%d/%m/%Y-%H:%M")
        
        # Hostname
        info['hostname'] = socket.gethostname()
        
        # RAM
        mem = subprocess.check_output("free -m", shell=True).decode().split('\n')[1].split()
        info['ram_total'] = f"{float(mem[1])/1024:.1f}G"
        info['ram_used'] = f"{mem[2]}M"
        info['ram_free'] = f"{float(mem[3])/1024:.1f}G"
        info['ram_percent'] = f"{(int(mem[2])/int(mem[1])*100):.2f}%"
        
        # CPU usage
        try:
            cpu = subprocess.check_output("top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1}'", shell=True).decode().strip()
            info['cpu_percent'] = f"{float(cpu):.1f}%"
        except:
            info['cpu_percent'] = "N/A"
        
    except Exception as e:
        print(f"{Color.RED}Error obteniendo info del sistema: {e}{Color.END}")
    
    return info

def get_active_ports():
    """Obtiene puertos activos - DETECCIÓN AUTOMÁTICA"""
    ports = {
        'SSH': '22',
        'SSL': '-',
        'BadVPN': '-',
        'Proxy': '-',
        'V2Ray': '-',
        'SlowDNS': '-'
    }
    
    try:
        result = subprocess.run(['ss', '-tulpn'], capture_output=True, text=True)
        output = result.stdout
        
        # Detectar SSH
        if ':22 ' in output or ':22\n' in output:
            ports['SSH'] = '22 ✓'
        
        # Detectar SSL/Stunnel (busca stunnel en proceso)
        stunnel_check = subprocess.run(['pgrep', '-f', 'stunnel'], capture_output=True, text=True)
        if stunnel_check.stdout.strip():
            # Encontrar puerto de stunnel
            for line in output.split('\n'):
                if 'stunnel' in line:
                    if ':443 ' in line or ':443\n' in line:
                        ports['SSL'] = '443 ✓'
                        break
                    elif ':444 ' in line or ':444\n' in line:
                        ports['SSL'] = '444 ✓'
                        break
                    # Buscar cualquier puerto
                    import re
                    match = re.search(r':(\d+)\s', line)
                    if match:
                        ports['SSL'] = f"{match.group(1)} ✓"
                        break
        
        # Detectar Proxy Python (busca pythonwe o proxy.py)
        proxy_check = subprocess.run(['pgrep', '-f', 'proxy.py'], capture_output=True, text=True)
        if proxy_check.stdout.strip():
            # Buscar puerto 80
            if ':80 ' in output or ':80\n' in output:
                if 'python' in output:
                    ports['Proxy'] = '80 ✓'
            # Buscar otros puertos python
            for line in output.split('\n'):
                if 'python' in line.lower():
                    import re
                    match = re.search(r':(\d+)\s', line)
                    if match and match.group(1) not in ['22', '443']:
                        ports['Proxy'] = f"{match.group(1)} ✓"
                        break
        
        # Detectar BadVPN (puerto 7300/7200)
        if ':7300 ' in output or ':7300\n' in output:
            ports['BadVPN'] = '7300 ✓'
        elif ':7200 ' in output or ':7200\n' in output:
            ports['BadVPN'] = '7200 ✓'
        
        # Detectar SlowDNS (puerto 5300)
        if ':5300 ' in output or ':5300\n' in output:
            ports['SlowDNS'] = '5300 ✓'
            
    except Exception as e:
        pass
    
    return ports
def init_system():
    """Inicializa el sistema"""
    CONFIG_DIR.mkdir(exist_ok=True)
    
    if not USERS_FILE.exists():
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)
    
    if not CONFIG_FILE.exists():
        config = {
            "system_name": "Moratech Panel",
            "version": "2.0",
            "installed": datetime.now().isoformat()
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    
    if not LOGS_FILE.exists():
        with open(LOGS_FILE, 'w') as f:
            json.dump([], f)
    
    if not TOKEN_CONFIG_FILE.exists():
        with open(TOKEN_CONFIG_FILE, 'w') as f:
            json.dump({"token_password": None}, f)
    
    if not CONNECTIONS_FILE.exists():
        with open(CONNECTIONS_FILE, 'w') as f:
            json.dump({}, f)
    
    if not PROTOCOLS_FILE.exists():
        with open(PROTOCOLS_FILE, 'w') as f:
            json.dump({
                "ssl": {"enabled": False, "port": 443},
                "v2ray": {"enabled": False, "port": 0},
                "slowdns": {"enabled": False, "port": 0},
                "proxy": {"enabled": False, "port": 80},
                "badvpn": {"enabled": False, "port": 7300}
            }, f, indent=4)

def load_users():
    """Carga usuarios"""
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    """Guarda usuarios y sincroniza con el sistema Linux"""
    # Guardar en JSON
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)
    
    # Sincronizar con usuarios del sistema
    try:
        # Obtener usuarios actuales del sistema
        result = subprocess.run(['cut', '-d:', '-f1', '/etc/passwd'], capture_output=True, text=True)
        system_users = result.stdout.strip().split('\n')
        
        # Crear/actualizar usuarios que están en JSON
        for username, data in users.items():
            if username == 'admin':
                continue  # No crear admin como usuario SSH
            
            # Si el usuario no existe en el sistema, crearlo
            if username not in system_users:
                subprocess.run(['useradd', '-M', '-s', '/bin/false', username], 
                             stderr=subprocess.DEVNULL)
            
            # Actualizar contraseña
            password = data.get('password', '')
            subprocess.run(['chpasswd'], 
                         input=f"{username}:{password}\n".encode(),
                         stderr=subprocess.DEVNULL)
        
        # Eliminar usuarios del sistema que ya no están en JSON
        moratech_users = [u for u in users.keys() if u != 'admin']
        for sys_user in system_users:
            # Solo eliminar usuarios creados por moratech (los que están en /home/moratech o sin home)
            if sys_user.startswith('token_') or (sys_user in ['admin'] + moratech_users):
                if sys_user not in moratech_users and sys_user != 'admin':
                    subprocess.run(['userdel', '-f', sys_user], stderr=subprocess.DEVNULL)
                    
    except Exception as e:
        pass  # Si falla, solo continuar (no bloquear el guardado del JSON)

def load_token_config():
    """Carga config de tokens"""
    with open(TOKEN_CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_token_config(config):
    """Guarda config de tokens"""
    with open(TOKEN_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def log_action(user, action):
    """Registra acción en logs"""
    with open(LOGS_FILE, 'r') as f:
        logs = json.load(f)
    
    logs.append({
        "user": user,
        "action": action,
        "timestamp": datetime.now().isoformat()
    })
    
    with open(LOGS_FILE, 'w') as f:
        json.dump(logs, f, indent=4)

def show_dashboard():
    """Muestra el dashboard principal"""
    clear_screen()
    print_banner()
    
    # Información del sistema
    info = get_system_info()
    ports = get_active_ports()
    
    print_line()
    print(f" {Color.CYAN}∘{Color.END} S.O: {Color.GREEN}{info.get('os', 'N/A')}{Color.END}  {Color.CYAN}∘{Color.END} Base:{Color.GREEN}{info.get('arch', 'N/A')}{Color.END} {Color.CYAN}∘{Color.END} CPU's:{Color.GREEN}{info.get('cpus', 'N/A')}{Color.END}")
    print(f" {Color.CYAN}∘{Color.END} IP: {Color.GREEN}{info.get('ip', 'N/A')}{Color.END}  {Color.CYAN}∘{Color.END} FECHA: {Color.GREEN}{info.get('date', 'N/A')}{Color.END}")
    print_line()
    print(f" Key: {Color.GREEN}Verified{Color.END}【 {Color.YELLOW}MoraTech©{Color.END} 】(V2.0) ► {Color.CYAN}[{info.get('hostname', 'N/A')}]{Color.END}")
    print_line()
    
    # Puertos en formato de 2 columnas
    port_list = list(ports.items())
    for i in range(0, len(port_list), 2):
        left = port_list[i]
        right = port_list[i+1] if i+1 < len(port_list) else ("", "")
        
        left_status = f"{Color.GREEN}{left[1]}{Color.END}" if '✓' in left[1] else f"{Color.YELLOW}{left[1]}{Color.END}"
        right_status = f"{Color.GREEN}{right[1]}{Color.END}" if right[1] and '✓' in right[1] else f"{Color.YELLOW}{right[1]}{Color.END}" if right[1] else ""
        
        left_text = f" {Color.CYAN}∘{Color.END} {left[0]}: {left_status}"
        right_text = f"{Color.CYAN}∘{Color.END} {right[0]}: {right_status}" if right[0] else ""
        
        print(f"{left_text:<45} {right_text}")
    
    print_line()
    print(f" {Color.CYAN}∘{Color.END} TOTAL: {Color.GREEN}{info.get('ram_total', 'N/A')}{Color.END} {Color.CYAN}∘{Color.END} M|LIBRE: {Color.GREEN}{info.get('ram_free', 'N/A')}{Color.END}  {Color.CYAN}∘{Color.END} EN USO: {Color.GREEN}{info.get('ram_used', 'N/A')}{Color.END}")
    print(f" {Color.CYAN}∘{Color.END} U/RAM: {Color.GREEN}{info.get('ram_percent', 'N/A')}{Color.END}  {Color.CYAN}∘{Color.END} U/CPU: {Color.GREEN}{info.get('cpu_percent', 'N/A')}{Color.END}")
    print_line()

def login():
    """Sistema de login"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INICIO DE SESIÓN{Color.END}")
    print_line()
    
    users = load_users()
    max_attempts = 3
    
    for attempt in range(max_attempts):
        # Usuario visible
        username = input(f"\n {Color.GREEN}Usuario:{Color.END} ").strip()
        
        # Contraseña visible
        password = input(f" {Color.GREEN}Contraseña:{Color.END} ").strip()
        
        
        if username in users and users[username]['password'] == password:
            print(f"\n {Color.GREEN}✓ Login exitoso!{Color.END}")
            log_action(username, "Login exitoso")
            import time
            time.sleep(1)
            return username
        else:
            remaining = max_attempts - attempt - 1
            if remaining > 0:
                print(f" {Color.RED}✗ Credenciales incorrectas. Intentos restantes: {remaining}{Color.END}")
    
    return None
    
    return None

# ==================== MENÚ DE USUARIOS ====================

def add_user():
    """Agregar usuario SSH o Token"""
    clear_screen()
    print_line()
    print(f" {Color.CYAN}CREAR CUENTA{Color.END}")
    print_line()
    print(f"{Color.YELLOW}USUARIO:{Color.END}")
    print(f"{Color.GREEN}1.{Color.END} > SSH")
    print(f"{Color.GREEN}2.{Color.END} > TOKEN")
    print_line()
    print(f"{Color.GREEN}0.{Color.END} Volver")
    
    choice = input(f"\n{Color.YELLOW}Selecciona: {Color.END}").strip()
    
    if choice == '1':
        add_ssh_user()
    elif choice == '2':
        add_token_user()

def add_ssh_user():
    """Agregar usuario SSH"""
    users = load_users()
    
    print(f"\n{Color.CYAN}--- NUEVO USUARIO SSH ---{Color.END}\n")
    
    username = input(f"{Color.GREEN}Nombre de usuario: {Color.END}").strip()
    
    if username in users:
        print(f"{Color.RED}✗ El usuario ya existe{Color.END}")
        input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    # Contraseña visible
    password = input(f"{Color.GREEN}Contraseña: {Color.END}").strip()
    
    # Días
    days = input(f"{Color.GREEN}Días de duración (0 = ilimitado): {Color.END}").strip()
    try:
        days = int(days)
        expires = (datetime.now() + timedelta(days=days)).isoformat() if days > 0 else None
    except:
        expires = None
    
    # Conexiones
    max_conn = input(f"{Color.GREEN}Máximas conexiones: {Color.END}").strip()
    try:
        max_conn = int(max_conn)
    except:
        max_conn = 1
    
    users[username] = {
        "password": password,
        "role": "user",
        "type": "ssh",
        "created": datetime.now().isoformat(),
        "expires": expires,
        "max_connections": max_conn,
        "enabled": True
    }
    
    save_users(users)
    log_action("admin", f"Usuario SSH creado: {username}")
    print(f"\n{Color.GREEN}✓ Usuario SSH creado exitosamente{Color.END}")
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def add_token_user():
    """Agregar usuario Token"""
    token_config = load_token_config()
    users = load_users()
    
    print(f"\n{Color.CYAN}--- NUEVO USUARIO TOKEN ---{Color.END}\n")
    
    # Verificar si existe contraseña maestra
    if not token_config.get('token_password'):
        print(f"{Color.YELLOW}No hay contraseña configurada para tokens.{Color.END}\n")
        
        # Contraseña visible
        token_pass = input(f"{Color.GREEN}Contraseña maestra para tokens: {Color.END}").strip()
        
        token_config['token_password'] = token_pass
        save_token_config(token_config)
        print(f"{Color.GREEN}✓ Contraseña configurada{Color.END}\n")
    
    # Token
    token_input = input(f"{Color.GREEN}Ingresa el token: {Color.END}").strip()
    token_username = token_input  # Usa el token directamente como username
    
    if token_username in users:
        print(f"{Color.RED}✗ Este token ya fue usado{Color.END}")
        input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    # Días
    days = input(f"{Color.GREEN}Días de duración: {Color.END}").strip()
    try:
        days = int(days)
        expires = (datetime.now() + timedelta(days=days)).isoformat()
    except:
        print(f"{Color.RED}✗ Valor inválido{Color.END}")
        input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    users[token_username] = {
        "password": token_config['token_password'],
        "role": "user",
        "type": "token",
        "created": datetime.now().isoformat(),
        "expires": expires,
        "max_connections": 1,
        "enabled": True,
        "original_token": token_input
    }
    
    save_users(users)
    log_action("admin", f"Usuario token creado: {token_username}")
    print(f"\n{Color.GREEN}✓ Usuario token creado{Color.END}")
    print(f"{Color.YELLOW}Username: {token_username}{Color.END}")
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def delete_users_menu():
    """Menú para eliminar usuarios"""
    while True:
        clear_screen()
        print_banner()
        print(f"\n{Color.CYAN}╔══════════════════════════════════════════════════════════╗{Color.END}")
        print(f"{Color.CYAN}║              ELIMINAR USUARIOS                           ║{Color.END}")
        print(f"{Color.CYAN}╚══════════════════════════════════════════════════════════╝{Color.END}\n")
        
        print(f"{Color.GREEN}1.{Color.END} Eliminar usuario específico")
        print(f"{Color.GREEN}2.{Color.END} Eliminar iterativo (1x1)")
        print(f"{Color.GREEN}3.{Color.END} Eliminar solo caducados")
        print(f"{Color.GREEN}4.{Color.END} Eliminar TODOS")
        print(f"{Color.GREEN}0.{Color.END} Volver")
        
        choice = input(f"\n{Color.YELLOW}Selecciona: {Color.END}").strip()
        
        if choice == '1':
            delete_specific_user()
        elif choice == '2':
            delete_iterative()
        elif choice == '3':
            delete_expired()
        elif choice == '4':
            delete_all_users()
        elif choice == '0':
            break

def delete_specific_user():
    """Eliminar usuario específico"""
    users = load_users()
    
    username = input(f"\n{Color.GREEN}Usuario a eliminar: {Color.END}").strip()
    
    if username == "admin":
        print(f"{Color.RED}✗ No puedes eliminar el usuario admin{Color.END}")
    elif username in users:
        del users[username]
        save_users(users)
        log_action("admin", f"Usuario eliminado: {username}")
        print(f"{Color.GREEN}✓ Usuario eliminado{Color.END}")
    else:
        print(f"{Color.RED}✗ Usuario no encontrado{Color.END}")
    
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def delete_iterative():
    """Eliminar usuarios uno por uno"""
    users = load_users()
    
    for username in list(users.keys()):
        if username == "admin":
            continue
        
        print(f"\n{Color.YELLOW}Usuario: {username}{Color.END}")
        confirm = input(f"¿Eliminar? (s/n): ").strip().lower()
        
        if confirm == 's':
            del users[username]
            print(f"{Color.GREEN}✓ Eliminado{Color.END}")
    
    save_users(users)
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def delete_expired():
    """Eliminar solo usuarios caducados"""
    users = load_users()
    deleted = 0
    
    for username in list(users.keys()):
        if username == "admin":
            continue
        
        user_data = users[username]
        if user_data.get('expires'):
            expire_date = datetime.fromisoformat(user_data['expires'])
            if datetime.now() > expire_date:
                del users[username]
                deleted += 1
                print(f"{Color.GREEN}✓ Eliminado: {username}{Color.END}")
    
    save_users(users)
    print(f"\n{Color.YELLOW}Total eliminados: {deleted}{Color.END}")
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def delete_all_users():
    """Eliminar TODOS los usuarios"""
    print(f"\n{Color.RED}⚠️  ADVERTENCIA: Esto eliminará TODOS los usuarios (excepto admin){Color.END}")
    confirm = input(f"{Color.YELLOW}Escribe 'CONFIRMAR' para continuar: {Color.END}").strip()
    
    if confirm == "CONFIRMAR":
        users = {"admin": load_users()["admin"]}
        save_users(users)
        log_action("admin", "Todos los usuarios eliminados")
        print(f"{Color.GREEN}✓ Todos los usuarios eliminados{Color.END}")
    else:
        print(f"{Color.YELLOW}Operación cancelada{Color.END}")
    
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def edit_user():
    """Editar o renovar usuario"""
    print(f"\n{Color.YELLOW}Función en desarrollo...{Color.END}")
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def show_users():
    """Mostrar usuarios registrados"""
    clear_screen()
    print_banner()
    print(f"\n{Color.CYAN}╔══════════════════════════════════════════════════════════╗{Color.END}")
    print(f"{Color.CYAN}║              USUARIOS REGISTRADOS                        ║{Color.END}")
    print(f"{Color.CYAN}╚══════════════════════════════════════════════════════════╝{Color.END}\n")
    
    users = load_users()
    
    for username, data in users.items():
        user_type = data.get('type', 'ssh')
        expires = data.get('expires')
        
        if expires:
            expire_date = datetime.fromisoformat(expires)
            if datetime.now() > expire_date:
                status = f"{Color.RED}EXPIRADO{Color.END}"
            else:
                days = (expire_date - datetime.now()).days
                status = f"{Color.GREEN}{days} días{Color.END}"
        else:
            status = f"{Color.BLUE}ILIMITADO{Color.END}"
        
        print(f"{Color.YELLOW}{username}{Color.END} ({user_type}) - {status}")
    
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def control_usuarios_menu():
    """Menú de control de usuarios"""
    while True:
        clear_screen()

        print_line()
        print(f" {Color.CYAN} >> CONTROL DE USUARIOS <<{Color.END}")
        print_line()

        print(f" {Color.GREEN}[01]{Color.END} ➮ AGREGAR USUARIO (SSH/TOKEN)")
        print(f" {Color.GREEN}[02]{Color.END} ➮ BORRAR 1/TODOS LOS USUARIO/s")
        print(f" {Color.GREEN}[03]{Color.END} ➮ EDITAR/RENOVAR USUARIOS")
        print(f" {Color.GREEN}[04]{Color.END} ➮ MOSTRAR USUARIOS REGISTRADOS")
        print_line()
        print(f" {Color.GREEN}[09]{Color.END} ➮ BACKUP USUARIOS")
        print(f" {Color.GREEN}[10]{Color.END} ➮ CHECKUSER ONLINE")
        print(f" {Color.GREEN}[11]{Color.END} ➮ BOT TELEGRAM")
        print_line()
        print(f" {Color.GREEN}[12]{Color.END} ➮ REINICIAR CONTRASEÑA TOKEN")
        print_line()
        print(f" {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}Volver{Color.END}")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
        
        if choice == '1' or choice == '01':
            add_user()
        elif choice == '2' or choice == '02':
            delete_users_menu()
        elif choice == '3' or choice == '03':
            edit_user()
        elif choice == '4' or choice == '04':
            show_users()
        elif choice == '9' or choice == '09':
            print(f"\n {Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        elif choice == '10':
            print(f"\n {Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        elif choice == '11':
            print(f"\n {Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        elif choice == '12':
            reset_token_password()
        elif choice == '0':
            break

# ==================== MENÚ DE PROTOCOLOS ====================

def protocols_menu():
    """Menú de protocolos"""
    while True:
        clear_screen()
        print_line()
        print(f" {Color.CYAN}>> INSTALACION DE PROTOCOLOS <<{Color.END}")
        print_line()
  
        print(f"{Color.GREEN}1.{Color.END} ➮ SSL/TLS")
        print(f"{Color.GREEN}2.{Color.END} ➮ PROXY PYTHON")
        print(f"{Color.GREEN}3.{Color.END} ➮ V2RAY SWITCH")
        print(f"{Color.GREEN}4.{Color.END} ➮ SlowDNS (desarrollo...)")

        print_line()
        print(f" {Color.CYAN}HERRAMIENTAS Y SERVICIOS{Color.END}")
        print_line()

        print(f"{Color.GREEN}5.{Color.END} ➮ BadVPN")
        print(f"{Color.GREEN}5.{Color.END} ➮ EXTRAS (desarrollo...)")
        

        print_line()
        print(f"{Color.GREEN}0.{Color.END} Volver")
        
        choice = input(f"\n{Color.YELLOW}Selecciona: {Color.END}").strip()
        if choice == '1':
            menu_ssl()
        elif choice == '2':
            menu_phyton() 
        elif choice == '3':
            menu_v2ray()
        elif choice == '5':
            menu_badvpn() 
        elif choice == '0':
            break
        else:
            print(f"\n{Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

# ==================== FUNCIONES DE PROTOCOLOS ====================
def menu_ssl():
    """Menu de ssl"""
    while True:
        #show_dashboard()

        # Mostrar estado actual - DETECCIÓN AUTOMÁTICA
        try:
            result = subprocess.run(['ss', '-tulpn'], capture_output=True, text=True)
            output = result.stdout
            
            # Detectar todos los puertos SSL/Stunnel
            ssl_ports = []
            for line in output.split('\n'):
                if 'stunnel' in line:
                    import re
                    match = re.search(r':(\d+)\s', line)
                    if match:
                        ssl_ports.append(match.group(1))
            
            if ssl_ports:
                ports_str = ", ".join(ssl_ports)
                ssl_status = f"{Color.GREEN}ACTIVO - Puerto(s) {ports_str}{Color.END}"
            else:
                ssl_status = f"{Color.YELLOW}INACTIVO{Color.END}"
        
            print(f" {Color.CYAN}∘{Color.END} CONFIGURACION SSL: {ssl_status}")
            print_line()
        except:
            pass
  
        print(f"{Color.GREEN}1.{Color.END} Agregar puerto")
        print(f"{Color.GREEN}2.{Color.END} Detener puerto")
        print(f"{Color.GREEN}0.{Color.END} Volver")
        
        choice = input(f"\n{Color.YELLOW}Selecciona: {Color.END}").strip()
        if choice == '1':
            install_ssl()
        elif choice == '2':
            stop_ssl()    
        elif choice == '0':
            break
        else:
            print(f"\n{Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def install_ssl():
    """Instalar SSL con Let's Encrypt (igual a la que funciona)"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INSTALANDO SSL CON LET'S ENCRYPT{Color.END}")
    print_line()
    
    domain = input(f"\n {Color.GREEN}Dominio (ej: vps2.moratech.work): {Color.END}").strip()
    if not domain:
        print(f" {Color.RED}✗ Dominio requerido{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    port = input(f" {Color.GREEN}Puerto para SSL (default 443): {Color.END}").strip()
    if not port:
        port = "443"
    
    print(f"\n {Color.YELLOW}Instalando SSL con certificado Let's Encrypt...{Color.END}")
    
    try:
        # Detener servicios anteriores
        subprocess.run(['pkill', '-f', 'stunnel4'], stderr=subprocess.DEVNULL)
        subprocess.run(['service', 'stunnel4', 'stop'], stderr=subprocess.DEVNULL)
        
        # Instalar stunnel y certbot
        print(f" {Color.YELLOW}Instalando paquetes...{Color.END}")
        subprocess.run(['apt-get', 'update'], stdout=subprocess.DEVNULL)
        subprocess.run(['apt-get', 'install', '-y', 'stunnel4', 'certbot'], stdout=subprocess.DEVNULL)
        
        # Detener servicios que usen puerto 80
        subprocess.run(['systemctl', 'stop', 'nginx'], stderr=subprocess.DEVNULL)
        subprocess.run(['systemctl', 'stop', 'apache2'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-f', 'pythonwe'], stderr=subprocess.DEVNULL)
        
        import time
        time.sleep(2)
        
        # Obtener certificado
        print(f" {Color.YELLOW}Obteniendo certificado SSL para {domain}...{Color.END}")
        
        result = subprocess.run([
            'certbot', 'certonly', '--standalone', 
            '-d', domain, 
            '--non-interactive', 
            '--agree-tos', 
            '--register-unsafely-without-email'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f" {Color.RED}✗ Error obteniendo certificado{Color.END}")
            print(result.stderr)
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        print(f" {Color.GREEN}✓ Certificado obtenido{Color.END}")
        
        # Combinar certificado y clave
        print(f" {Color.YELLOW}Configurando certificado...{Color.END}")
        cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
        key_path = f"/etc/letsencrypt/live/{domain}/privkey.pem"
        
        subprocess.run([
            'bash', '-c',
            f'cat {cert_path} {key_path} > /etc/stunnel/stunnel.pem'
        ])
        
        subprocess.run(['chmod', '600', '/etc/stunnel/stunnel.pem'])
        
        # Obtener puerto SSH
        ssh_port = '22'
        
        # Configuración stunnel EXACTA como la máquina que funciona
        stunnel_conf = f"""cert = /etc/stunnel/stunnel.pem
client = no
socket = a:SO_REUSEADDR=1
socket = l:TCP_NODELAY=1
socket = r:TCP_NODELAY=1

[ssh-tls]
connect = 127.0.0.1:{ssh_port}
accept = {port}
cert = /etc/stunnel/stunnel.pem
TIMEOUTclose = 0
"""
        
        with open('/etc/stunnel/stunnel.conf', 'w') as f:
            f.write(stunnel_conf)
        
        # Configurar /etc/default/stunnel4
        with open('/etc/default/stunnel4', 'r') as f:
            content = f.read()
        
        if 'FILES="/etc/stunnel/*.conf"' not in content:
            with open('/etc/default/stunnel4', 'a') as f:
                f.write('\nFILES="/etc/stunnel/*.conf"\n')
        
        # Iniciar
        print(f" {Color.YELLOW}Iniciando Stunnel...{Color.END}")
        subprocess.run(['systemctl', 'daemon-reload'])
        subprocess.run(['systemctl', 'restart', 'stunnel4'])
        subprocess.run(['systemctl', 'enable', 'stunnel4'], stderr=subprocess.DEVNULL)
        
        time.sleep(2)
        
        # Verificar
        result = subprocess.run(['systemctl', 'status', 'stunnel4'], capture_output=True, text=True)
        if 'active (running)' in result.stdout:
            print(f" {Color.GREEN}✓ Stunnel iniciado{Color.END}")
        
        # Verificar puerto
        result = subprocess.run(['ss', '-tuln'], capture_output=True, text=True)
        if f':{port}' in result.stdout:
            print(f" {Color.GREEN}✓ Puerto {port} escuchando{Color.END}")
        
        # Abrir puerto
        subprocess.run(['ufw', 'allow', port], stderr=subprocess.DEVNULL)
        subprocess.run(['iptables', '-I', 'INPUT', '-p', 'tcp', '--dport', port, '-j', 'ACCEPT'])
        
        # Forwarding
        print(f" {Color.YELLOW}Configurando forwarding...{Color.END}")
        configure_forwarding()
        print(f" {Color.GREEN}✓ Forwarding configurado{Color.END}")
        
        # Guardar en config
        with open(PROTOCOLS_FILE, 'r') as f:
            protocols = json.load(f)
        
        protocols['ssl']['enabled'] = True
        protocols['ssl']['port'] = int(port)
        protocols['ssl']['domain'] = domain
        protocols['ssl']['cert_type'] = 'letsencrypt'
        
        with open(PROTOCOLS_FILE, 'w') as f:
            json.dump(protocols, f, indent=4)
        
        print(f"\n {Color.GREEN}✓ SSL Let's Encrypt instalado exitosamente{Color.END}")
        print(f" {Color.CYAN}Dominio: {domain}{Color.END}")
        print(f" {Color.CYAN}Puerto: {port}{Color.END}")
        print(f" {Color.YELLOW}Certificado válido por 90 días{Color.END}")
        log_action("admin", f"SSL Let's Encrypt: {domain}:{port}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def stop_ssl():
    """Detener SSL/Stunnel"""
    clear_screen()
    print_line()
    print(f" {Color.CYAN}DETENER SSL/STUNNEL{Color.END}")
    print_line()
    
    try:
        # Mostrar puertos SSL activos
        result = subprocess.run(['ss', '-tulpn'], capture_output=True, text=True)
        ssl_ports = []
        
        for line in result.stdout.split('\n'):
            if 'stunnel' in line:
                import re
                match = re.search(r':(\d+)\s', line)
                if match:
                    ssl_ports.append(match.group(1))
        
        if not ssl_ports:
            print(f"\n {Color.YELLOW}No hay puertos SSL activos{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        # Eliminar duplicados y ordenar
        ssl_ports = sorted(list(set(ssl_ports)))
        
        print(f"\n {Color.YELLOW}Puertos SSL activos:{Color.END}")
        for i, port in enumerate(ssl_ports, 1):
            print(f" {Color.GREEN}[{i}]{Color.END} Puerto {port}")
        
        print(f"\n {Color.GREEN}[0]{Color.END} Detener TODOS los puertos SSL")
        print(f" {Color.RED}[X]{Color.END} Cancelar")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Selecciona opción: ").strip()
        
        if choice.upper() == 'X':
            return
        
        if choice == '0':
            # Detener todo
            confirm = input(f"\n {Color.YELLOW}¿Detener TODOS los servicios SSL? (s/n): {Color.END}").strip().lower()
            if confirm != 's':
                return
            
            subprocess.run(['pkill', '-f', 'stunnel4'], stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'stunnel'], stderr=subprocess.DEVNULL)
            subprocess.run(['service', 'stunnel4', 'stop'], stderr=subprocess.DEVNULL)
            
            # Limpiar config
            with open(PROTOCOLS_FILE, 'r') as f:
                protocols = json.load(f)
            
            protocols['ssl']['enabled'] = False
            
            with open(PROTOCOLS_FILE, 'w') as f:
                json.dump(protocols, f, indent=4)
            
            print(f"\n {Color.GREEN}✓ Todos los servicios SSL detenidos{Color.END}")
            log_action("admin", "Todos los servicios SSL detenidos")
            
        else:
            # Detener puerto específico
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(ssl_ports):
                    port = ssl_ports[idx]
                    
                    # Leer configuración actual
                    with open('/etc/stunnel/stunnel.conf', 'r') as f:
                        lines = f.readlines()
                    
                    # Filtrar secciones que usan ese puerto
                    new_lines = []
                    skip = False
                    
                    for line in lines:
                        if line.strip().startswith('['):
                            skip = False
                        
                        if f'accept = {port}' in line:
                            skip = True
                            continue
                        
                        if not skip:
                            new_lines.append(line)
                    
                    # Guardar nueva configuración
                    with open('/etc/stunnel/stunnel.conf', 'w') as f:
                        f.writelines(new_lines)
                    
                    # Reiniciar stunnel
                    subprocess.run(['service', 'stunnel4', 'restart'], stderr=subprocess.DEVNULL)
                    
                    # Cerrar puerto en firewall
                    subprocess.run(['iptables', '-D', 'INPUT', '-p', 'tcp', '--dport', port, '-j', 'ACCEPT'], stderr=subprocess.DEVNULL)
                    
                    print(f"\n {Color.GREEN}✓ Puerto {port} SSL detenido{Color.END}")
                    log_action("admin", f"Puerto {port} SSL detenido")
                else:
                    print(f" {Color.RED}✗ Opción inválida{Color.END}")
            except ValueError:
                print(f" {Color.RED}✗ Opción inválida{Color.END}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def menu_phyton():
    """Menu de phyton"""
    while True:
        #show_dashboard()

        # Mostrar estado actual - DETECCIÓN AUTOMÁTICA
        try:
            result = subprocess.run(['ss', '-tulpn'], capture_output=True, text=True)
            output = result.stdout
            
            # Detectar Proxy Python
            proxy_ports = []
            proxy_check = subprocess.run(['pgrep', '-f', 'proxy.py'], capture_output=True, text=True)
            if proxy_check.stdout.strip():
                for line in output.split('\n'):
                    if 'python' in line.lower():
                        import re
                        match = re.search(r':(\d+)\s', line)
                        if match and match.group(1) not in ['22']:
                            proxy_ports.append(match.group(1))
            
            if proxy_ports:
                ports_str = ", ".join(set(proxy_ports))
                proxy_status = f"{Color.GREEN}ACTIVO - Puerto(s) {ports_str}{Color.END}"
            else:
                proxy_status = f"{Color.YELLOW}INACTIVO{Color.END}"
            
            print(f" {Color.CYAN}∘{Color.END} CONFIGURACION PHYTON: {proxy_status}")
            print_line()
        except:
            pass
  
        print(f"{Color.GREEN}1.{Color.END} Agregar puerto")
        print(f"{Color.GREEN}2.{Color.END} Detener puerto")
        print(f"{Color.GREEN}0.{Color.END} Volver")
        
        choice = input(f"\n{Color.YELLOW}Selecciona: {Color.END}").strip()
        if choice == '1':
            install_proxy()
        elif choice == '2':
            stop_proxy()    
        elif choice == '0':
            break
        else:
            print(f"\n{Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def install_proxy():
    """Instalar Proxy Python (Python 2) - versión que funciona"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INSTALANDO PROXY PYTHON{Color.END}")
    print_line()

    port = input(f"\n {Color.GREEN}Puerto para Proxy (default 80): {Color.END}").strip()
    if not port:
        port = "80"

    # Verificar y liberar puerto si está ocupado
    try:
        result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
        pids = result.stdout.strip()
        if pids:
            print(f"\n {Color.RED}⚠ Puerto {port} está en uso:{Color.END}")
            result_process = subprocess.run(['lsof', '-i', f':{port}'], capture_output=True, text=True)
            print(result_process.stdout)
            confirm = input(f"\n {Color.YELLOW}¿Liberar el puerto {port}? (s/n): {Color.END}").strip().lower()
            if confirm == 's':
                for pid in pids.split('\n'):
                    if pid:
                        subprocess.run(['kill', '-9', pid], stderr=subprocess.DEVNULL)
                import time
                time.sleep(2)
            else:
                print(f" {Color.RED}Instalación cancelada{Color.END}")
                input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                return
    except:
        pass

    print(f"\n {Color.YELLOW}Instalando Proxy Python en puerto {port}...{Color.END}")

    try:
        # Detener procesos previos
        subprocess.run(['pkill', '-f', 'pythonwe'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-f', 'proxy.py'], stderr=subprocess.DEVNULL)

        # Instalar dependencias
        print(f" {Color.YELLOW}Instalando dependencias...{Color.END}")
        subprocess.run(['apt-get', 'update'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['apt-get', 'install', 'python2', '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['apt-get', 'install', 'python', '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['apt-get', 'install', 'screen', '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['apt-get', 'install', 'lsof', '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Detectar puerto SSH
        ssh_port = '22'
        print(f" {Color.YELLOW}Puerto SSH: {ssh_port}{Color.END}")

        # Script Python 2 ORIGINAL que funciona
        proxy_script = f"""#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import socket, threading, thread, select, signal, sys, time, getopt

# CONFIG
LISTENING_ADDR = '0.0.0.0'
LISTENING_PORT = {port}
PASS = ''

# CONST
BUFLEN = 4096 * 4
TIMEOUT = 60
DEFAULT_HOST = "127.0.0.1:{ssh_port}"
RESPONSE = 'HTTP/1.1 101 Switching Protocols! \\r\\n\\r\\n'
 
class Server(threading.Thread):
    def __init__(self, host, port):
        threading.Thread.__init__(self)
        self.running = False
        self.host = host
        self.port = port
        self.threads = []
        self.threadsLock = threading.Lock()
        self.logLock = threading.Lock()

    def run(self):
        self.soc = socket.socket(socket.AF_INET)
        self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.soc.settimeout(2)
        self.soc.bind((self.host, self.port))
        self.soc.listen(0)
        self.running = True

        try:                    
            while self.running:
                try:
                    c, addr = self.soc.accept()
                    c.setblocking(1)
                except socket.timeout:
                    continue
                
                conn = ConnectionHandler(c, self, addr)
                conn.start();
                self.addConn(conn)
        finally:
            self.running = False
            self.soc.close()
            
    def printLog(self, log):
        self.logLock.acquire()
        print log
        self.logLock.release()
    
    def addConn(self, conn):
        try:
            self.threadsLock.acquire()
            if self.running:
                self.threads.append(conn)
        finally:
            self.threadsLock.release()
                    
    def removeConn(self, conn):
        try:
            self.threadsLock.acquire()
            self.threads.remove(conn)
        finally:
            self.threadsLock.release()
                
    def close(self):
        try:
            self.running = False
            self.threadsLock.acquire()
            
            threads = list(self.threads)
            for c in threads:
                c.close()
        finally:
            self.threadsLock.release()
            

class ConnectionHandler(threading.Thread):
    def __init__(self, socClient, server, addr):
        threading.Thread.__init__(self)
        self.clientClosed = False
        self.targetClosed = True
        self.client = socClient
        self.client_buffer = ''
        self.server = server
        self.log = 'Connection: ' + str(addr)

    def close(self):
        try:
            if not self.clientClosed:
                self.client.shutdown(socket.SHUT_RDWR)
                self.client.close()
        except:
            pass
        finally:
            self.clientClosed = True
            
        try:
            if not self.targetClosed:
                self.target.shutdown(socket.SHUT_RDWR)
                self.target.close()
        except:
            pass
        finally:
            self.targetClosed = True

    def run(self):
        try:
            self.client_buffer = self.client.recv(BUFLEN)
        
            hostPort = self.findHeader(self.client_buffer, 'X-Real-Host')
            
            if hostPort == '':
                hostPort = DEFAULT_HOST

            split = self.findHeader(self.client_buffer, 'X-Split')

            if split != '':
                self.client.recv(BUFLEN)
            
            if hostPort != '':
                passwd = self.findHeader(self.client_buffer, 'X-Pass')
                
                if len(PASS) != 0 and passwd == PASS:
                    self.method_CONNECT(hostPort)
                elif len(PASS) != 0 and passwd != PASS:
                    self.client.send('HTTP/1.1 400 WrongPass!\\r\\n\\r\\n')
                elif hostPort.startswith('127.0.0.1') or hostPort.startswith('localhost'):
                    self.method_CONNECT(hostPort)
                else:
                    self.client.send('HTTP/1.1 403 Forbidden!\\r\\n\\r\\n')
            else:
                self.client.send('HTTP/1.1 400 NoXRealHost!\\r\\n\\r\\n')

        except Exception as e:
            self.log += ' - error: ' + str(e)
            self.server.printLog(self.log)
        finally:
            self.close()
            self.server.removeConn(self)

    def findHeader(self, head, header):
        aux = head.find(header + ': ')
    
        if aux == -1:
            return ''

        aux = head.find(':', aux)
        head = head[aux+2:]
        aux = head.find('\\r\\n')

        if aux == -1:
            return ''

        return head[:aux];

    def connect_target(self, host):
        i = host.find(':')
        if i != -1:
            port = int(host[i+1:])
            host = host[:i]
        else:
            port = 80

        (soc_family, soc_type, proto, _, address) = socket.getaddrinfo(host, port)[0]
        self.target = socket.socket(soc_family, soc_type, proto)
        self.targetClosed = False
        self.target.connect(address)

    def method_CONNECT(self, path):
        self.log += ' - CONNECT ' + path
        
        self.connect_target(path)
        self.client.sendall(RESPONSE)
        self.client_buffer = ''

        self.server.printLog(self.log)
        self.doCONNECT()

    def doCONNECT(self):
        socs = [self.client, self.target]
        count = 0
        error = False
        while True:
            count += 1
            (recv, _, err) = select.select(socs, [], socs, 3)
            if err:
                error = True
            if recv:
                for in_ in recv:
                    try:
                        data = in_.recv(BUFLEN)
                        if data:
                            if in_ is self.target:
                                self.client.send(data)
                            else:
                                while data:
                                    byte = self.target.send(data)
                                    data = data[byte:]
                            count = 0
                        else:
                            break
                    except:
                        error = True
                        break
            if count == TIMEOUT:
                error = True

            if error:
                break


def main():
    print "\\n=============================="
    print "      PYTHON PROXY"
    print "=============================="
    print "IP: " + LISTENING_ADDR
    print "Puerto: " + str(LISTENING_PORT)
    print "Iniciado correctamente\\n"
    
    server = Server(LISTENING_ADDR, LISTENING_PORT)
    server.start()

    while True:
        try:
            time.sleep(2)
        except KeyboardInterrupt:
            print 'Deteniendo...'
            server.close()
            break

if __name__ == '__main__':
    main()
"""

        # Guardar script
        with open('/root/proxy.py', 'w') as f:
            f.write(proxy_script)
        
        subprocess.run(['chmod', '+x', '/root/proxy.py'])

        # Iniciar proxy en screen con Python 2
        print(f" {Color.YELLOW}Iniciando proxy en segundo plano...{Color.END}")
        subprocess.run(['screen', '-wipe'], stderr=subprocess.DEVNULL)
        subprocess.run(['screen', '-dmS', 'pythonwe', 'python2', '/root/proxy.py'])

        import time
        time.sleep(2)

        # Verificar si inició
        result = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        if 'pythonwe' in result.stdout:
            print(f" {Color.GREEN}✓ Proxy iniciado en screen{Color.END}")
        else:
            print(f" {Color.RED}⚠ Proxy pudo no iniciar correctamente{Color.END}")

        # Abrir puerto
        subprocess.run(['iptables', '-I', 'INPUT', '-p', 'tcp', '--dport', port, '-j', 'ACCEPT'])
        subprocess.run(['ufw', 'allow', port], stderr=subprocess.DEVNULL)

        # Configurar forwarding
        print(f" {Color.YELLOW}Configurando forwarding...{Color.END}")
        configure_forwarding()
        print(f" {Color.GREEN}✓ Forwarding configurado{Color.END}")

        # Guardar en config
        with open(PROTOCOLS_FILE, 'r') as f:
            protocols = json.load(f)

        protocols['proxy']['enabled'] = True
        protocols['proxy']['port'] = int(port)

        with open(PROTOCOLS_FILE, 'w') as f:
            json.dump(protocols, f, indent=4)

        print(f"\n {Color.GREEN}✓ Proxy Python instalado en puerto {port}{Color.END}")
        print(f" {Color.YELLOW}Para ver logs: screen -r pythonwe{Color.END}")
        log_action("admin", f"Proxy Python configurado en puerto {port}")

    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()

    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def stop_proxy():
    """Detener Proxy Python"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}DETENER PROXY PYTHON{Color.END}")
    print_line()
    
    try:
        # Mostrar proxies activos
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        proxy_processes = []
        
        for line in result.stdout.split('\n'):
            if 'proxy.py' in line or 'pythonwe' in line:
                if 'grep' not in line:
                    # Extraer puerto del proceso
                    import re
                    match = re.search(r'proxy\.py\s+(\d+)', line)
                    if match:
                        port = match.group(1)
                    else:
                        # Verificar en netstat
                        net_result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
                        for net_line in net_result.stdout.split('\n'):
                            if 'python' in net_line:
                                port_match = re.search(r':(\d+)\s', net_line)
                                if port_match:
                                    port = port_match.group(1)
                                    break
                        else:
                            port = "desconocido"
                    
                    pid = line.split()[1]
                    proxy_processes.append({'pid': pid, 'port': port, 'line': line})
        
        if not proxy_processes:
            print(f"\n {Color.YELLOW}No hay proxies Python activos{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        # Mostrar proxies encontrados
        print(f"\n {Color.YELLOW}Proxies Python activos:{Color.END}")
        unique_ports = {}
        for proc in proxy_processes:
            if proc['port'] not in unique_ports:
                unique_ports[proc['port']] = proc['pid']
        
        ports_list = list(unique_ports.keys())
        for i, port in enumerate(ports_list, 1):
            pid = unique_ports[port]
            print(f" {Color.GREEN}[{i}]{Color.END} Puerto {port} (PID: {pid})")
        
        print(f"\n {Color.GREEN}[0]{Color.END} Detener TODOS los proxies")
        print(f" {Color.RED}[X]{Color.END} Cancelar")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Selecciona opción: ").strip()
        
        if choice.upper() == 'X':
            return
        
        if choice == '0':
            # Detener todos
            confirm = input(f"\n {Color.YELLOW}¿Detener TODOS los proxies? (s/n): {Color.END}").strip().lower()
            if confirm != 's':
                return
            
            subprocess.run(['pkill', '-f', 'pythonwe'], stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'proxy.py'], stderr=subprocess.DEVNULL)
            subprocess.run(['screen', '-S', 'pythonwe', '-X', 'quit'], stderr=subprocess.DEVNULL)
            
            # Limpiar config
            with open(PROTOCOLS_FILE, 'r') as f:
                protocols = json.load(f)
            
            protocols['proxy']['enabled'] = False
            
            with open(PROTOCOLS_FILE, 'w') as f:
                json.dump(protocols, f, indent=4)
            
            print(f"\n {Color.GREEN}✓ Todos los proxies detenidos{Color.END}")
            log_action("admin", "Todos los proxies detenidos")
            
        else:
            # Detener proxy específico
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(ports_list):
                    port = ports_list[idx]
                    pid = unique_ports[port]
                    
                    # Matar proceso específico
                    subprocess.run(['kill', '-9', pid], stderr=subprocess.DEVNULL)
                    
                    # Cerrar puerto en firewall
                    subprocess.run(['iptables', '-D', 'INPUT', '-p', 'tcp', '--dport', port, '-j', 'ACCEPT'], stderr=subprocess.DEVNULL)
                    
                    print(f"\n {Color.GREEN}✓ Proxy en puerto {port} detenido{Color.END}")
                    log_action("admin", f"Proxy puerto {port} detenido")
                else:
                    print(f" {Color.RED}✗ Opción inválida{Color.END}")
            except ValueError:
                print(f" {Color.RED}✗ Opción inválida{Color.END}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
    
def install_badvpn():
    """Instalar BadVPN-UDP Gateway"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INSTALANDO BADVPN{Color.END}")
    print_line()
    
    port = input(f"\n {Color.GREEN}Puerto para BadVPN (default 7300): {Color.END}").strip()
    if not port:
        port = "7300"
    
    print(f"\n {Color.YELLOW}Instalando BadVPN en puerto {port}...{Color.END}")
    
    try:
        # Verificar si ya está instalado
        badvpn_installed = subprocess.run(['which', 'badvpn-udpgw'], capture_output=True).returncode == 0
        
        if not badvpn_installed:
            print(f" {Color.YELLOW}Instalando dependencias...{Color.END}")
            subprocess.run(['apt-get', 'update'], stdout=subprocess.DEVNULL)
            subprocess.run(['apt-get', 'install', '-y', 'cmake', 'screen', 'wget', 'gcc', 'build-essential', 'g++', 'make'], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Descargar BadVPN
            print(f" {Color.YELLOW}Descargando BadVPN...{Color.END}")
            subprocess.run(['wget', '-O', '/tmp/badvpn.tar.bz2',
                          'https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/badvpn/badvpn-1.999.128.tar.bz2'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Extraer
            subprocess.run(['tar', 'xf', '/tmp/badvpn.tar.bz2', '-C', '/tmp/'], stderr=subprocess.DEVNULL)
            
            # Compilar
            print(f" {Color.YELLOW}Compilando BadVPN (puede tardar)...{Color.END}")
            subprocess.run(['cmake', '/tmp/badvpn-1.999.128', 
                          '-DBUILD_NOTHING_BY_DEFAULT=1', '-DBUILD_UDPGW=1'],
                         cwd='/tmp/badvpn-1.999.128',
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            subprocess.run(['make', 'install'], 
                         cwd='/tmp/badvpn-1.999.128',
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Limpiar
            subprocess.run(['rm', '-rf', '/tmp/badvpn-1.999.128', '/tmp/badvpn.tar.bz2'], stderr=subprocess.DEVNULL)
            
            print(f" {Color.GREEN}✓ BadVPN compilado e instalado{Color.END}")
        else:
            print(f" {Color.GREEN}✓ BadVPN ya está instalado{Color.END}")
        
        # Verificar si el puerto está en uso
        result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
        if result.stdout.strip():
            print(f" {Color.YELLOW}⚠ Puerto {port} ya está en uso por BadVPN{Color.END}")
            confirm = input(f" {Color.YELLOW}¿Usar este puerto de todas formas? (s/n): {Color.END}").strip().lower()
            if confirm != 's':
                input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                return
        
        # Iniciar BadVPN
        print(f" {Color.YELLOW}Iniciando BadVPN en puerto {port}...{Color.END}")
        
        # Detener instancia anterior del mismo puerto si existe
        subprocess.run(['pkill', '-f', f'badvpn-udpgw.*{port}'], stderr=subprocess.DEVNULL)
        
        # Iniciar en screen
        screen_name = f'badvpn_{port}'
        subprocess.run(['screen', '-dmS', screen_name, 
                       'badvpn-udpgw', '--listen-addr', f'127.0.0.1:{port}'])
        
        import time
        time.sleep(2)
        
        # Verificar que inició
        result = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        if screen_name in result.stdout:
            print(f" {Color.GREEN}✓ BadVPN iniciado en screen ({screen_name}){Color.END}")
        
        # Verificar puerto
        result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
        if f'127.0.0.1:{port}' in result.stdout:
            print(f" {Color.GREEN}✓ Puerto {port} escuchando correctamente{Color.END}")
        
        # Guardar en autostart
        autostart_line = f"screen -dmS {screen_name} badvpn-udpgw --listen-addr 127.0.0.1:{port}"
        
        if not os.path.exists('/etc/autostart'):
            with open('/etc/autostart', 'w') as f:
                f.write('#!/bin/bash\n')
            subprocess.run(['chmod', '+x', '/etc/autostart'])
        
        with open('/etc/autostart', 'r') as f:
            autostart_content = f.read()
        
        if autostart_line not in autostart_content:
            with open('/etc/autostart', 'a') as f:
                f.write(f"\n{autostart_line}\n")
        
        # Guardar en config
        with open(PROTOCOLS_FILE, 'r') as f:
            protocols = json.load(f)

        if 'badvpn' not in protocols:
            protocols['badvpn'] = {'enabled': False, 'ports': []}

        # Asegurar que 'ports' existe
        if 'ports' not in protocols['badvpn']:
            protocols['badvpn']['ports'] = []

        if int(port) not in protocols['badvpn']['ports']:
            protocols['badvpn']['ports'].append(int(port))

        protocols['badvpn']['enabled'] = True

        with open(PROTOCOLS_FILE, 'w') as f:
            json.dump(protocols, f, indent=4)

        print(f"\n {Color.GREEN}✓ BadVPN instalado en puerto {port}{Color.END}")
        print(f" {Color.CYAN}Para llamadas y juegos UDP{Color.END}")
        log_action("admin", f"BadVPN instalado en puerto {port}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")


def stop_badvpn():
    """Detener BadVPN"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}DETENER BADVPN{Color.END}")
    print_line()
    
    try:
        # Buscar instancias de BadVPN
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        badvpn_instances = []
        
        for line in result.stdout.split('\n'):
            if 'badvpn-udpgw' in line and 'grep' not in line:
                import re
                match = re.search(r'127\.0\.0\.1:(\d+)', line)
                if match:
                    port = match.group(1)
                    pid = line.split()[1]
                    badvpn_instances.append({'port': port, 'pid': pid})
        
        if not badvpn_instances:
            print(f"\n {Color.YELLOW}No hay instancias de BadVPN activas{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        print(f"\n {Color.YELLOW}Instancias de BadVPN activas:{Color.END}")
        for i, instance in enumerate(badvpn_instances, 1):
            print(f" {Color.GREEN}[{i}]{Color.END} Puerto {instance['port']} (PID: {instance['pid']})")
        
        print(f"\n {Color.GREEN}[0]{Color.END} Detener TODAS las instancias")
        print(f" {Color.RED}[X]{Color.END} Cancelar")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Selecciona opción: ").strip()
        
        if choice.upper() == 'X':
            return
        
        if choice == '0':
            # Detener todas
            confirm = input(f"\n {Color.YELLOW}¿Detener TODAS las instancias de BadVPN? (s/n): {Color.END}").strip().lower()
            if confirm != 's':
                return
            
            subprocess.run(['pkill', '-f', 'badvpn-udpgw'], stderr=subprocess.DEVNULL)
            
            # Limpiar screens
            result = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'badvpn_' in line:
                    screen_name = line.split('.')[1].split('\t')[0]
                    subprocess.run(['screen', '-S', screen_name, '-X', 'quit'], stderr=subprocess.DEVNULL)
            
            # Limpiar config
            with open(PROTOCOLS_FILE, 'r') as f:
                protocols = json.load(f)
            
            protocols['badvpn']['enabled'] = False
            protocols['badvpn']['ports'] = []
            
            with open(PROTOCOLS_FILE, 'w') as f:
                json.dump(protocols, f, indent=4)
            
            print(f"\n {Color.GREEN}✓ Todas las instancias de BadVPN detenidas{Color.END}")
            log_action("admin", "Todas las instancias de BadVPN detenidas")
            
        else:
            # Detener instancia específica
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(badvpn_instances):
                    port = badvpn_instances[idx]['port']
                    pid = badvpn_instances[idx]['pid']
                    
                    # Matar proceso
                    subprocess.run(['kill', '-9', pid], stderr=subprocess.DEVNULL)
                    
                    # Detener screen
                    subprocess.run(['screen', '-S', f'badvpn_{port}', '-X', 'quit'], stderr=subprocess.DEVNULL)
                    
                    # Actualizar config
                    with open(PROTOCOLS_FILE, 'r') as f:
                        protocols = json.load(f)
                    
                    if 'badvpn' in protocols and int(port) in protocols['badvpn']['ports']:
                        protocols['badvpn']['ports'].remove(int(port))
                        
                        if not protocols['badvpn']['ports']:
                            protocols['badvpn']['enabled'] = False
                        
                        with open(PROTOCOLS_FILE, 'w') as f:
                            json.dump(protocols, f, indent=4)
                    
                    print(f"\n {Color.GREEN}✓ BadVPN en puerto {port} detenido{Color.END}")
                    log_action("admin", f"BadVPN puerto {port} detenido")
                else:
                    print(f" {Color.RED}✗ Opción inválida{Color.END}")
            except ValueError:
                print(f" {Color.RED}✗ Opción inválida{Color.END}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")


def menu_badvpn():
    """Menú de BadVPN"""
    while True:
        clear_screen()
        print_banner()
        print_line()
        print(f" {Color.CYAN}BADVPN - UDP GATEWAY{Color.END}")
        print_line()
        
        # Mostrar instancias activas
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            ports_active = []
            
            for line in result.stdout.split('\n'):
                if 'badvpn-udpgw' in line and 'grep' not in line:
                    import re
                    match = re.search(r'127\.0\.0\.1:(\d+)', line)
                    if match:
                        ports_active.append(match.group(1))
            
            if ports_active:
                print(f" {Color.GREEN}Puertos activos: {', '.join(ports_active)}{Color.END}")
            else:
                print(f" {Color.YELLOW}No hay instancias activas{Color.END}")
            
            print_line()
        except:
            pass
        
        print(f" {Color.GREEN}[1]{Color.END} ➮ Instalar/Agregar BadVPN")
        print(f" {Color.GREEN}[2]{Color.END} ➮ Detener BadVPN")
        print_line()
        print(f" {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}Volver{Color.END}")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
        
        if choice == '1':
            install_badvpn()
        elif choice == '2':
            stop_badvpn()
        elif choice == '0':
            break

def menu_v2ray():
    """Menú de V2Ray/3X-UI"""
    while True:
        clear_screen()
        print_banner()
        print_line()
        print(f" {Color.CYAN}V2RAY / 3X-UI PANEL{Color.END}")
        print_line()
        
        # Verificar si está instalado
        v2ray_installed = subprocess.run(['which', 'x-ui'], capture_output=True).returncode == 0
        
        if v2ray_installed:
            # Verificar estado del servicio
            result = subprocess.run(['systemctl', 'is-active', 'x-ui'], capture_output=True, text=True)
            if 'active' in result.stdout:
                status = f"{Color.GREEN}ACTIVO ✓{Color.END}"
            else:
                status = f"{Color.YELLOW}INACTIVO{Color.END}"
            
            # Verificar puerto
            result_port = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
            if ':54321' in result_port.stdout:
                port_status = f"{Color.GREEN}54321 ✓{Color.END}"
            else:
                port_status = f"{Color.YELLOW}54321{Color.END}"
            
            print(f" {Color.CYAN}∘{Color.END} Estado: {status}")
            print(f" {Color.CYAN}∘{Color.END} Puerto: {port_status}")
            
            # Mostrar IP de acceso
            try:
                ip = subprocess.check_output(['curl', '-s', 'ifconfig.me'], timeout=3).decode().strip()
                print(f" {Color.CYAN}∘{Color.END} Acceso: {Color.GREEN}http://{ip}:54321{Color.END}")
            except:
                pass
            
            print_line()
            print(f" {Color.GREEN}[1]{Color.END} ➮ Ingresar al menú x-ui")
            print(f" {Color.GREEN}[2]{Color.END} ➮ Reiniciar servicio")
            print(f" {Color.GREEN}[3]{Color.END} ➮ Detener servicio")
            print(f" {Color.GREEN}[4]{Color.END} ➮ Desinstalar 3X-UI")
            
        else:
            print(f" {Color.YELLOW}3X-UI no está instalado{Color.END}")
            print_line()
            print(f" {Color.GREEN}[1]{Color.END} ➮ Instalar 3X-UI")
        
        print_line()
        print(f" {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}Volver{Color.END}")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
        
        if not v2ray_installed:
            # Si NO está instalado
            if choice == '1':
                install_v2ray()
            elif choice == '0':
                break
        else:
            # Si SÍ está instalado
            if choice == '1':
                # Ingresar al menú x-ui
                clear_screen()
                print_banner()
                print_line()
                print(f" {Color.CYAN}Abriendo menú 3X-UI...{Color.END}")
                print_line()
                subprocess.run(['x-ui'])
                input(f"\n {Color.CYAN}Presiona Enter para volver...{Color.END}")
                
            elif choice == '2':
                # Reiniciar
                print(f"\n {Color.YELLOW}Reiniciando 3X-UI...{Color.END}")
                subprocess.run(['x-ui', 'restart'])
                print(f" {Color.GREEN}✓ 3X-UI reiniciado{Color.END}")
                log_action("admin", "3X-UI reiniciado")
                input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                
            elif choice == '3':
                # Detener
                print(f"\n {Color.YELLOW}Deteniendo 3X-UI...{Color.END}")
                subprocess.run(['x-ui', 'stop'])
                print(f" {Color.GREEN}✓ 3X-UI detenido{Color.END}")
                log_action("admin", "3X-UI detenido")
                input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                
            elif choice == '4':
                # Desinstalar
                clear_screen()
                print_banner()
                print_line()
                print(f" {Color.RED}DESINSTALAR 3X-UI{Color.END}")
                print_line()
                
                confirm = input(f"\n {Color.RED}⚠️  ¿Desinstalar completamente 3X-UI? (s/n): {Color.END}").strip().lower()
                if confirm == 's':
                    print(f"\n {Color.YELLOW}Desinstalando 3X-UI...{Color.END}")
                    subprocess.run(['bash', '-c', 'x-ui uninstall'])
                    
                    # Limpiar config
                    try:
                        with open(PROTOCOLS_FILE, 'r') as f:
                            protocols = json.load(f)
                        
                        if 'v2ray' in protocols:
                            protocols['v2ray']['enabled'] = False
                        
                        with open(PROTOCOLS_FILE, 'w') as f:
                            json.dump(protocols, f, indent=4)
                    except:
                        pass
                    
                    print(f"\n {Color.GREEN}✓ 3X-UI desinstalado{Color.END}")
                    log_action("admin", "3X-UI desinstalado")
                else:
                    print(f"\n {Color.YELLOW}Desinstalación cancelada{Color.END}")
                
                input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                
            elif choice == '0':
                break

def install_v2ray():
    """Instalar 3X-UI (V2Ray Panel)"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INSTALANDO 3X-UI (V2RAY PANEL){Color.END}")
    print_line()
    
    print(f"\n {Color.YELLOW}3X-UI es un panel web para gestionar V2Ray/Xray{Color.END}")
    print(f" {Color.YELLOW}Se instalará en el puerto 54321 (por defecto){Color.END}\n")
    
    confirm = input(f" {Color.GREEN}¿Continuar con la instalación? (s/n): {Color.END}").strip().lower()
    if confirm != 's':
        return
    
    try:
        print(f"\n {Color.YELLOW}Descargando e instalando 3X-UI...{Color.END}")
        print(f" {Color.CYAN}Esto puede tardar varios minutos...{Color.END}\n")
        print_line()
        
        # Ejecutar instalación
        result = subprocess.run([
            'bash', '-c',
            'curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh | bash'
        ])
        
        print_line()
        
        if result.returncode == 0:
            print(f"\n {Color.GREEN}✓ 3X-UI instalado correctamente{Color.END}")
            
            # Guardar en config
            try:
                with open(PROTOCOLS_FILE, 'r') as f:
                    protocols = json.load(f)
                
                protocols['v2ray'] = {
                    'enabled': True,
                    'port': 54321,
                    'type': '3x-ui'
                }
                
                with open(PROTOCOLS_FILE, 'w') as f:
                    json.dump(protocols, f, indent=4)
            except:
                pass
            
            print(f"\n {Color.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Color.END}")
            print(f" {Color.YELLOW}Para acceder al panel 3X-UI, ejecuta:{Color.END}")
            print(f" {Color.GREEN}x-ui{Color.END}")
            print(f"\n {Color.YELLOW}O accede vía web:{Color.END}")
            
            # Obtener IP
            try:
                ip = subprocess.check_output(['curl', '-s', 'ifconfig.me']).decode().strip()
                print(f" {Color.GREEN}http://{ip}:54321{Color.END}")
            except:
                print(f" {Color.GREEN}http://TU_IP:54321{Color.END}")
            
            print(f" {Color.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Color.END}")
            
            log_action("admin", "3X-UI instalado")
        else:
            print(f"\n {Color.RED}✗ Error durante la instalación{Color.END}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")


def stop_v2ray():
    """Detener/Desinstalar 3X-UI"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}GESTIONAR 3X-UI{Color.END}")
    print_line()
    
    print(f"\n {Color.YELLOW}Opciones disponibles:{Color.END}")
    print(f" {Color.GREEN}[1]{Color.END} Detener servicio 3X-UI")
    print(f" {Color.GREEN}[2]{Color.END} Reiniciar servicio 3X-UI")
    print(f" {Color.GREEN}[3]{Color.END} Desinstalar 3X-UI")
    print(f" {Color.RED}[0]{Color.END} Volver")
    print_line()
    
    choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
    
    try:
        if choice == '1':
            # Detener
            subprocess.run(['x-ui', 'stop'])
            print(f"\n {Color.GREEN}✓ 3X-UI detenido{Color.END}")
            log_action("admin", "3X-UI detenido")
            
        elif choice == '2':
            # Reiniciar
            subprocess.run(['x-ui', 'restart'])
            print(f"\n {Color.GREEN}✓ 3X-UI reiniciado{Color.END}")
            log_action("admin", "3X-UI reiniciado")
            
        elif choice == '3':
            # Desinstalar
            confirm = input(f"\n {Color.RED}⚠️  ¿Desinstalar completamente 3X-UI? (s/n): {Color.END}").strip().lower()
            if confirm == 's':
                subprocess.run(['bash', '-c', 'x-ui uninstall'])
                
                # Limpiar config
                try:
                    with open(PROTOCOLS_FILE, 'r') as f:
                        protocols = json.load(f)
                    
                    if 'v2ray' in protocols:
                        protocols['v2ray']['enabled'] = False
                    
                    with open(PROTOCOLS_FILE, 'w') as f:
                        json.dump(protocols, f, indent=4)
                except:
                    pass
                
                print(f"\n {Color.GREEN}✓ 3X-UI desinstalado{Color.END}")
                log_action("admin", "3X-UI desinstalado")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
    
    if choice in ['1', '2', '3']:
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")


def menu_v2ray():
    """Menú de V2Ray/3X-UI"""
    while True:
        clear_screen()
        print_banner()
        print_line()
        print(f" {Color.CYAN}V2RAY / 3X-UI PANEL{Color.END}")
        print_line()
        
        # Verificar si está instalado
        v2ray_installed = subprocess.run(['which', 'x-ui'], capture_output=True).returncode == 0
        
        if v2ray_installed:
            # Verificar estado
            result = subprocess.run(['systemctl', 'is-active', 'x-ui'], capture_output=True, text=True)
            if 'active' in result.stdout:
                status = f"{Color.GREEN}ACTIVO{Color.END}"
            else:
                status = f"{Color.YELLOW}INACTIVO{Color.END}"
            
            print(f" Estado: {status}")
            print_line()
        else:
            print(f" {Color.YELLOW}3X-UI no está instalado{Color.END}")
            print_line()
        
        print(f" {Color.GREEN}[1]{Color.END} ➮ Instalar 3X-UI")
        print(f" {Color.GREEN}[2]{Color.END} ➮ Gestionar 3X-UI")
        
        if v2ray_installed:
            print(f" {Color.GREEN}[3]{Color.END} ➮ Acceder al menú x-ui")
        
        print_line()
        print(f" {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}Volver{Color.END}")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
        
        if choice == '1':
            install_v2ray()
        elif choice == '2':
            stop_v2ray()
        elif choice == '3' and v2ray_installed:
            clear_screen()
            print_banner()
            print_line()
            print(f" {Color.CYAN}Abriendo menú 3X-UI...{Color.END}")
            print_line()
            subprocess.run(['x-ui'])
            input(f"\n {Color.CYAN}Presiona Enter para volver...{Color.END}")
        elif choice == '0':
            break
# ==================== EXTRAS ====================

def check_and_free_port(port):
    
    """Verifica y libera un puerto"""
    try:
        # Ver qué proceso usa el puerto
        result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
        pids = result.stdout.strip().split('\n')
        
        if pids and pids[0]:
            print(f" {Color.YELLOW}Puerto {port} en uso. Liberando...{Color.END}")
            for pid in pids:
                if pid:
                    subprocess.run(['kill', '-9', pid], stderr=subprocess.DEVNULL)
            import time
            time.sleep(1)
    except:
        pass

def reset_token_password():
    """Resetear contraseña de tokens"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}RESETEAR CONTRASEÑA DE TOKENS{Color.END}")
    print_line()
    
    new_pass = input(f"\n {Color.GREEN}Nueva contraseña para tokens: {Color.END}").strip()
    
    token_config = load_token_config()
    token_config['token_password'] = new_pass
    save_token_config(token_config)
    
    # Actualizar todos los usuarios token existentes
    users = load_users()
    for username, data in users.items():
        if data.get('type') == 'token':
            users[username]['password'] = token_config['token_password']
    save_users(users)
    
    print(f"\n {Color.GREEN}✓ Contraseña de tokens actualizada{Color.END}")
    print(f" {Color.YELLOW}Todos los usuarios token ahora usan: {new_pass}{Color.END}")
    log_action("admin", "Contraseña de tokens reseteada")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def configure_forwarding():
    """Configura IP forwarding y NAT para Ubuntu (iptables + ufw aware)"""
    import shutil, traceback, time
    try:
        if os.geteuid() != 0:
            raise RuntimeError("Necesitas ejecutar como root.")

        # Habilitar ip_forward inmediatamente
        subprocess.run(['sysctl','-w','net.ipv4.ip_forward=1'], check=False)

        # Hacer permanente (usar /etc/sysctl.d/99-moratech.conf para no tocar sysctl.conf directo)
        conf_path = '/etc/sysctl.d/99-moratech.conf'
        with open(conf_path, 'w') as f:
            f.write('# Habilitado por Moratech\nnet.ipv4.ip_forward=1\n')
        subprocess.run(['sysctl','--system'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Detectar interfaz de salida por default
        route = subprocess.run(['ip','route','show','default'], capture_output=True, text=True)
        ext_if = 'eth0'
        if route.returncode == 0 and route.stdout:
            parts = route.stdout.split()
            if 'dev' in parts:
                idx = parts.index('dev')
                if idx + 1 < len(parts):
                    ext_if = parts[idx+1]

        # Determinar interfaz TUN (tun0 o similar) para reglas FORWARD; no obligatoria si proxy solo usa NAT universal
        tun_if = 'tun0'
        links = subprocess.run(['ip','-o','link','show'], capture_output=True, text=True)
        for line in links.stdout.splitlines():
            name = line.split(':')[1].split('@')[0].strip()
            if name.startswith('tun') or name.startswith('tap') or name.startswith('wg') or name.startswith('vmnet'):
                tun_if = name
                break

        # Reglas iptables:
        # Aceptar conexiones RELATED/ESTABLISHED entrantes desde internet al tun y viceversa
        subprocess.run(['iptables','-A','FORWARD','-i',ext_if,'-o',tun_if,'-m','state','--state','RELATED,ESTABLISHED','-j','ACCEPT'])
        subprocess.run(['iptables','-A','FORWARD','-i',tun_if,'-o',ext_if,'-j','ACCEPT'])
        # MASQUERADE en salida por interfaz externa
        subprocess.run(['iptables','-t','nat','-A','POSTROUTING','-o',ext_if,'-j','MASQUERADE'])

        # Si ufw está activo, ajustar DEFAULT_FORWARD_POLICY y before.rules
        if shutil.which('ufw'):
            ufw_status = subprocess.run(['ufw','status','verbose'], capture_output=True, text=True)
            if 'Status: active' in ufw_status.stdout:
                # Cambiar politica forward a ACCEPT en /etc/default/ufw
                dpath = '/etc/default/ufw'
                if os.path.exists(dpath):
                    with open(dpath,'r') as f:
                        d = f.read()
                    d = d.replace('DEFAULT_FORWARD_POLICY="DROP"','DEFAULT_FORWARD_POLICY="ACCEPT"')
                    with open(dpath,'w') as f:
                        f.write(d)
                # Añadir bloque NAT si no existe en before.rules
                before = '/etc/ufw/before.rules'
                if os.path.exists(before):
                    with open(before,'r') as f:
                        b = f.read()
                    if '*nat' not in b:
                        nat_block = f"\n# NAT table rules (added by Moratech)\n*nat\n:POSTROUTING ACCEPT [0:0]\n-A POSTROUTING -o {ext_if} -j MASQUERADE\nCOMMIT\n"
                        with open(before,'a') as f:
                            f.write(nat_block)
                        # reload ufw
                        subprocess.run(['ufw','disable'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        time.sleep(0.5)
                        subprocess.run(['ufw','enable'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Persistir reglas (iptables-persistent / netfilter-persistent)
        if shutil.which('netfilter-persistent'):
            subprocess.run(['netfilter-persistent','save'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # fallback: iptables-save to /etc/iptables/rules.v4 si existe paquete
            if os.path.exists('/etc/iptables'):
                subprocess.run(['iptables-save'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return True
    except Exception as e:
        print("Error en configure_forwarding:", e)
        traceback.print_exc()
        return False

# ==================== MENÚ PRINCIPAL ====================

def main_menu(username):
    """Menú principal"""
    while True:
        show_dashboard()

        print(f" {Color.GREEN}[01]{Color.END} ➮ CONTROL USUARIOS (SSH/TOKEN)")
        print(f" {Color.GREEN}[02]{Color.END} ➮ INSTALADOR DE PROTOCOLOS")
        print(f" {Color.GREEN}[03]{Color.END} ➮ OPTIMIZAR VPS")
        print(f" {Color.GREEN}[04]{Color.END} ➮ ESTADÍSTICAS Y LOGS")
        print_line()
        print(f" {Color.GREEN}[05]{Color.END} ➮ UPDATE / REMOVE  |  {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}[ SALIR ]{Color.END}")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
        
        if choice == '1' or choice == '01':
            control_usuarios_menu()
        elif choice == '2' or choice == '02':
            protocols_menu()
        elif choice == '3' or choice == '03':
            print(f"\n {Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        elif choice == '4' or choice == '04':
            print(f"\n {Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        elif choice == '5' or choice == '05':
            print(f"\n {Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        elif choice == '0':
            log_action(username, "Logout")
            print(f"\n {Color.GREEN}¡Hasta pronto!{Color.END}\n")
            sys.exit(0)

def main():
    """Función principal"""
    init_system()
    main_menu("admin")


if __name__ == "__main__":
    main()
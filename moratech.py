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

def print_banner():
    """Muestra el banner de Moratech"""
    banner = f"""
{Color.PURPLE}{Color.BOLD}
╔══════════════════════════════════════════════════════════╗
║    ███╗   ███╗ ██████╗ ██████╗  █████╗ ████████╗███████╗║
║    ████╗ ████║██╔═══██╗██╔══██╗██╔══██╗╚══██╔══╝██╔════╝║
║    ██╔████╔██║██║   ██║██████╔╝███████║   ██║   █████╗  ║
║    ██║╚██╔╝██║██║   ██║██╔══██╗██╔══██║   ██║   ██╔══╝  ║
║    ██║ ╚═╝ ██║╚██████╔╝██║  ██║██║  ██║   ██║   ███████╗║
║    ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝║
╚══════════════════════════════════════════════════════════╝
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
        
        # CPUs
        info['cpus'] = subprocess.check_output("nproc", shell=True).decode().strip()
        
        # IP Pública
        try:
            info['ip'] = subprocess.check_output("curl -s ifconfig.me", shell=True, timeout=3).decode().strip()
        except:
            info['ip'] = "No disponible"
        
        # Fecha actual
        info['date'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Hostname
        info['hostname'] = socket.gethostname()
        
    except Exception as e:
        print(f"{Color.RED}Error obteniendo info del sistema: {e}{Color.END}")
    
    return info

def get_active_ports():
    """Obtiene puertos activos"""
    ports = {
        'SSH': '22',
        'SSL': '-',
        'BadVPN': '-',
        'Proxy': '-',
        'V2Ray': '-',
        'SlowDNS': '-'
    }
    
    try:
        # Verificar SSH
        result = subprocess.run(['ss', '-tulpn'], capture_output=True, text=True)
        output = result.stdout
        
        if ':22 ' in output or ':22\n' in output:
            ports['SSH'] = '22 ✓'
        
        # Aquí luego agregaremos verificación de otros puertos
        
    except Exception as e:
        pass
    
    return ports

def init_system():
    """Inicializa el sistema"""
    CONFIG_DIR.mkdir(exist_ok=True)
    
    if not USERS_FILE.exists():
        users = {
            "admin": {
                "password": hashlib.sha256("admin123".encode()).hexdigest(),
                "role": "admin",
                "type": "ssh",
                "created": datetime.now().isoformat(),
                "expires": None,
                "max_connections": 999,
                "enabled": True
            }
        }
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=4)
    
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
    """Guarda usuarios"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

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
    
    print(f"\n{Color.CYAN}╔══════════════════════════════════════════════════════════╗{Color.END}")
    print(f"{Color.CYAN}║              INFORMACIÓN DEL SISTEMA                     ║{Color.END}")
    print(f"{Color.CYAN}╚══════════════════════════════════════════════════════════╝{Color.END}\n")
    
    print(f"{Color.GREEN}SO:{Color.END} {info.get('os', 'N/A')}")
    print(f"{Color.GREEN}CPUs:{Color.END} {info.get('cpus', 'N/A')} cores")
    print(f"{Color.GREEN}IP:{Color.END} {info.get('ip', 'N/A')}")
    print(f"{Color.GREEN}Fecha:{Color.END} {info.get('date', 'N/A')}")
    print(f"{Color.GREEN}Hostname:{Color.END} {info.get('hostname', 'N/A')}")
    
    print(f"\n{Color.CYAN}╔══════════════════════════════════════════════════════════╗{Color.END}")
    print(f"{Color.CYAN}║                 PUERTOS ACTIVOS                          ║{Color.END}")
    print(f"{Color.CYAN}╚══════════════════════════════════════════════════════════╝{Color.END}\n")
    
    for protocol, port in ports.items():
        status = f"{Color.GREEN}{port}{Color.END}" if '✓' in port else f"{Color.YELLOW}{port}{Color.END}"
        print(f"{Color.BLUE}{protocol}:{Color.END} {status}")

def login():
    """Sistema de login"""
    clear_screen()
    print_banner()
    print(f"\n{Color.CYAN}╔═══════════════════════════════════════╗{Color.END}")
    print(f"{Color.CYAN}║          INICIO DE SESIÓN             ║{Color.END}")
    print(f"{Color.CYAN}╚═══════════════════════════════════════╝{Color.END}\n")
    
    users = load_users()
    max_attempts = 3
    
    for attempt in range(max_attempts):
        username = input(f"{Color.GREEN}Usuario: {Color.END}").strip()
        
        # Mostrar contraseña mientras se escribe
        import sys
        password = ""
        print(f"{Color.GREEN}Contraseña: {Color.END}", end='', flush=True)
        
        while True:
            char = sys.stdin.read(1)
            if char == '\n':
                break
            elif char == '\x7f':  # Backspace
                if password:
                    password = password[:-1]
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
            else:
                password += char
                sys.stdout.write(char)
                sys.stdout.flush()
        print()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if username in users and users[username]['password'] == password_hash:
            print(f"\n{Color.GREEN}✓ Login exitoso!{Color.END}")
            log_action(username, "Login exitoso")
            import time
            time.sleep(1)
            return username
        else:
            remaining = max_attempts - attempt - 1
            if remaining > 0:
                print(f"{Color.RED}✗ Credenciales incorrectas. Intentos restantes: {remaining}{Color.END}\n")
    
    return None

# ==================== MENÚ DE USUARIOS ====================

def add_user():
    """Agregar usuario SSH o Token"""
    clear_screen()
    print_banner()
    print(f"\n{Color.CYAN}╔══════════════════════════════════════════════════════════╗{Color.END}")
    print(f"{Color.CYAN}║              AGREGAR USUARIO                             ║{Color.END}")
    print(f"{Color.CYAN}╚══════════════════════════════════════════════════════════╝{Color.END}\n")
    
    print(f"{Color.YELLOW}Tipo de usuario:{Color.END}")
    print(f"{Color.GREEN}1.{Color.END} Usuario SSH")
    print(f"{Color.GREEN}2.{Color.END} Usuario Token")
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
    import sys
    password = ""
    print(f"{Color.GREEN}Contraseña: {Color.END}", end='', flush=True)
    
    while True:
        char = sys.stdin.read(1)
        if char == '\n':
            break
        elif char == '\x7f':
            if password:
                password = password[:-1]
                sys.stdout.write('\b \b')
                sys.stdout.flush()
        else:
            password += char
            sys.stdout.write(char)
            sys.stdout.flush()
    print()
    
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
        "password": hashlib.sha256(password.encode()).hexdigest(),
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
        
        import sys
        token_pass = ""
        print(f"{Color.GREEN}Contraseña maestra para tokens: {Color.END}", end='', flush=True)
        
        while True:
            char = sys.stdin.read(1)
            if char == '\n':
                break
            elif char == '\x7f':
                if token_pass:
                    token_pass = token_pass[:-1]
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
            else:
                token_pass += char
                sys.stdout.write(char)
                sys.stdout.flush()
        print()
        
        token_config['token_password'] = hashlib.sha256(token_pass.encode()).hexdigest()
        save_token_config(token_config)
        print(f"{Color.GREEN}✓ Contraseña configurada{Color.END}\n")
    
    # Token
    token_input = input(f"{Color.GREEN}Ingresa el token: {Color.END}").strip()
    token_username = "token_" + hashlib.sha256(token_input.encode()).hexdigest()[:8]
    
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

def users_menu():
    """Menú de control de usuarios"""
    while True:
        show_dashboard()
        print(f"\n{Color.CYAN}╔══════════════════════════════════════════════════════════╗{Color.END}")
        print(f"{Color.CYAN}║              CONTROL DE USUARIOS                         ║{Color.END}")
        print(f"{Color.CYAN}╚══════════════════════════════════════════════════════════╝{Color.END}\n")
        
        print(f"{Color.GREEN}1.{Color.END} Agregar usuario")
        print(f"{Color.GREEN}2.{Color.END} Borrar usuario")
        print(f"{Color.GREEN}3.{Color.END} Editar/Renovar usuario")
        print(f"{Color.GREEN}4.{Color.END} Mostrar usuarios")
        print(f"{Color.GREEN}9.{Color.END} Backup de usuarios")
        print(f"{Color.GREEN}10.{Color.END} CheckUser Online")
        print(f"{Color.GREEN}11.{Color.END} Bot Telegram")
        print(f"{Color.GREEN}0.{Color.END} Volver al menú principal")
        
        choice = input(f"\n{Color.YELLOW}Selecciona: {Color.END}").strip()
        
        if choice == '1':
            add_user()
        elif choice == '2':
            delete_users_menu()
        elif choice == '3':
            edit_user()
        elif choice == '4':
            show_users()
        elif choice == '9':
            print(f"\n{Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")
        elif choice == '10':
            print(f"\n{Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")
        elif choice == '11':
            print(f"\n{Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")
        elif choice == '0':
            break

# ==================== MENÚ DE PROTOCOLOS ====================

def protocols_menu():
    """Menú de protocolos"""
    while True:
        show_dashboard()
        print(f"\n{Color.CYAN}╔══════════════════════════════════════════════════════════╗{Color.END}")
        print(f"{Color.CYAN}║                  PROTOCOLOS                              ║{Color.END}")
        print(f"{Color.CYAN}╚══════════════════════════════════════════════════════════╝{Color.END}\n")
        
        print(f"{Color.GREEN}1.{Color.END} SSL (Puerto 443)")
        print(f"{Color.GREEN}2.{Color.END} V2Ray")
        print(f"{Color.GREEN}3.{Color.END} SlowDNS")
        print(f"{Color.GREEN}4.{Color.END} Proxy Python (Puerto 80)")
        print(f"{Color.GREEN}5.{Color.END} BadVPN (Puerto 7300)")
        print(f"{Color.GREEN}0.{Color.END} Volver")
        
        choice = input(f"\n{Color.YELLOW}Selecciona: {Color.END}").strip()
        
        if choice == '0':
            break
        else:
            print(f"\n{Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

# ==================== MENÚ PRINCIPAL ====================

def main_menu(username):
    """Menú principal"""
    while True:
        show_dashboard()
        print(f"\n{Color.GREEN}Usuario:{Color.END} {username}")
        print(f"\n{Color.CYAN}╔══════════════════════════════════════════════════════════╗{Color.END}")
        print(f"{Color.CYAN}║                  MENÚ PRINCIPAL                          ║{Color.END}")
        print(f"{Color.CYAN}╚══════════════════════════════════════════════════════════╝{Color.END}\n")
        
        print(f"{Color.GREEN}1.{Color.END} Control de Usuarios")
        print(f"{Color.GREEN}2.{Color.END} Protocolos")
        print(f"{Color.GREEN}0.{Color.END} Salir")
        
        choice = input(f"\n{Color.YELLOW}Selecciona una opción: {Color.END}").strip()
        
        if choice == '1':
            users_menu()
        elif choice == '2':
            protocols_menu()
        elif choice == '0':
            log_action(username, "Logout")
            print(f"\n{Color.GREEN}¡Hasta pronto!{Color.END}\n")
            sys.exit(0)

def main():
    """Función principal"""
    init_system()
    username = login()
    
    if username:
        main_menu(username)
    else:
        sys.exit(1)

if __name__ == "__main__":
    # Configurar terminal para leer caracteres individuales
    import tty
    import termios
    
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        main()
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
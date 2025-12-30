#!/usr/bin/env python3
"""
MORATECH - Panel de Administración en Consola
Sistema completo de gestión para Ubuntu
"""

import os
import sys
import json
import getpass
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

# Colores para terminal
class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# Configuración
CONFIG_DIR = Path.home() / '.moratech'
CONFIG_FILE = CONFIG_DIR / 'config.json'
USERS_FILE = CONFIG_DIR / 'users.json'
LOGS_FILE = CONFIG_DIR / 'logs.json'
SERVICES_FILE = CONFIG_DIR / 'services.json'
TOKEN_CONFIG_FILE = CONFIG_DIR / 'token_config.json'
CONNECTIONS_FILE = CONFIG_DIR / 'connections.json'

def clear_screen():
    """Limpia la pantalla"""
    os.system('clear')

def print_banner():
    """Muestra el banner de Moratech"""
    banner = f"""
{Color.PURPLE}{Color.BOLD}
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║    ███╗   ███╗ ██████╗ ██████╗  █████╗ ████████╗███████╗║
║    ████╗ ████║██╔═══██╗██╔══██╗██╔══██╗╚══██╔══╝██╔════╝║
║    ██╔████╔██║██║   ██║██████╔╝███████║   ██║   █████╗  ║
║    ██║╚██╔╝██║██║   ██║██╔══██╗██╔══██║   ██║   ██╔══╝  ║
║    ██║ ╚═╝ ██║╚██████╔╝██║  ██║██║  ██║   ██║   ███████╗║
║    ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝║
║                                                          ║
║              Panel de Administración v1.0                ║
╚══════════════════════════════════════════════════════════╝
{Color.END}"""
    print(banner)

def init_system():
    """Inicializa el sistema y crea archivos necesarios"""
    CONFIG_DIR.mkdir(exist_ok=True)
    
    if not USERS_FILE.exists():
        users = {
            "admin": {
                "password": hashlib.sha256("admin123".encode()).hexdigest(),
                "role": "superadmin",
                "type": "regular",
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
            "version": "1.0",
            "installed": datetime.now().isoformat()
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    
    if not LOGS_FILE.exists():
        with open(LOGS_FILE, 'w') as f:
            json.dump([], f)
    
    if not SERVICES_FILE.exists():
        with open(SERVICES_FILE, 'w') as f:
            json.dump([], f)
    
    if not TOKEN_CONFIG_FILE.exists():
        with open(TOKEN_CONFIG_FILE, 'w') as f:
            json.dump({"token_password": None}, f)
    
    if not CONNECTIONS_FILE.exists():
        with open(CONNECTIONS_FILE, 'w') as f:
            json.dump({}, f)

def load_users():
    """Carga usuarios del sistema"""
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    """Guarda usuarios en el sistema"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def log_action(user, action):
    """Registra una acción en los logs"""
    with open(LOGS_FILE, 'r') as f:
        logs = json.load(f)
    
    logs.append({
        "user": user,
        "action": action,
        "timestamp": datetime.now().isoformat()
    })
    
    with open(LOGS_FILE, 'w') as f:
        json.dump(logs, f, indent=4)

def load_token_config():
    """Carga configuración de tokens"""
    with open(TOKEN_CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_token_config(config):
    """Guarda configuración de tokens"""
    with open(TOKEN_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def check_user_expired(user_data):
    """Verifica si un usuario está expirado"""
    if user_data.get('expires'):
        expire_date = datetime.fromisoformat(user_data['expires'])
        if datetime.now() > expire_date:
            return True
    return False

def check_max_connections(username, user_data):
    """Verifica si el usuario puede conectarse (no excede máx conexiones)"""
    with open(CONNECTIONS_FILE, 'r') as f:
        connections = json.load(f)
    
    current_connections = connections.get(username, 0)
    max_connections = user_data.get('max_connections', 1)
    
    return current_connections < max_connections

def add_connection(username):
    """Registra una nueva conexión"""
    with open(CONNECTIONS_FILE, 'r') as f:
        connections = json.load(f)
    
    connections[username] = connections.get(username, 0) + 1
    
    with open(CONNECTIONS_FILE, 'w') as f:
        json.dump(connections, f, indent=4)

def remove_connection(username):
    """Elimina una conexión al cerrar sesión"""
    with open(CONNECTIONS_FILE, 'r') as f:
        connections = json.load(f)
    
    if username in connections and connections[username] > 0:
        connections[username] -= 1
    
    with open(CONNECTIONS_FILE, 'w') as f:
        json.dump(connections, f, indent=4)

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
        password = getpass.getpass(f"{Color.GREEN}Contraseña: {Color.END}")
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if username in users and users[username]['password'] == password_hash:
            user_data = users[username]
            
            # Verificar si está habilitado
            if not user_data.get('enabled', True):
                print(f"\n{Color.RED}✗ Usuario deshabilitado{Color.END}")
                log_action(username, "Login fallido - usuario deshabilitado")
                input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")
                return None, None
            
            # Verificar expiración
            if check_user_expired(user_data):
                print(f"\n{Color.RED}✗ Usuario expirado{Color.END}")
                log_action(username, "Login fallido - usuario expirado")
                input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")
                return None, None
            
            # Verificar conexiones máximas
            if not check_max_connections(username, user_data):
                print(f"\n{Color.RED}✗ Máximo de conexiones alcanzado{Color.END}")
                log_action(username, "Login fallido - máx conexiones")
                input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")
                return None, None
            
            # Login exitoso
            add_connection(username)
            print(f"\n{Color.GREEN}✓ Login exitoso!{Color.END}")
            log_action(username, "Login exitoso")
            
            # Mostrar info del usuario
            if user_data.get('expires'):
                expire_date = datetime.fromisoformat(user_data['expires']).strftime("%Y-%m-%d")
                print(f"{Color.YELLOW}Tu cuenta expira el: {expire_date}{Color.END}")
            
            import time
            time.sleep(1)
            return username, users[username]['role']
        else:
            remaining = max_attempts - attempt - 1
            if remaining > 0:
                print(f"{Color.RED}✗ Credenciales incorrectas. Intentos restantes: {remaining}{Color.END}\n")
            else:
                print(f"{Color.RED}✗ Acceso denegado. Demasiados intentos fallidos.{Color.END}")
                log_action(username if username else "unknown", "Login fallido - demasiados intentos")
    
    return None, None

def show_system_info():
    """Muestra información del sistema"""
    clear_screen()
    print_banner()
    print(f"\n{Color.CYAN}═══════════════════════════════════════════════════════════{Color.END}")
    print(f"{Color.CYAN}{Color.BOLD}               INFORMACIÓN DEL SISTEMA{Color.END}")
    print(f"{Color.CYAN}═══════════════════════════════════════════════════════════{Color.END}\n")
    
    # Información del sistema
    try:
        hostname = subprocess.check_output(['hostname']).decode().strip()
        uptime = subprocess.check_output(['uptime', '-p']).decode().strip()
        memory = subprocess.check_output(['free', '-h']).decode()
        disk = subprocess.check_output(['df', '-h', '/']).decode()
        
        print(f"{Color.GREEN}Hostname:{Color.END} {hostname}")
        print(f"{Color.GREEN}Uptime:{Color.END} {uptime}")
        print(f"\n{Color.YELLOW}Memoria:{Color.END}")
        print(memory)
        print(f"\n{Color.YELLOW}Disco:{Color.END}")
        print(disk)
    except Exception as e:
        print(f"{Color.RED}Error al obtener información: {e}{Color.END}")
    
    input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")

def manage_users(current_user):
    """Gestión de usuarios"""
    while True:
        clear_screen()
        print_banner()
        print(f"\n{Color.CYAN}═══════════════════════════════════════════════════════════{Color.END}")
        print(f"{Color.CYAN}{Color.BOLD}                 GESTIÓN DE USUARIOS{Color.END}")
        print(f"{Color.CYAN}═══════════════════════════════════════════════════════════{Color.END}\n")
        
        users = load_users()
        
        print(f"{Color.YELLOW}Usuarios registrados:{Color.END}\n")
        for i, (username, data) in enumerate(users.items(), 1):
            user_type = data.get('type', 'regular')
            expires = data.get('expires')
            max_conn = data.get('max_connections', 'N/A')
            enabled = "✓" if data.get('enabled', True) else "✗"
            
            expire_str = ""
            if expires:
                expire_date = datetime.fromisoformat(expires)
                if datetime.now() > expire_date:
                    expire_str = f" - {Color.RED}EXPIRADO{Color.END}"
                else:
                    days_left = (expire_date - datetime.now()).days
                    expire_str = f" - {days_left} días restantes"
            
            print(f"{Color.GREEN}{i}.{Color.END} {enabled} {username} ({user_type}) - Rol: {data['role']} - Max Conn: {max_conn}{expire_str}")
        
        print(f"\n{Color.CYAN}Opciones:{Color.END}")
        print(f"{Color.GREEN}1.{Color.END} Crear nuevo usuario")
        print(f"{Color.GREEN}2.{Color.END} Eliminar usuario")
        print(f"{Color.GREEN}3.{Color.END} Cambiar contraseña")
        print(f"{Color.GREEN}4.{Color.END} Habilitar/Deshabilitar usuario")
        print(f"{Color.GREEN}5.{Color.END} Configurar contraseña de Token")
        print(f"{Color.GREEN}6.{Color.END} Volver al menú principal")
        
        choice = input(f"\n{Color.YELLOW}Selecciona una opción: {Color.END}").strip()
        
        if choice == '1':
            # Crear usuario
            clear_screen()
            print_banner()
            print(f"\n{Color.CYAN}═══════════════════════════════════════════════════════════{Color.END}")
            print(f"{Color.CYAN}{Color.BOLD}                CREAR NUEVO USUARIO{Color.END}")
            print(f"{Color.CYAN}═══════════════════════════════════════════════════════════{Color.END}\n")
            
            print(f"{Color.YELLOW}Tipo de usuario:{Color.END}")
            print(f"{Color.GREEN}1.{Color.END} Usuario Regular")
            print(f"{Color.GREEN}2.{Color.END} Usuario Token")
            
            user_type_choice = input(f"\n{Color.YELLOW}Selecciona el tipo: {Color.END}").strip()
            
            if user_type_choice == '1':
                # USUARIO REGULAR
                new_user = input(f"\n{Color.GREEN}Nombre de usuario: {Color.END}").strip()
                
                if new_user in users:
                    print(f"{Color.RED}✗ El usuario ya existe{Color.END}")
                    input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")
                    continue
                
                new_pass = getpass.getpass(f"{Color.GREEN}Contraseña: {Color.END}")
                
                # Días de expiración
                days = input(f"{Color.GREEN}Días de duración (0 = sin expiración): {Color.END}").strip()
                try:
                    days = int(days)
                    if days > 0:
                        expires = (datetime.now() + __import__('datetime').timedelta(days=days)).isoformat()
                    else:
                        expires = None
                except ValueError:
                    print(f"{Color.RED}✗ Valor inválido, sin expiración{Color.END}")
                    expires = None
                
                # Máximas conexiones
                max_conn = input(f"{Color.GREEN}Máximas conexiones simultáneas: {Color.END}").strip()
                try:
                    max_conn = int(max_conn)
                except ValueError:
                    max_conn = 1
                
                users[new_user] = {
                    "password": hashlib.sha256(new_pass.encode()).hexdigest(),
                    "role": "user",
                    "type": "regular",
                    "created": datetime.now().isoformat(),
                    "expires": expires,
                    "max_connections": max_conn,
                    "enabled": True
                }
                save_users(users)
                log_action(current_user, f"Usuario regular creado: {new_user}")
                print(f"\n{Color.GREEN}✓ Usuario regular creado exitosamente{Color.END}")
                input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")
            
            elif user_type_choice == '2':
                # USUARIO TOKEN
                token_config = load_token_config()
                
                # Verificar si existe contraseña de token
                if not token_config.get('token_password'):
                    print(f"\n{Color.YELLOW}No hay contraseña configurada para tokens.{Color.END}")
                    print(f"{Color.YELLOW}Por favor, configura una contraseña maestra para tokens.{Color.END}\n")
                    
                    token_master_pass = getpass.getpass(f"{Color.GREEN}Contraseña maestra para tokens: {Color.END}")
                    token_confirm = getpass.getpass(f"{Color.GREEN}Confirmar contraseña: {Color.END}")
                    
                    if token_master_pass == token_confirm:
                        token_config['token_password'] = hashlib.sha256(token_master_pass.encode()).hexdigest()
                        save_token_config(token_config)
                        print(f"\n{Color.GREEN}✓ Contraseña de token configurada{Color.END}\n")
                    else:
                        print(f"\n{Color.RED}✗ Las contraseñas no coinciden{Color.END}")
                        input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")
                        continue
                
                # Solicitar token
                token_input = input(f"\n{Color.GREEN}Ingresa el token: {Color.END}").strip()
                
                # Generar nombre de usuario basado en token (últimos 8 caracteres del hash)
                token_username = "token_" + hashlib.sha256(token_input.encode()).hexdigest()[:8]
                
                if token_username in users:
                    print(f"{Color.RED}✗ Este token ya fue usado{Color.END}")
                    input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")
                    continue
                
                # Días de expiración
                days = input(f"{Color.GREEN}Días de duración: {Color.END}").strip()
                try:
                    days = int(days)
                    expires = (datetime.now() + __import__('datetime').timedelta(days=days)).isoformat()
                except ValueError:
                    print(f"{Color.RED}✗ Valor inválido{Color.END}")
                    input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")
                    continue
                
                # Crear usuario token
                users[token_username] = {
                    "password": token_config['token_password'],
                    "role": "user",
                    "type": "token",
                    "created": datetime.now().isoformat(),
                    "expires": expires,
                    "max_connections": 1,  # Siempre 1 para tokens
                    "enabled": True,
                    "original_token": token_input
                }
                save_users(users)
                log_action(current_user, f"Usuario token creado: {token_username}")
                print(f"\n{Color.GREEN}✓ Usuario token creado exitosamente{Color.END}")
                print(f"{Color.YELLOW}Username: {token_username}{Color.END}")
                input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")
            
        elif choice == '2':
            # Eliminar usuario
            user_to_delete = input(f"\n{Color.GREEN}Usuario a eliminar: {Color.END}").strip()
            if user_to_delete == current_user:
                print(f"{Color.RED}✗ No puedes eliminar tu propio usuario{Color.END}")
            elif user_to_delete in users:
                del users[user_to_delete]
                save_users(users)
                log_action(current_user, f"Usuario eliminado: {user_to_delete}")
                print(f"{Color.GREEN}✓ Usuario eliminado{Color.END}")
            else:
                print(f"{Color.RED}✗ Usuario no encontrado{Color.END}")
            input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")
            
        elif choice == '3':
            # Cambiar contraseña
            user_to_change = input(f"\n{Color.GREEN}Usuario: {Color.END}").strip()
            if user_to_change in users:
                if users[user_to_change].get('type') == 'token':
                    print(f"{Color.RED}✗ No se puede cambiar contraseña de usuarios token{Color.END}")
                else:
                    new_pass = getpass.getpass(f"{Color.GREEN}Nueva contraseña: {Color.END}")
                    users[user_to_change]['password'] = hashlib.sha256(new_pass.encode()).hexdigest()
                    save_users(users)
                    log_action(current_user, f"Contraseña cambiada para: {user_to_change}")
                    print(f"{Color.GREEN}✓ Contraseña actualizada{Color.END}")
            else:
                print(f"{Color.RED}✗ Usuario no encontrado{Color.END}")
            input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")
        
        elif choice == '4':
            # Habilitar/Deshabilitar usuario
            user_to_toggle = input(f"\n{Color.GREEN}Usuario: {Color.END}").strip()
            if user_to_toggle in users:
                current_status = users[user_to_toggle].get('enabled', True)
                users[user_to_toggle]['enabled'] = not current_status
                save_users(users)
                status_text = "habilitado" if users[user_to_toggle]['enabled'] else "deshabilitado"
                log_action(current_user, f"Usuario {status_text}: {user_to_toggle}")
                print(f"{Color.GREEN}✓ Usuario {status_text}{Color.END}")
            else:
                print(f"{Color.RED}✗ Usuario no encontrado{Color.END}")
            input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")
        
        elif choice == '5':
            # Configurar contraseña de token
            token_config = load_token_config()
            
            if token_config.get('token_password'):
                print(f"\n{Color.YELLOW}Ya existe una contraseña configurada.{Color.END}")
                confirm = input(f"{Color.RED}¿Deseas cambiarla? (s/n): {Color.END}").strip().lower()
                if confirm != 's':
                    continue
            
            new_token_pass = getpass.getpass(f"\n{Color.GREEN}Nueva contraseña maestra para tokens: {Color.END}")
            confirm_pass = getpass.getpass(f"{Color.GREEN}Confirmar contraseña: {Color.END}")
            
            if new_token_pass == confirm_pass:
                token_config['token_password'] = hashlib.sha256(new_token_pass.encode()).hexdigest()
                save_token_config(token_config)
                log_action(current_user, "Contraseña de token actualizada")
                print(f"\n{Color.GREEN}✓ Contraseña de token actualizada{Color.END}")
            else:
                print(f"\n{Color.RED}✗ Las contraseñas no coinciden{Color.END}")
            input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")
            
        elif choice == '6':
            break

def view_logs():
    """Ver logs del sistema"""
    clear_screen()
    print_banner()
    print(f"\n{Color.CYAN}═══════════════════════════════════════════════════════════{Color.END}")
    print(f"{Color.CYAN}{Color.BOLD}                  LOGS DEL SISTEMA{Color.END}")
    print(f"{Color.CYAN}═══════════════════════════════════════════════════════════{Color.END}\n")
    
    with open(LOGS_FILE, 'r') as f:
        logs = json.load(f)
    
    if not logs:
        print(f"{Color.YELLOW}No hay logs disponibles{Color.END}")
    else:
        # Mostrar últimos 20 logs
        for log in logs[-20:]:
            timestamp = datetime.fromisoformat(log['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
            print(f"{Color.GREEN}[{timestamp}]{Color.END} {Color.YELLOW}{log['user']}{Color.END} - {log['action']}")
    
    input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")

def manage_services():
    """Gestión de servicios"""
    clear_screen()
    print_banner()
    print(f"\n{Color.CYAN}═══════════════════════════════════════════════════════════{Color.END}")
    print(f"{Color.CYAN}{Color.BOLD}                GESTIÓN DE SERVICIOS{Color.END}")
    print(f"{Color.CYAN}═══════════════════════════════════════════════════════════{Color.END}\n")
    
    services = ['nginx', 'apache2', 'mysql', 'postgresql', 'ssh', 'docker']
    
    for i, service in enumerate(services, 1):
        try:
            status = subprocess.check_output(['systemctl', 'is-active', service], stderr=subprocess.DEVNULL).decode().strip()
            if status == 'active':
                print(f"{Color.GREEN}{i}. {service}: ● ACTIVO{Color.END}")
            else:
                print(f"{Color.RED}{i}. {service}: ○ INACTIVO{Color.END}")
        except:
            print(f"{Color.YELLOW}{i}. {service}: ? NO INSTALADO{Color.END}")
    
    input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")

def view_connections():
    """Ver conexiones activas"""
    clear_screen()
    print_banner()
    print(f"\n{Color.CYAN}═══════════════════════════════════════════════════════════{Color.END}")
    print(f"{Color.CYAN}{Color.BOLD}               CONEXIONES ACTIVAS{Color.END}")
    print(f"{Color.CYAN}═══════════════════════════════════════════════════════════{Color.END}\n")
    
    with open(CONNECTIONS_FILE, 'r') as f:
        connections = json.load(f)
    
    users = load_users()
    
    if not any(connections.values()):
        print(f"{Color.YELLOW}No hay conexiones activas{Color.END}")
    else:
        for username, count in connections.items():
            if count > 0:
                user_data = users.get(username, {})
                user_type = user_data.get('type', 'unknown')
                max_conn = user_data.get('max_connections', 'N/A')
                print(f"{Color.GREEN}● {username}{Color.END} ({user_type}) - {count}/{max_conn} conexiones")
    
    input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")

def main_menu(username, role):
    """Menú principal"""
    try:
        while True:
            clear_screen()
            print_banner()
            print(f"\n{Color.GREEN}Usuario:{Color.END} {username} | {Color.YELLOW}Rol:{Color.END} {role}")
            print(f"{Color.CYAN}═══════════════════════════════════════════════════════════{Color.END}")
            print(f"{Color.CYAN}{Color.BOLD}                    MENÚ PRINCIPAL{Color.END}")
            print(f"{Color.CYAN}═══════════════════════════════════════════════════════════{Color.END}\n")
            
            print(f"{Color.GREEN}1.{Color.END} Información del Sistema")
            print(f"{Color.GREEN}2.{Color.END} Gestión de Usuarios")
            print(f"{Color.GREEN}3.{Color.END} Gestión de Servicios")
            print(f"{Color.GREEN}4.{Color.END} Ver Logs")
            print(f"{Color.GREEN}5.{Color.END} Ver Conexiones Activas")
            print(f"{Color.GREEN}6.{Color.END} Salir")
            
            choice = input(f"\n{Color.YELLOW}Selecciona una opción: {Color.END}").strip()
            
            if choice == '1':
                show_system_info()
            elif choice == '2':
                if role in ['admin', 'superadmin']:
                    manage_users(username)
                else:
                    print(f"{Color.RED}✗ No tienes permisos para esta acción{Color.END}")
                    input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.END}")
            elif choice == '3':
                manage_services()
            elif choice == '4':
                view_logs()
            elif choice == '5':
                view_connections()
            elif choice == '6':
                remove_connection(username)
                log_action(username, "Logout")
                print(f"\n{Color.GREEN}¡Hasta pronto!{Color.END}\n")
                sys.exit(0)
    except KeyboardInterrupt:
        # Si se cierra con Ctrl+C, también remover conexión
        remove_connection(username)
        log_action(username, "Logout forzado")
        print(f"\n\n{Color.YELLOW}Sesión cerrada.{Color.END}\n")
        sys.exit(0)

def main():
    """Función principal"""
    init_system()
    username, role = login()
    
    if username:
        main_menu(username, role)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
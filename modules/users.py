#!/usr/bin/env python3
"""
Módulo SSL - Gestión de Stunnel
"""
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path

from modules.common import Color, PROTOCOLS_FILE, clear_screen, print_banner, print_line
import moratech

CONFIG_DIR = Path.home() / '.moratech'
TOKEN_CONFIG_FILE = CONFIG_DIR / 'token_config.json'
USERS_FILE = CONFIG_DIR / 'users.json'


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
    moratech.log_action("admin", f"Usuario SSH creado: {username}")
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
    moratech.log_action("admin", f"Usuario token creado: {token_username}")
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
        moratech.log_action("admin", f"Usuario eliminado: {username}")
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
        moratech.log_action("admin", "Todos los usuarios eliminados")
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
    moratech.log_action("admin", "Contraseña de tokens reseteada")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

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

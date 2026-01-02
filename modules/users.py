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
    
    if save_users(users):
        moratech.log_action("admin", f"Usuario SSH creado: {username}")
        print(f"\n{Color.GREEN}✓ Usuario SSH creado exitosamente{Color.END}")
    else:
        print(f"\n{Color.RED}✗ Error creando usuario en el sistema{Color.END}")
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def add_token_user():
    """Agregar usuario Token"""
    token_config = load_token_config()
    users = load_users()
    
    print(f"\n{Color.CYAN}--- NUEVO USUARIO TOKEN ---{Color.END}\n")
    
    # Verificar si existe contraseña maestra
    if not token_config.get('token_password'):
        print(f"{Color.YELLOW}No hay contraseña configurada para tokens.{Color.END}\n")
        token_pass = input(f"{Color.GREEN}Contraseña maestra para tokens: {Color.END}").strip()
        token_config['token_password'] = token_pass
        save_token_config(token_config)
        print(f"{Color.GREEN}✓ Contraseña configurada{Color.END}\n")
    
    # Nombre visible
    display_name = input(f"{Color.GREEN}Nombre del usuario (ej: PedroCastro): {Color.END}").strip()
    
    # Token
    token_input = input(f"{Color.GREEN}Token de acceso: {Color.END}").strip()
    
    if token_input in users:
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
    
    users[token_input] = {
        "password": token_config['token_password'],
        "role": "user",
        "type": "token",
        "display_name": display_name,
        "created": datetime.now().isoformat(),
        "expires": expires,
        "max_connections": 1,
        "enabled": True,
        "original_token": token_input
    }
    
    if save_users(users):
        moratech.log_action("admin", f"Usuario token creado: {display_name} ({token_input})")
        print(f"\n{Color.GREEN}✓ Usuario token creado{Color.END}")
    else:
        print(f"\n{Color.RED}✗ Error creando usuario en el sistema{Color.END}")
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
    
    if username in users:
        del users[username]
        if save_users(users):
            moratech.log_action("admin", f"Usuario eliminado: {username}")
            print(f"{Color.GREEN}✓ Usuario eliminado{Color.END}")
        else:
            print(f"{Color.RED}✗ Error eliminando usuario del sistema{Color.END}")
    else:
        print(f"{Color.RED}✗ Usuario no encontrado{Color.END}")
    
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def delete_iterative():
    """Eliminar usuarios uno por uno"""
    users = load_users()
    
    for username in list(users.keys()):
        print(f"\n{Color.YELLOW}Usuario: {username}{Color.END}")
        confirm = input(f"¿Eliminar? (s/n): ").strip().lower()
        
        if confirm == 's':
            del users[username]
            print(f"{Color.GREEN}✓ Marcado para eliminar{Color.END}")

    if save_users(users):
        print(f"\n{Color.GREEN}✓ Cambios guardados{Color.END}")
    else:
        print(f"\n{Color.RED}✗ Error guardando cambios{Color.END}")

    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def delete_expired():
    """Eliminar solo usuarios caducados"""
    users = load_users()
    deleted = 0
    
    for username in list(users.keys()):
        user_data = users[username]
        if user_data.get('expires'):
            expire_date = datetime.fromisoformat(user_data['expires'])
            if datetime.now() > expire_date:
                del users[username]
                deleted += 1
                print(f"{Color.GREEN}✓ Eliminado: {username}{Color.END}")
    
    if save_users(users):
        print(f"\n{Color.YELLOW}Total eliminados: {deleted}{Color.END}")
    else:
        print(f"\n{Color.RED}✗ Error guardando cambios{Color.END}")
        
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def delete_all_users():
    """Eliminar TODOS los usuarios"""
    print(f"\n{Color.RED}⚠️  ADVERTENCIA: Esto eliminará TODOS los usuarios (excepto admin){Color.END}")
    confirm = input(f"{Color.YELLOW}Escribe 'CONFIRMAR' para continuar: {Color.END}").strip()
    
    if confirm == "CONFIRMAR":
        users = {}
        if save_users(users):
            moratech.log_action("admin", "Todos los usuarios eliminados")
            print(f"{Color.GREEN}✓ Todos los usuarios eliminados{Color.END}")
        else:
            print(f"{Color.RED}✗ Error eliminando usuarios del sistema{Color.END}")
    
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def edit_user():
    """Editar o renovar usuario"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}EDITAR/RENOVAR USUARIO{Color.END}")
    print_line()
    
    users = load_users()
    
    if not users:
        print(f"\n {Color.YELLOW}No hay usuarios registrados{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    # Mostrar usuarios disponibles
    print(f"\n {Color.YELLOW}Usuarios disponibles:{Color.END}\n")
    for i, (username, data) in enumerate(users.items(), 1):
        user_type = data.get('type', 'ssh')
        display_name = data.get('display_name', username) if user_type == 'token' else username
        
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
        
        print(f" {Color.GREEN}[{i}]{Color.END} {display_name} ({user_type}) - {status}")
    
    print_line()
    username_input = input(f"\n {Color.GREEN}Ingresa el nombre de usuario o token: {Color.END}").strip()
    
    if username_input not in users:
        print(f" {Color.RED}✗ Usuario no encontrado{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    user_data = users[username_input]
    
    # Menú de edición
    print(f"\n {Color.CYAN}--- EDITAR: {username_input} ---{Color.END}")
    print(f"\n {Color.GREEN}[1]{Color.END} Sumar días")
    print(f" {Color.GREEN}[2]{Color.END} Reiniciar días")
    print(f" {Color.GREEN}[3]{Color.END} Cambiar contraseña")
    print(f" {Color.GREEN}[4]{Color.END} Eliminar usuario")
    print(f" {Color.RED}[0]{Color.END} Cancelar")
    
    choice = input(f"\n {Color.CYAN}►{Color.END} Opción: ").strip()
    
    if choice == '1':
        # Sumar días
        days_to_add = input(f"\n {Color.GREEN}Días a sumar: {Color.END}").strip()
        try:
            days_to_add = int(days_to_add)
            
            if user_data.get('expires'):
                current_expire = datetime.fromisoformat(user_data['expires'])
                if datetime.now() > current_expire:
                    # Si ya expiró, sumar desde hoy
                    new_expire = datetime.now() + timedelta(days=days_to_add)
                else:
                    # Si no ha expirado, sumar a la fecha actual
                    new_expire = current_expire + timedelta(days=days_to_add)
            else:
                # Si es ilimitado, crear fecha desde hoy
                new_expire = datetime.now() + timedelta(days=days_to_add)

            users[username_input]['expires'] = new_expire.isoformat()

            if save_users(users):
                print(f"\n {Color.GREEN}✓ Cambios guardados{Color.END}")
                moratech.log_action("admin", f"Usuario editado: {username_input}")
            else:
                print(f" {Color.RED}✗ Los cambios NO fueron aplicados{Color.END}")
            
            new_days = (new_expire - datetime.now()).days
            print(f"\n {Color.GREEN}✓ Se sumaron {days_to_add} días{Color.END}")
            print(f" {Color.CYAN}Nuevo total: {new_days} días{Color.END}")
            moratech.log_action("admin", f"Días sumados a {username_input}: +{days_to_add}")
        except:
            print(f" {Color.RED}✗ Valor inválido{Color.END}")
    
    elif choice == '2':
        # Reiniciar días
        new_days = input(f"\n {Color.GREEN}Nuevos días (0 = ilimitado): {Color.END}").strip()
        try:
            new_days = int(new_days)
            
            if new_days > 0:
                new_expire = datetime.now() + timedelta(days=new_days)
                users[username_input]['expires'] = new_expire.isoformat()
            else:
                users[username_input]['expires'] = None
            
            if save_users(users):
                print(f"\n {Color.GREEN}✓ Días reiniciados{Color.END}")
                print(f" {Color.CYAN}Nuevo total: {new_days if new_days > 0 else 'ILIMITADO'} días{Color.END}")
                moratech.log_action("admin", f"Días reiniciados para {username_input}: {new_days}")
            else:
                print(f" {Color.RED}✗ Los cambios NO fueron aplicados{Color.END}")
        except:
            print(f" {Color.RED}✗ Valor inválido{Color.END}")
    
    elif choice == '3':
        # Cambiar contraseña
        if user_data.get('type') == 'token':
            print(f"\n {Color.YELLOW}Los usuarios token usan la contraseña maestra{Color.END}")
            print(f" {Color.YELLOW}Usa la opción [12] del menú principal para cambiarla{Color.END}")
        else:
            new_pass = input(f"\n {Color.GREEN}Nueva contraseña: {Color.END}").strip()
            users[username_input]['password'] = new_pass
            if save_users(users):
                print(f"\n {Color.GREEN}✓ Contraseña actualizada{Color.END}")
                moratech.log_action("admin", f"Contraseña cambiada para {username_input}")
            else:
                print(f" {Color.RED}✗ Los cambios NO fueron aplicados{Color.END}")
    
    elif choice == '4':
        # Eliminar usuario
        confirm = input(f"\n {Color.RED}¿Eliminar usuario {username_input}? (s/n): {Color.END}").strip().lower()
        if confirm == 's':
            del users[username_input]
            if save_users(users):
                print(f"\n {Color.GREEN}✓ Usuario eliminado{Color.END}")
                moratech.log_action("admin", f"Usuario eliminado: {username_input}")
            else:
                print(f" {Color.RED}✗ Error eliminando usuario{Color.END}")
        else:
            print(f" {Color.YELLOW}Operación cancelada{Color.END}")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def show_users():
    """Mostrar usuarios registrados"""
    clear_screen()
    print_banner()
    print(f"\n{Color.CYAN}╔══════════════════════════════════════════════════════════╗{Color.END}")
    print(f"{Color.CYAN}║              USUARIOS REGISTRADOS                        ║{Color.END}")
    print(f"{Color.CYAN}╚══════════════════════════════════════════════════════════╝{Color.END}\n")
    
    users = load_users()
    
    if not users:
        print(f" {Color.YELLOW}No hay usuarios registrados{Color.END}")
    else:
        for username, data in users.items():
            user_type = data.get('type', 'ssh')
            expires = data.get('expires')
            
            # Mostrar nombre visible para tokens
            if user_type == 'token':
                display_name = data.get('display_name', username)
                user_label = f"{display_name} (token)"
            else:
                user_label = f"{username} (ssh)"
            
            if expires:
                expire_date = datetime.fromisoformat(expires)
                if datetime.now() > expire_date:
                    status = f"{Color.RED}EXPIRADO{Color.END}"
                else:
                    days = (expire_date - datetime.now()).days
                    status = f"{Color.GREEN}{days} días{Color.END}"
            else:
                status = f"{Color.BLUE}ILIMITADO{Color.END}"
            
            print(f"{Color.YELLOW}{user_label}{Color.END} - {status}")
    
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
    """Guarda usuarios y sincroniza con el sistema Linux - transaccional"""
    import tempfile
    
    try:
        # 1. Primero sincronizar con el sistema (si falla, no guardamos JSON)
        result = subprocess.run(['cut', '-d:', '-f1', '/etc/passwd'], capture_output=True, text=True)
        system_users = result.stdout.strip().split('\n')
        
        # Crear/actualizar usuarios que están en JSON
        for username, data in users.items():
            # Si el usuario no existe en el sistema, crearlo
            if username not in system_users:
                result = subprocess.run(['useradd', '-M', '-s', '/bin/false', username], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"Error creando usuario {username}: {result.stderr}")
            
            # Actualizar contraseña
            password = str(data.get('password', ''))
            result = subprocess.run(['chpasswd'], 
                                  input=f"{username}:{password}\n".encode('utf-8'),
                                  capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Error actualizando contraseña de {username}: {result.stderr}")
        
        # Eliminar usuarios del sistema que ya no están en JSON
        moratech_users = list(users.keys())
        for sys_user in system_users:
            if sys_user.startswith('token_') or sys_user in moratech_users:
                if sys_user not in moratech_users:
                    result = subprocess.run(['userdel', '-f', sys_user], 
                                          capture_output=True, text=True)
                    if result.returncode != 0:
                        raise Exception(f"Error eliminando usuario {sys_user}: {result.stderr}")
        
        # 2. Si todo salió bien, guardar JSON
        # Primero guardar en archivo temporal
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, dir=CONFIG_DIR)
        json.dump(users, temp_file, indent=4)
        temp_file.close()
        
        # Luego mover atómicamente (esto previene corrupción)
        import shutil
        shutil.move(temp_file.name, USERS_FILE)
        
        return True
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error sincronizando usuarios con el sistema:{Color.END}")
        print(f" {Color.RED}{str(e)}{Color.END}")
        print(f" {Color.YELLOW}Los cambios NO fueron guardados{Color.END}")
        
        # Limpiar archivo temporal si existe
        try:
            import os
            if 'temp_file' in locals():
                os.unlink(temp_file.name)
        except:
            pass
        
        return False
    
def load_token_config():
    """Carga config de tokens"""
    with open(TOKEN_CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_token_config(config):
    """Guarda config de tokens"""
    with open(TOKEN_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

#!/usr/bin/env python3
"""
Módulo SSL - Gestión de Stunnel
"""
import time
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
        print_line()
        print(f" {Color.GREEN}[11]{Color.END} ➮ BOT API")
        print(f" {Color.GREEN}[12]{Color.END} ➮ BOT TELEGRAM")
        print_line()
        print(f" {Color.GREEN}[13]{Color.END} ➮ CHECKUSER ONLINE")    
        print_line()
        print(f" {Color.GREEN}[12]{Color.END} ➮ REINICIAR CONTRASEÑA TOKEN")
        print_line()
        print(f" {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}Volver{Color.END}")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
        
        if choice == '1':
            add_user()
        elif choice == '2':
            delete_users_menu()
        elif choice == '3':
            edit_user()
        elif choice == '4':
            show_users()
        elif choice == '9':
            menu_backup()
        elif choice == '13':
            menu_checkuser()
        elif choice == '11':
            menu_api_server()
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
    days = input(f"{Color.GREEN}Días de duración (0 = hoy 6pm): {Color.END}").strip()
    try:
        days = int(days)
        if days >= 0:
            # Calcular fecha de expiración a las 6pm
            expire_date = (datetime.now().date() + timedelta(days=days))
            expires = datetime.combine(expire_date, datetime.min.time()).replace(hour=18, minute=0, second=0).isoformat()
        else:
            expires = None       
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
    days = input(f"{Color.GREEN}Días de duración (0 = hoy 6pm): {Color.END}").strip()
    try:
        days = int(days)
        # Calcular fecha de expiración a las 6pm
        expire_date = (datetime.now().date() + timedelta(days=days))
        expires = datetime.combine(expire_date, datetime.min.time()).replace(hour=18, minute=0, second=0).isoformat()
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
        
        # Calcular status primero
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
        
        # Mostrar nombre y token
        if user_type == 'token':
            display_name = data.get('display_name', username)
            user_label = f"{display_name} ({username})"
        else:
            user_label = f"{username} (ssh)"
        
        print(f" {Color.GREEN}[{i}]{Color.END} {user_label} - {status}")
    
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
                    # Si ya expiró, sumar desde hoy a las 6pm
                    expire_date = (datetime.now().date() + timedelta(days=days_to_add))
                    new_expire = datetime.combine(expire_date, datetime.min.time()).replace(hour=18, minute=0, second=0)
                else:
                    # Si no ha expirado, sumar días manteniendo la hora 6pm
                    new_expire = current_expire + timedelta(days=days_to_add)
            else:
                # Si no tiene expiración, crear desde hoy a las 6pm
                expire_date = (datetime.now().date() + timedelta(days=days_to_add))
                new_expire = datetime.combine(expire_date, datetime.min.time()).replace(hour=18, minute=0, second=0)

            users[username_input]['expires'] = new_expire.isoformat()

            if save_users(users):
                new_days = (new_expire - datetime.now()).days
                print(f"\n {Color.GREEN}✓ Se sumaron {days_to_add} días{Color.END}")
                print(f" {Color.CYAN}Nuevo total: {new_days} días{Color.END}")
                moratech.log_action("admin", f"Días sumados a {username_input}: +{days_to_add}")
            else:
                print(f" {Color.RED}✗ Los cambios NO fueron aplicados{Color.END}")
        except:
            print(f" {Color.RED}✗ Valor inválido{Color.END}")
    
    elif choice == '2':
        # Reiniciar días
        new_days = input(f"\n {Color.GREEN}Nuevos días (0 = hoy 6pm): {Color.END}").strip()
        try:
            new_days = int(new_days)
            
            if new_days >= 0:
                # Calcular fecha de expiración a las 6pm
                expire_date = (datetime.now().date() + timedelta(days=new_days))
                new_expire = datetime.combine(expire_date, datetime.min.time()).replace(hour=18, minute=0, second=0)
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
                user_label = f"{display_name} ({username})"
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
                                  capture_output=True)
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

# sistema de backups regular

def menu_backup():
    """Menú de backup de usuarios"""
    while True:
        clear_screen()
        print_banner()
        print_line()
        print(f" {Color.CYAN}BACKUP DE USUARIOS{Color.END}")
        print_line()
        
        # Mostrar info de backups
        try:
            backup_dir = CONFIG_DIR / 'backups'
            if backup_dir.exists():
                backups = sorted(backup_dir.glob('backup_*.json'), reverse=True)
                if backups:
                    last_backup = backups[0]
                    backup_time = datetime.fromtimestamp(last_backup.stat().st_mtime)
                    print(f" {Color.YELLOW}Último backup local:{Color.END}")
                    print(f" {Color.GREEN}{last_backup.name}{Color.END}")
                    print(f" {Color.CYAN}Fecha: {backup_time.strftime('%d/%m/%Y %H:%M')}{Color.END}")
                else:
                    print(f" {Color.YELLOW}No hay backups locales{Color.END}")
            else:
                print(f" {Color.YELLOW}No hay backups locales{Color.END}")
        except:
            pass
        
        print_line()
        print(f" {Color.GREEN}[1]{Color.END} ➮ Respaldar usuarios [EN LÍNEA]")
        print(f" {Color.GREEN}[2]{Color.END} ➮ Restaurar usuarios [EN LÍNEA]")
        print(f" {Color.GREEN}[3]{Color.END} ➮ Restaurar usuarios [LOCALMENTE]")
        print(f" {Color.GREEN}[4]{Color.END} ➮ Ver backups locales")
        print_line()
        print(f" {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}Volver{Color.END}")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
        
        if choice == '1':
            backup_online()
        elif choice == '2':
            restore_online()
        elif choice == '3':
            restore_local_m()
        elif choice == '4':
            list_backups_m()
        elif choice == '0':
            break

def backup_online():
    """Respaldar usuarios en línea (formato texto compatible)"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}RESPALDAR USUARIOS EN LÍNEA{Color.END}")
    print_line()
    
    print(f"\n {Color.YELLOW}Creando backup...{Color.END}")
    
    try:
        # Crear directorio de backups
        backup_dir = CONFIG_DIR / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'backup_{timestamp}.txt'
        backup_path = backup_dir / backup_filename
        
        # Leer usuarios actuales
        users = load_users()
        
        # Convertir a formato texto
        backup_lines = []
        for username, data in users.items():
            user_type = data.get('type', 'ssh')
            password = data.get('password', '')
            max_conn = data.get('max_connections', 1)
            
            if user_type == 'token':
                # Formato TOKEN: {token}:{contraseña_token}:TOKEN:{dias}:{nombre_visual}
                display_name = data.get('display_name', username)
                
                # Calcular días restantes
                expires = data.get('expires')
                if expires:
                    expire_date = datetime.fromisoformat(expires)
                    days = max(0, (expire_date - datetime.now()).days)
                else:
                    days = 0
                
                line = f"{username}:{password}:TOKEN:{days}:{display_name}"
            else:
                # Formato SSH: {nombre}:{contraseña}:{max_conexiones}:{dias}
                expires = data.get('expires')
                if expires:
                    expire_date = datetime.fromisoformat(expires)
                    days = max(0, (expire_date - datetime.now()).days)
                else:
                    days = 0
                
                line = f"{username}:{password}:{max_conn}:{days}"
            
            backup_lines.append(line)
        
        # Guardar en archivo
        with open(backup_path, 'w') as f:
            f.write('\n'.join(backup_lines))
        
        print(f" {Color.GREEN}✓ Backup creado: {backup_filename}{Color.END}")
        print(f" {Color.CYAN}Total usuarios: {len(users)}{Color.END}")
        
        # Obtener IP del servidor
        import subprocess
        try:
            ip_result = subprocess.run(['curl', '-s', 'ifconfig.me'], 
                                     capture_output=True, text=True, timeout=3)
            server_ip = ip_result.stdout.strip()
        except:
            server_ip = "TU_IP"
        
        # Configurar servidor HTTP
        print(f"\n {Color.YELLOW}Configurando servidor HTTP...{Color.END}")
        
        port = input(f" {Color.GREEN}Puerto para servidor HTTP (default: 8000): {Color.END}").strip()
        if not port:
            port = "8000"
        
        # Verificar si ya hay servidor corriendo
        check_server = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        if 'moratech_backup' in check_server.stdout:
            subprocess.run(['screen', '-S', 'moratech_backup', '-X', 'quit'], stderr=subprocess.DEVNULL)
            import time
            time.sleep(1)
        
        # Iniciar servidor HTTP en background
        subprocess.run([
            'screen', '-dmS', 'moratech_backup',
            'python3', '-m', 'http.server', port,
            '--directory', str(backup_dir)
        ])
        
        # Abrir puerto en firewall
        subprocess.run(['ufw', 'allow', port], stderr=subprocess.DEVNULL)
        
        backup_url = f"http://{server_ip}:{port}/{backup_filename}"
        
        print(f"\n {Color.GREEN}✓ Servidor HTTP iniciado en puerto {port}{Color.END}")
        print(f"\n {Color.CYAN}URL del backup:{Color.END}")
        print(f" {Color.GREEN}{backup_url}{Color.END}")
        
        # Guardar URL del backup
        url_file = CONFIG_DIR / 'last_backup_url.txt'
        with open(url_file, 'w') as f:
            f.write(f"{backup_url}\n")
        
        print(f"\n {Color.YELLOW}Nota: El servidor HTTP quedará activo.{Color.END}")
        print(f" {Color.YELLOW}Para detenerlo: screen -S moratech_backup -X quit{Color.END}")
        
        moratech.log_action("admin", f"Backup en línea creado: {backup_url}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

# sistema de backups compatible con chumo

def restore_online():
    """Restaurar usuarios desde servidor HTTP (formato texto)"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}RESTAURAR USUARIOS EN LÍNEA{Color.END}")
    print_line()
    
    # Mostrar última URL guardada
    try:
        url_file = CONFIG_DIR / 'last_backup_url.txt'
        if url_file.exists():
            with open(url_file, 'r') as f:
                last_url = f.read().strip()
                print(f"\n {Color.YELLOW}Último backup en línea:{Color.END}")
                print(f" {Color.GREEN}{last_url}{Color.END}\n")
    except:
        pass
    
    backup_url = input(f" {Color.GREEN}URL del backup: {Color.END}").strip()
    
    if not backup_url:
        print(f" {Color.RED}✗ URL requerida{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    print(f"\n {Color.YELLOW}Descargando backup...{Color.END}")
    
    try:
        import subprocess
        import tempfile
        
        # Descargar archivo
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        temp_file.close()
        
        result = subprocess.run([
            'curl', '-s', '-o', temp_file.name, backup_url
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Leer backup descargado
            with open(temp_file.name, 'r') as f:
                backup_content = f.read().strip()
            
            if not backup_content:
                print(f" {Color.RED}✗ Backup vacío o inválido{Color.END}")
                import os
                os.unlink(temp_file.name)
                input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                return
            
            # Parsear backup
            users = {}
            token_config = load_token_config()
            
            for line in backup_content.split('\n'):
                if not line.strip():
                    continue
                
                parts = line.split(':')
                
                if 'TOKEN' in line:
                    # Formato TOKEN: {token}:{contraseña}:TOKEN:{dias}:{nombre_visual}
                    if len(parts) >= 5:
                        token = parts[0]
                        password = parts[1]
                        days = int(parts[3])
                        display_name = parts[4]
                        
                        # Guardar contraseña token si es la primera
                        if not token_config.get('token_password'):
                            token_config['token_password'] = password
                            save_token_config(token_config)
                        
                        expires = (datetime.now() + timedelta(days=days)).isoformat() if days > 0 else None
                        
                        users[token] = {
                            "password": token_config['token_password'],
                            "role": "user",
                            "type": "token",
                            "display_name": display_name,
                            "created": datetime.now().isoformat(),
                            "expires": expires,
                            "max_connections": 1,
                            "enabled": True,
                            "original_token": token
                        }
                else:
                    # Formato SSH: {nombre}:{contraseña}:{max_conexiones}:{dias}
                    if len(parts) >= 4:
                        username = parts[0]
                        password = parts[1]
                        max_conn = int(parts[2])
                        days = int(parts[3])
                        
                        expires = (datetime.now() + timedelta(days=days)).isoformat() if days > 0 else None
                        
                        users[username] = {
                            "password": password,
                            "role": "user",
                            "type": "ssh",
                            "created": datetime.now().isoformat(),
                            "expires": expires,
                            "max_connections": max_conn,
                            "enabled": True
                        }
            
            print(f" {Color.GREEN}✓ Backup descargado{Color.END}")
            print(f" {Color.CYAN}Usuarios en backup: {len(users)}{Color.END}")
            
            # Mostrar preview
            print(f"\n {Color.YELLOW}Preview de usuarios:{Color.END}")
            for i, (username, data) in enumerate(list(users.items())[:5], 1):
                user_type = data.get('type', 'ssh')
                if user_type == 'token':
                    display = f"{data.get('display_name')} ({username[:8]}...)"
                else:
                    display = username
                print(f" {i}. {display} ({user_type})")
            
            if len(users) > 5:
                print(f" ... y {len(users) - 5} más")
            
            confirm = input(f"\n {Color.YELLOW}¿Restaurar estos usuarios? (s/n): {Color.END}").strip().lower()
            
            if confirm == 's':
                if save_users(users):
                    print(f"\n {Color.GREEN}✓ Usuarios restaurados correctamente{Color.END}")
                    moratech.log_action("admin", f"Usuarios restaurados desde: {backup_url}")
                else:
                    print(f"\n {Color.RED}✗ Error restaurando usuarios{Color.END}")
            else:
                print(f"\n {Color.YELLOW}Restauración cancelada{Color.END}")
        else:
            print(f" {Color.RED}✗ Error descargando backup{Color.END}")
        
        # Limpiar archivo temporal
        import os
        os.unlink(temp_file.name)
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def backup_online_m():
    """Respaldar usuarios en línea (servidor HTTP)"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}RESPALDAR USUARIOS EN LÍNEA{Color.END}")
    print_line()
    
    print(f"\n {Color.YELLOW}Creando backup...{Color.END}")
    
    try:
        # Crear backup local primero
        backup_dir = CONFIG_DIR / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'backup_{timestamp}.json'
        backup_path = backup_dir / backup_filename
        
        # Leer usuarios actuales
        users = load_users()
        
        # Crear backup con metadata
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'users_count': len(users),
            'users': users
        }
        
        # Guardar localmente
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=4)
        
        print(f" {Color.GREEN}✓ Backup local creado: {backup_filename}{Color.END}")
        
        # Obtener IP del servidor
        import subprocess
        try:
            ip_result = subprocess.run(['curl', '-s', 'ifconfig.me'], 
                                     capture_output=True, text=True, timeout=3)
            server_ip = ip_result.stdout.strip()
        except:
            server_ip = "TU_IP"
        
        # Configurar servidor HTTP
        print(f"\n {Color.YELLOW}Configurando servidor HTTP...{Color.END}")
        
        port = input(f" {Color.GREEN}Puerto para servidor HTTP (default: 8000): {Color.END}").strip()
        if not port:
            port = "8000"
        
        # Iniciar servidor HTTP en background
        import subprocess
        subprocess.run([
            'screen', '-dmS', 'moratech_backup',
            'python3', '-m', 'http.server', port,
            '--directory', str(backup_dir)
        ])
        
        # Abrir puerto en firewall
        subprocess.run(['ufw', 'allow', port], stderr=subprocess.DEVNULL)
        
        backup_url = f"http://{server_ip}:{port}/{backup_filename}"
        
        print(f"\n {Color.GREEN}✓ Servidor HTTP iniciado en puerto {port}{Color.END}")
        print(f"\n {Color.CYAN}URL del backup:{Color.END}")
        print(f" {Color.GREEN}{backup_url}{Color.END}")
        
        # Guardar URL del backup
        url_file = CONFIG_DIR / 'last_backup_url.txt'
        with open(url_file, 'w') as f:
            f.write(f"{backup_url}\n")
        
        print(f"\n {Color.YELLOW}Nota: El servidor HTTP quedará activo.{Color.END}")
        print(f" {Color.YELLOW}Para detenerlo: screen -S moratech_backup -X quit{Color.END}")
        
        moratech.log_action("admin", f"Backup en línea creado: {backup_url}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def restore_online_m():
    """Restaurar usuarios desde servidor HTTP"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}RESTAURAR USUARIOS EN LÍNEA{Color.END}")
    print_line()
    
    # Mostrar última URL guardada
    try:
        url_file = CONFIG_DIR / 'last_backup_url.txt'
        if url_file.exists():
            with open(url_file, 'r') as f:
                last_url = f.read().strip()
                print(f"\n {Color.YELLOW}Último backup en línea:{Color.END}")
                print(f" {Color.GREEN}{last_url}{Color.END}\n")
    except:
        pass
    
    backup_url = input(f" {Color.GREEN}URL del backup: {Color.END}").strip()
    
    if not backup_url:
        print(f" {Color.RED}✗ URL requerida{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    print(f"\n {Color.YELLOW}Descargando backup...{Color.END}")
    
    try:
        import subprocess
        import json as js
        import tempfile
        
        # Descargar archivo
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        temp_file.close()
        
        result = subprocess.run([
            'curl', '-s', '-o', temp_file.name, backup_url
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Leer backup descargado
            with open(temp_file.name, 'r') as f:
                backup_data = js.load(f)
            
            users = backup_data.get('users', {})
            
            print(f" {Color.GREEN}✓ Backup descargado{Color.END}")
            print(f" {Color.CYAN}Usuarios en backup: {len(users)}{Color.END}")
            print(f" {Color.CYAN}Fecha: {backup_data.get('timestamp', 'N/A')}{Color.END}")
            
            confirm = input(f"\n {Color.YELLOW}¿Restaurar estos usuarios? (s/n): {Color.END}").strip().lower()
            
            if confirm == 's':
                if save_users(users):
                    print(f"\n {Color.GREEN}✓ Usuarios restaurados correctamente{Color.END}")
                    moratech.log_action("admin", f"Usuarios restaurados desde: {backup_url}")
                else:
                    print(f"\n {Color.RED}✗ Error restaurando usuarios{Color.END}")
            else:
                print(f"\n {Color.YELLOW}Restauración cancelada{Color.END}")
        else:
            print(f" {Color.RED}✗ Error descargando backup{Color.END}")
        
        # Limpiar archivo temporal
        import os
        os.unlink(temp_file.name)
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def restore_local_m():
    """Restaurar usuarios desde backup local"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}RESTAURAR USUARIOS LOCALMENTE{Color.END}")
    print_line()
    
    try:
        backup_dir = CONFIG_DIR / 'backups'
        
        if not backup_dir.exists():
            print(f"\n {Color.YELLOW}No hay backups locales{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        backups = sorted(backup_dir.glob('backup_*.json'), reverse=True)
        
        if not backups:
            print(f"\n {Color.YELLOW}No hay backups locales{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        print(f"\n {Color.YELLOW}Backups disponibles:{Color.END}\n")
        
        for i, backup in enumerate(backups[:10], 1):  # Mostrar últimos 10
            backup_time = datetime.fromtimestamp(backup.stat().st_mtime)
            
            # Leer info del backup
            try:
                with open(backup, 'r') as f:
                    data = json.load(f)
                    users_count = data.get('users_count', len(data.get('users', {})))
            except:
                users_count = '?'
            
            print(f" {Color.GREEN}[{i}]{Color.END} {backup.name}")
            print(f"     {Color.CYAN}Fecha: {backup_time.strftime('%d/%m/%Y %H:%M')}{Color.END}")
            print(f"     {Color.CYAN}Usuarios: {users_count}{Color.END}\n")
        
        print_line()
        choice = input(f" {Color.GREEN}Selecciona backup a restaurar (0 = cancelar): {Color.END}").strip()
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(backups):
                selected_backup = backups[idx]
                
                # Leer backup
                with open(selected_backup, 'r') as f:
                    backup_data = json.load(f)
                
                users = backup_data.get('users', {})
                
                print(f"\n {Color.CYAN}Backup seleccionado: {selected_backup.name}{Color.END}")
                print(f" {Color.CYAN}Usuarios: {len(users)}{Color.END}")
                
                confirm = input(f"\n {Color.YELLOW}¿Restaurar estos usuarios? (s/n): {Color.END}").strip().lower()
                
                if confirm == 's':
                    if save_users(users):
                        print(f"\n {Color.GREEN}✓ Usuarios restaurados correctamente{Color.END}")
                        moratech.log_action("admin", f"Usuarios restaurados desde: {selected_backup.name}")
                    else:
                        print(f"\n {Color.RED}✗ Error restaurando usuarios{Color.END}")
                else:
                    print(f"\n {Color.YELLOW}Restauración cancelada{Color.END}")
            elif int(choice) == 0:
                print(f"\n {Color.YELLOW}Operación cancelada{Color.END}")
            else:
                print(f"\n {Color.RED}✗ Opción inválida{Color.END}")
        except ValueError:
            print(f"\n {Color.RED}✗ Opción inválida{Color.END}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def list_backups_m():
    """Listar backups locales"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}BACKUPS LOCALES{Color.END}")
    print_line()
    
    try:
        backup_dir = CONFIG_DIR / 'backups'
        
        if not backup_dir.exists():
            print(f"\n {Color.YELLOW}No hay backups locales{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        backups = sorted(backup_dir.glob('backup_*.json'), reverse=True)
        
        if not backups:
            print(f"\n {Color.YELLOW}No hay backups locales{Color.END}")
        else:
            print(f"\n {Color.YELLOW}Total de backups: {len(backups)}{Color.END}\n")
            
            for backup in backups:
                backup_time = datetime.fromtimestamp(backup.stat().st_mtime)
                size = backup.stat().st_size / 1024  # KB
                
                # Leer info del backup
                try:
                    with open(backup, 'r') as f:
                        data = json.load(f)
                        users_count = data.get('users_count', len(data.get('users', {})))
                except:
                    users_count = '?'
                
                print(f" {Color.GREEN}{backup.name}{Color.END}")
                print(f" {Color.CYAN}Fecha: {backup_time.strftime('%d/%m/%Y %H:%M')}{Color.END}  |  {Color.CYAN}Usuarios: {users_count}{Color.END}  |  {Color.CYAN}Tamaño: {size:.1f} KB{Color.END}\n")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

#menu del checkuser

def menu_checkuser():
    """Menú de CheckUser Online"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}CHECKUSER ONLINE{Color.END}")
    print_line()
    
    # Verificar si hay servidor corriendo
    check_server = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
    is_running = 'moratech_checkuser' in check_server.stdout
    
    if is_running:
        # Obtener puerto actual
        try:
            port_file = CONFIG_DIR / 'checkuser_port.txt'
            if port_file.exists():
                with open(port_file, 'r') as f:
                    port = f.read().strip()
            else:
                port = "8888"
        except:
            port = "8888"
        
        print(f"\n {Color.GREEN}✓ Servidor activo en puerto {port}{Color.END}")
        
        # Obtener IP
        try:
            ip_result = subprocess.run(['curl', '-s', 'ifconfig.me'], 
                                     capture_output=True, text=True, timeout=3)
            server_ip = ip_result.stdout.strip()
            print(f" {Color.CYAN}URL: {Color.GREEN}http://{server_ip}:{port}/checkUser{Color.END}")
        except:
            pass
        
        print_line()
        print(f" {Color.GREEN}[1]{Color.END} ➮ Ver logs en tiempo real")
        print(f" {Color.GREEN}[2]{Color.END} ➮ Detener servidor")
    else:
        print(f"\n {Color.YELLOW}Servidor detenido{Color.END}")
        print_line()
        print(f" {Color.GREEN}[1]{Color.END} ➮ Iniciar servidor CheckUser")
    
    print_line()
    print(f" {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}Volver{Color.END}")
    print_line()
    
    choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
    
    if choice == '1':
        if is_running:
            view_checkuser_logs()
        else:
            start_checkuser_server()
    elif choice == '2' and is_running:
        stop_checkuser_server()
    elif choice == '0':
        return

def start_checkuser_server():
    """Iniciar servidor CheckUser con Flask"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INICIAR CHECKUSER ONLINE{Color.END}")
    print_line()
    
    port = input(f"\n {Color.GREEN}Puerto para CheckUser (default: 8888): {Color.END}").strip()
    if not port:
        port = "8888"
    
    print(f"\n {Color.YELLOW}Iniciando servidor CheckUser...{Color.END}")
    
    try:
        # Obtener ruta del script Flask
        import os
        flask_script = os.path.join(os.path.dirname(__file__), 'checkuser_flask.py')
        
        if not os.path.exists(flask_script):
            print(f" {Color.RED}✗ Error: checkuser_flask.py no encontrado{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        # Instalar Flask si no está
        print(f" {Color.YELLOW}Verificando Flask...{Color.END}")
        
        # Detectar pip disponible
        pip_cmd = None
        for cmd in ['pip', 'pip3', 'python3 -m pip', 'python -m pip']:
            try:
                check = subprocess.run(cmd.split() + ['--version'], 
                                     capture_output=True, text=True, timeout=5)
                if check.returncode == 0:
                    pip_cmd = cmd
                    break
            except:
                continue
        
        if not pip_cmd:
            print(f" {Color.RED}✗ pip no encontrado, instalando...{Color.END}")
            subprocess.run(['apt-get', 'update'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['apt-get', 'install', '-y', 'python3-pip'], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            pip_cmd = 'pip3'
        
        # Verificar si Flask está instalado
        try:
            result = subprocess.run(pip_cmd.split() + ['show', 'flask'], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f" {Color.YELLOW}Instalando Flask...{Color.END}")
                
                # Usar apt-get (más confiable en Ubuntu)
                install_result = subprocess.run(
                    ['apt-get', 'install', '-y', 'python3-flask'],
                    capture_output=True, text=True
                )
                
                # Verificar instalación nuevamente
                check_flask = subprocess.run(['python3', '-c', 'import flask'], 
                                             capture_output=True, text=True)
                
                if install_result.returncode != 0:
                    # Fallback a pip normal
                    subprocess.run(pip_cmd.split() + ['install', 'flask', '--break-system-packages'], 
                                capture_output=True, text=True)
                
                if check_flask.returncode == 0:
                    print(f" {Color.GREEN}✓ Flask instalado{Color.END}")
                else:
                    print(f" {Color.RED}✗ Flask no se pudo instalar{Color.END}")
                    print(f" {Color.YELLOW}Intenta manualmente: apt-get install -y python3-flask{Color.END}")
                    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                    return
            else:
                print(f" {Color.GREEN}✓ Flask ya instalado{Color.END}")

        except Exception as e:
            print(f" {Color.RED}✗ Error verificando Flask: {e}{Color.END}")
        
        # Abrir puerto en firewall
        subprocess.run(['ufw', 'allow', port], stderr=subprocess.DEVNULL)
        
        # Iniciar servidor en screen
        import time
        subprocess.run([
            'screen', '-dmS', 'moratech_checkuser',
            'python3', flask_script, port
        ])
        
        # Esperar a que inicie
        time.sleep(2)
        
        # Verificar si está corriendo
        check = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        if 'moratech_checkuser' not in check.stdout:
            print(f"\n {Color.RED}✗ El servidor no pudo iniciar{Color.END}")
            print(f" {Color.YELLOW}Ejecutando manualmente para ver error...{Color.END}")
            
            result = subprocess.run(['python3', flask_script, port], 
                                  capture_output=True, text=True, timeout=5)
            if result.stderr:
                print(f" {Color.RED}{result.stderr}{Color.END}")
            if result.stdout:
                print(f" {Color.YELLOW}{result.stdout}{Color.END}")
            
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        # Guardar puerto
        port_file = CONFIG_DIR / 'checkuser_port.txt'
        with open(port_file, 'w') as f:
            f.write(port)
        
        # Obtener IP
        try:
            ip_result = subprocess.run(['curl', '-s', 'ifconfig.me'], 
                                     capture_output=True, text=True, timeout=3)
            server_ip = ip_result.stdout.strip()
        except:
            server_ip = "TU_IP"
        
        print(f"\n {Color.GREEN}✓ Servidor CheckUser iniciado{Color.END}")
        print(f"\n {Color.CYAN}Configuración:{Color.END}")
        print(f" {Color.CYAN}Puerto: {Color.GREEN}{port}{Color.END}")
        print(f" {Color.CYAN}URL: {Color.GREEN}http://{server_ip}:{port}/checkUser{Color.END}")
        print(f" {Color.CYAN}Test: {Color.GREEN}http://{server_ip}:{port}/{Color.END}")
        
        print(f"\n {Color.YELLOW}Nota: El servidor quedará activo en background{Color.END}")
        print(f" {Color.YELLOW}Para ver logs: opción [1] en el menú{Color.END}")
        
        moratech.log_action("admin", f"CheckUser Online iniciado en puerto {port}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def stop_checkuser_server():
    """Detener servidor CheckUser"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}DETENER CHECKUSER{Color.END}")
    print_line()
    
    confirm = input(f"\n {Color.YELLOW}¿Detener servidor CheckUser? (s/n): {Color.END}").strip().lower()
    
    if confirm == 's':
        try:
            # Detener screen
            subprocess.run(['screen', '-S', 'moratech_checkuser', '-X', 'quit'], 
                         stderr=subprocess.DEVNULL)
            
            print(f"\n {Color.GREEN}✓ Servidor detenido{Color.END}")
            moratech.log_action("admin", "CheckUser Online detenido")
            
        except Exception as e:
            print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
    else:
        print(f"\n {Color.YELLOW}Operación cancelada{Color.END}")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")


def view_checkuser_logs():
    """Ver logs del CheckUser en tiempo real"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}LOGS DE CHECKUSER (Ctrl+C para salir){Color.END}")
    print_line()
    
    log_file = CONFIG_DIR / 'checkuser.log'
    
    if not log_file.exists():
        print(f"\n {Color.YELLOW}No hay logs todavía{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    try:
        # tail -f del log
        subprocess.run(['tail', '-f', str(log_file)])
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")



#MENU MAS IMPORANTE, MENU DE API SERVER PARA RENOVAR, CREAR, ETC##
def menu_api_server():
    """Menú del servidor API"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}SERVIDOR API REST{Color.END}")
    print_line()
    
    # Verificar si hay servidor corriendo
    check_server = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
    is_running = 'moratech_api' in check_server.stdout
    
    if is_running:
        # Obtener puerto actual
        try:
            port_file = CONFIG_DIR / 'api_port.txt'
            if port_file.exists():
                with open(port_file, 'r') as f:
                    port = f.read().strip()
            else:
                port = "9000"
        except:
            port = "9000"
        
        print(f"\n {Color.GREEN}✓ Servidor API activo en puerto {port}{Color.END}")
        print(f" {Color.CYAN}Clave: {Color.GREEN}moratech-key{Color.END}")
        
        # Obtener IP
        try:
            ip_result = subprocess.run(['curl', '-s', 'ifconfig.me'], 
                                     capture_output=True, text=True, timeout=3)
            server_ip = ip_result.stdout.strip()
            print(f" {Color.CYAN}URL: {Color.GREEN}http://{server_ip}:{port}/api/{Color.END}")
        except:
            pass
        
        print_line()
        print(f" {Color.GREEN}[1]{Color.END} ➮ Ver logs")
        print(f" {Color.GREEN}[2]{Color.END} ➮ Detener servidor")
    else:
        print(f"\n {Color.YELLOW}Servidor detenido{Color.END}")
        print_line()
        print(f" {Color.GREEN}[1]{Color.END} ➮ Iniciar servidor API")
    
    print_line()
    print(f" {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}Volver{Color.END}")
    print_line()
    
    choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
    
    if choice == '1':
        if is_running:
            view_api_logs()
        else:
            start_api_server()
    elif choice == '2' and is_running:
        stop_api_server()
    elif choice == '0':
        return
    else:
        menu_api_server()

def start_api_server():
    """Iniciar servidor API"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INICIAR SERVIDOR API{Color.END}")
    print_line()
    
    port = input(f"\n {Color.GREEN}Puerto para API (default: 9000): {Color.END}").strip()
    if not port:
        port = "9000"
    
    print(f"\n {Color.YELLOW}Iniciando servidor API...{Color.END}")
    
    try:
        # Obtener ruta del script
        import os
        api_script = os.path.join(os.path.dirname(__file__), 'api_server.py')
        
        if not os.path.exists(api_script):
            print(f" {Color.RED}✗ Error: api_server.py no encontrado{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        # Verificar Flask
        check_flask = subprocess.run(['python3', '-c', 'import flask'], 
                                    capture_output=True, text=True)
        
        if check_flask.returncode != 0:
            print(f" {Color.YELLOW}Instalando Flask...{Color.END}")
            subprocess.run(['apt-get', 'install', '-y', 'python3-flask'],
                         capture_output=True, text=True)
            print(f" {Color.GREEN}✓ Flask instalado{Color.END}")
        else:
            print(f" {Color.GREEN}✓ Flask disponible{Color.END}")
        
        # Abrir puerto
        subprocess.run(['ufw', 'allow', port], stderr=subprocess.DEVNULL)
        
        # Iniciar servidor
        import time
        subprocess.run([
            'screen', '-dmS', 'moratech_api',
            'python3', api_script, port
        ])
        
        time.sleep(2)
        
        # Verificar
        check = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        if 'moratech_api' not in check.stdout:
            print(f"\n {Color.RED}✗ El servidor no pudo iniciar{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        # Guardar puerto
        port_file = CONFIG_DIR / 'api_port.txt'
        with open(port_file, 'w') as f:
            f.write(port)
        
        # Obtener IP
        try:
            ip_result = subprocess.run(['curl', '-s', 'ifconfig.me'], 
                                     capture_output=True, text=True, timeout=3)
            server_ip = ip_result.stdout.strip()
        except:
            server_ip = "TU_IP"
        
        print(f"\n {Color.GREEN}✓ Servidor API iniciado{Color.END}")
        print(f"\n {Color.CYAN}Configuración:{Color.END}")
        print(f" {Color.CYAN}Puerto: {Color.GREEN}{port}{Color.END}")
        print(f" {Color.CYAN}URL: {Color.GREEN}http://{server_ip}:{port}/api/{Color.END}")
        
        moratech.log_action("admin", f"API Server iniciado en puerto {port}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
    menu_api_server()


def stop_api_server():
    """Detener servidor API"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}DETENER SERVIDOR API{Color.END}")
    print_line()
    
    confirm = input(f"\n {Color.YELLOW}¿Detener servidor API? (s/n): {Color.END}").strip().lower()
    
    if confirm == 's':
        try:
            subprocess.run(['screen', '-S', 'moratech_api', '-X', 'quit'], 
                         stderr=subprocess.DEVNULL)
            print(f"\n {Color.GREEN}✓ Servidor detenido{Color.END}")
            moratech.log_action("admin", "API Server detenido")
        except Exception as e:
            print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
    else:
        print(f"\n {Color.YELLOW}Operación cancelada{Color.END}")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
    menu_api_server()

def view_api_logs():
    """Ver logs del API"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}LOGS DEL API (Ctrl+C para salir){Color.END}")
    print_line()
    
    log_file = CONFIG_DIR / 'api.log'
    
    if not log_file.exists():
        print(f"\n {Color.YELLOW}No hay logs todavía{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    try:
        subprocess.run(['tail', '-f', str(log_file)])
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
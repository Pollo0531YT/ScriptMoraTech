#!/usr/bin/env python3
"""
Módulo USUARIOS  - Gestión de USUARIOS
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
        print(f" {Color.GREEN}[05]{Color.END} ➮ INFO EXACTA DE USUARIO")
        print_line()
        print(f" {Color.GREEN}[09]{Color.END} ➮ BACKUP USUARIOS")
        print_line()
        print(f" {Color.GREEN}[11]{Color.END} ➮ API INDIVIDUAL")
        print(f" {Color.GREEN}[12]{Color.END} ➮ API MASTER")
        print_line()
        print(f" {Color.GREEN}[13]{Color.END} ➮ CHECKUSER ONLINE")    
        print_line()
        print(f" {Color.GREEN}[14]{Color.END} ➮ REINICIAR CONTRASEÑA TOKEN")
        print_line()
        print(f" {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}Volver{Color.END}")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
        
        if choice == '1':
            agregar_usuario()
        elif choice == '2':
            menu_borrar_usuarios()
        elif choice == '3':
            editar_usuario()
        elif choice == '4':
            mostrar_users_registrados()
        elif choice == '5':
            info_exacta_usuario()
        elif choice == '9':
            menu_backup()
        elif choice == '13':
            menu_checkuser()
        elif choice == '11':
            menu_api_server()
        elif choice == '12':
            start_api_general_server
        elif choice == '14':
            reset_token_password()
        elif choice == '0':
            break

# ==================== MENÚ DE USUARIOS ====================

def agregar_usuario():
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
    """Agregar usuario SSH con vencimiento a las 6pm"""
    users = load_users()
    print(f"\n{Color.CYAN}--- NUEVO USUARIO SSH ---{Color.END}\n")
    
    username = input(f"{Color.GREEN}Nombre de usuario: {Color.END}").strip()
    if not username or username in users:
        print(f"{Color.RED}✗ El usuario ya existe o es inválido{Color.END}")
        input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    password = input(f"{Color.GREEN}Contraseña: {Color.END}").strip()
    days_input = input(f"{Color.GREEN}Días de duración (0 = hoy 6pm): {Color.END}").strip()
    
    try:
        days = int(days_input)
        expire_date = (datetime.now().date() + timedelta(days=days))
        expires = datetime.combine(expire_date, datetime.min.time()).replace(hour=18, minute=0, second=0).isoformat()
    except:
        expires = None 
    
    max_conn = input(f"{Color.GREEN}Máximas conexiones: {Color.END}").strip()
    max_conn = int(max_conn) if max_conn.isdigit() else 1
    
    new_user_data = {
        "password": password,
        "role": "user", "type": "ssh",
        "created": datetime.now().isoformat(),
        "expires": expires,
        "max_connections": max_conn,
        "enabled": True
    }
    
    users[username] = new_user_data
    print(f"\n{Color.YELLOW}⏳ Creando acceso en el sistema...{Color.END}", end="\r", flush=True)

    if save_users({username: new_user_data}, full_database=users):
        print(f"{' ' * 40}\r{Color.GREEN}✓ Usuario SSH creado exitosamente{Color.END}")
        moratech.log_action("admin", f"Usuario SSH creado: {username}")
    else:
        print(f"\n{Color.RED}✗ Error creando usuario en el sistema{Color.END}")
    
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def add_token_user():
    """Agregar usuario Token con vencimiento a las 6pm"""
    token_config = load_token_config()
    users = load_users()
    
    print(f"\n{Color.CYAN}--- NUEVO USUARIO TOKEN ---{Color.END}\n")
    
    if not token_config.get('token_password'):
        token_pass = input(f"{Color.GREEN}Contraseña maestra para tokens: {Color.END}").strip()
        token_config['token_password'] = token_pass
        save_token_config(token_config)
    
    display_name = input(f"{Color.GREEN}Nombre del usuario (ej: Pedro): {Color.END}").strip()
    token_input = input(f"{Color.GREEN}Token de acceso: {Color.END}").strip()
    
    if not token_input or token_input in users:
        print(f"{Color.RED}✗ Token inválido o ya existente{Color.END}")
        input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    days_input = input(f"{Color.GREEN}Días de duración (0 = hoy 6pm): {Color.END}").strip()
    try:
        days = int(days_input)
        expire_date = (datetime.now().date() + timedelta(days=days))
        expires = datetime.combine(expire_date, datetime.min.time()).replace(hour=18, minute=0, second=0).isoformat()
    except:
        print(f"{Color.RED}✗ Valor de días inválido{Color.END}")
        return

    new_token_data = {
        "password": token_config['token_password'],
        "role": "user", "type": "token",
        "display_name": display_name,
        "created": datetime.now().isoformat(),
        "expires": expires,
        "max_connections": 1,
        "enabled": True
    }
    
    users[token_input] = new_token_data
    print(f"\n{Color.YELLOW}⏳ Generando token en el sistema...{Color.END}", end="\r", flush=True)

    if save_users({token_input: new_token_data}, full_database=users):
        print(f"{' ' * 40}\r{Color.GREEN}✓ Usuario token creado correctamente{Color.END}")
        moratech.log_action("admin", f"Usuario token creado: {display_name} ({token_input})")
    else:
        print(f"\n{Color.RED}✗ Error al registrar el token{Color.END}")
        
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def editar_usuario():
    """Editar o renovar usuario - Optimización Instantánea"""
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
    
    # --- LISTADO RÁPIDO ---
    print(f"\n {Color.YELLOW}Usuarios disponibles:{Color.END}\n")
    for i, (username, data) in enumerate(users.items(), 1):
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
        
        display_name = data.get('display_name', username) if user_type == 'token' else username
        label = f"({user_type})"
        print(f" {Color.GREEN}[{i}]{Color.END} {display_name:<15} {Color.GRAY}{label:<7}{Color.END} - {status}")
    
    print_line()
    username_input = input(f"\n {Color.GREEN}Ingresa el nombre de usuario o token: {Color.END}").strip()
    
    if username_input not in users:
        print(f" {Color.RED}✗ Usuario no encontrado{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    user_data = users[username_input]
    
    # --- MENÚ DE EDICIÓN ---
    print(f"\n {Color.CYAN}--- GESTIÓN DE USUARIO: {username_input} ---{Color.END}")
    print(f" {Color.GREEN}[1]{Color.END} Sumar días (Extender vigencia)")
    print(f" {Color.GREEN}[2]{Color.END} Reiniciar días (Nueva fecha desde hoy)")
    print(f" {Color.GREEN}[3]{Color.END} Cambiar Contraseña")
    print(f" {Color.RED}[0]{Color.END} Salir / Cancelar")
    
    choice = input(f"\n {Color.CYAN}►{Color.END} Opción: ").strip()
    
    if choice == '1':
        days_to_add_input = input(f" {Color.GREEN}Días a sumar: {Color.END}").strip()
        try:
            days_to_add = int(days_to_add_input)
            now = datetime.now()
            current_expire = datetime.fromisoformat(user_data['expires']) if user_data.get('expires') else now
            base_date = now.date() if now > current_expire else current_expire.date()
            
            new_expire = datetime.combine(base_date + timedelta(days=days_to_add), datetime.min.time()).replace(hour=18, minute=0)
            users[username_input]['expires'] = new_expire.isoformat()
            users[username_input]['enabled'] = True

            print(f" {Color.YELLOW}⏳ Sincronizando...{Color.END}", end="\r")
            
            # MEJORA: Solo enviamos el usuario modificado
            if save_users({username_input: users[username_input]}, full_database=users):
                print(f"{' ' * 40}\r {Color.GREEN}✓ Días sumados exitosamente.{Color.END}")
                print(f" {Color.CYAN}Nueva fecha: {new_expire.strftime('%d/%m/%Y %H:%M')}{Color.END}")
            else:
                print(f"\n {Color.RED}✗ Error en el sistema.{Color.END}")
        except: print(f" {Color.RED}✗ Valor inválido.{Color.END}")

    elif choice == '2':
        new_days_input = input(f" {Color.GREEN}Nuevos días (0 = hoy 6pm): {Color.END}").strip()
        try:
            new_days = int(new_days_input)
            expire_date = (datetime.now().date() + timedelta(days=new_days))
            new_expire = datetime.combine(expire_date, datetime.min.time()).replace(hour=18, minute=0)
            
            users[username_input]['expires'] = new_expire.isoformat()
            users[username_input]['enabled'] = True

            print(f" {Color.YELLOW}⏳ Reiniciando vigencia...{Color.END}", end="\r")
            
            # MEJORA: Sincronización selectiva
            if save_users({username_input: users[username_input]}, full_database=users):
                print(f"{' ' * 40}\r {Color.GREEN}✓ Días reiniciados.{Color.END}")
            else:
                print(f"\n {Color.RED}✗ Error al aplicar cambios.{Color.END}")
        except: print(f" {Color.RED}✗ Valor inválido.{Color.END}")

    elif choice == '3':
        if user_data.get('type') == 'token':
            print(f" {Color.YELLOW}Los tokens usan la contraseña maestra (Opción 12).{Color.END}")
        else:
            new_pass = input(f" {Color.GREEN}Nueva contraseña: {Color.END}").strip()
            if new_pass:
                users[username_input]['password'] = new_pass
                print(f" {Color.YELLOW}⏳ Actualizando clave...{Color.END}", end="\r")
                
                # MEJORA: Solo actualizamos password de este usuario
                if save_users({username_input: users[username_input]}, full_database=users):
                    print(f"{' ' * 40}\r {Color.GREEN}✓ Contraseña actualizada.{Color.END}")
            else: print(f" {Color.RED}✗ No puede estar vacía.{Color.END}")
   
    input(f"\n {Color.CYAN}Presiona Enter para continuar...{Color.END}")

def menu_borrar_usuarios():
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
            borrar_usuario_especifico()
        elif choice == '2':
            borrar_iterativo()
        elif choice == '3':
            borrar_expirados()
        elif choice == '4':
            borrar_todos()
        elif choice == '0':
            break

def borrar_usuario_especifico():
    """Eliminar usuario específico - Eliminación Real de Linux"""
    users = load_users()
    username = input(f"\n{Color.GREEN}Usuario a eliminar: {Color.END}").strip()
    
    if username in users:
        print(f" {Color.YELLOW}🗑️  Eliminando {username} del sistema...{Color.END}", end="\r")
        
        # 1. Matar procesos para que no esté "busy" (ocupado)
        subprocess.run(['pkill', '-9', '-u', username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 2. ELIMINACIÓN FÍSICA DE LINUX (Fundamental)
        # -f fuerza la eliminación incluso si hay procesos pendientes
        # -r borraría también su carpeta home (úsalo si la creas)
        result = subprocess.run(['userdel', '-f', username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 3. Quitar de tu base de datos JSON
        del users[username]
        
        # 4. Guardar cambios en el JSON (Sin intentar sincronizar nada más)
        if save_users({}, full_database=users):
            moratech.log_action("admin", f"Usuario eliminado y purgado: {username}")
            print(f"{' ' * 50}\r{Color.GREEN}✓ Usuario {username} purgado totalmente del servidor{Color.END}")
        else:
            print(f"\n{Color.RED}✗ Error al guardar cambios en la base de datos{Color.END}")
    else:
        print(f"{Color.RED}✗ El usuario no existe en la base de datos{Color.END}")
    
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")
    
def borrar_iterativo():
    """Eliminar usuarios uno por uno - Corregido"""
    users = load_users()
    deleted_count = 0

    for username in list(users.keys()):
        if username == "admin": continue
        print(f"\n{Color.YELLOW}Usuario: {Color.WHITE}{username}{Color.END}")
        confirm = input(f" ¿Eliminar? (s/n): ").strip().lower()

        if confirm == 's':
            # 1. Expulsar y Borrar de Linux REAL
            subprocess.run(['pkill', '-9', '-u', username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['userdel', '-f', username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # 2. Quitar del diccionario
            del users[username]
            deleted_count += 1
            print(f" {Color.RED}✗ Eliminado del sistema{Color.END}")

    if deleted_count > 0:
        save_users({}, full_database=users)
        print(f"\n{Color.GREEN}✓ Proceso terminado. {deleted_count} usuarios purgados.{Color.END}")
    
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def borrar_expirados():
    """Eliminar usuarios caducados - Purgado Real"""
    clear_screen()
    print_banner()
    users = load_users()
    now = datetime.now()
    to_delete = [u for u, d in users.items() if d.get('expires') and now > datetime.fromisoformat(d['expires'])]

    if not to_delete:
        print(f" {Color.GREEN}✨ No hay usuarios caducados.{Color.END}")
    else:
        print(f" {Color.YELLOW}Limpiando {len(to_delete)} usuarios...{Color.END}")
        for username in to_delete:
            subprocess.run(['pkill', '-9', '-u', username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['userdel', '-f', username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            del users[username]
        
        save_users({}, full_database=users)
        print(f" {Color.GREEN}✓ Usuarios expirados eliminados físicamente.{Color.END}")
        
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def borrar_todos():
    """Eliminar TODOS los usuarios - Limpieza Total"""
    print(f"\n{Color.RED}⚠️  ADVERTENCIA: LIMPIEZA TOTAL DEL SISTEMA{Color.END}")
    if input(f"{Color.YELLOW}Escribe 'CONFIRMAR' para continuar: {Color.END}").strip() == "CONFIRMAR":
        users = load_users()
        # Filtrar usuarios reales de Linux para borrar (menos admin)
        for username in list(users.keys()):
            if username != "admin":
                subprocess.run(['pkill', '-9', '-u', username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['userdel', '-f', username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if save_users({}, full_database={}):
            print(f"\n{Color.GREEN}✓ Servidor limpio de usuarios externos.{Color.END}")
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def mostrar_users_registrados():
    """Mostrar usuarios registrados con diseño jerárquico y contador final"""
    clear_screen()
    print_banner()
    print(f"\n{Color.CYAN}╔══════════════════════════════════════════════════════════╗{Color.END}")
    print(f"{Color.CYAN}║              LISTADO DE USUARIOS REGISTRADOS             ║{Color.END}")
    print(f"{Color.CYAN}╚══════════════════════════════════════════════════════════╝{Color.END}\n")
    
    users = load_users()
    total_users = len(users)
    
    if not users:
        print(f" {Color.YELLOW}No hay usuarios registrados en la base de datos.{Color.END}")
    else:
        for username, data in users.items():
            user_type = data.get('type', 'ssh')
            expires = data.get('expires')
            
            # --- NIVEL 1: Nombre y Tipo ---
            if user_type == 'token':
                display_name = data.get('display_name', 'Sin Nombre')
                print(f" {Color.WHITE}{display_name}{Color.END} - {Color.MAGENTA}(TOKEN){Color.END}")
                detail_id = username
            else:
                print(f" {Color.WHITE}{username}{Color.END} - {Color.BLUE}(SSH){Color.END}")
                detail_id = username

            # --- CÁLCULO DE STATUS ---
            if expires:
                expire_date = datetime.fromisoformat(expires)
                if datetime.now() > expire_date:
                    status = f"{Color.RED}EXPIRADO{Color.END}"
                else:
                    days = (expire_date - datetime.now()).days
                    status = f"{Color.GREEN}{days} días{Color.END}"
            else:
                status = f"{Color.CYAN}ILIMITADO{Color.END}"

            # --- NIVEL 2: Detalle Técnico (Flecha) ---
            # Usamos :<20 para alinear la columna de los días
            print(f" {Color.CYAN}└─>{Color.END} {Color.YELLOW}{detail_id:<18}{Color.END} | {status}")
            print(f" {Color.GRAY}{'─' * 45}{Color.END}") # Línea divisora sutil

        # --- RESUMEN FINAL ---
        print(f"\n {Color.CYAN}Total usuarios registrados:{Color.END} {Color.GREEN}{total_users}{Color.END}")
    
    input(f"\n {Color.CYAN}Presiona Enter para volver...{Color.END}")

def info_exacta_usuario():
    """Muestra la ficha técnica detallada de un usuario o token"""
    clear_screen()
    print_banner()
    print(f"\n{Color.CYAN}╔══════════════════════════════════════════════════════════╗{Color.END}")
    print(f"{Color.CYAN}║                INFO EXACTA DE USUARIO                    ║{Color.END}")
    print(f"{Color.CYAN}╚══════════════════════════════════════════════════════════╝{Color.END}\n")
    
    users = load_users()
    search = input(f" {Color.GREEN}Ingresa el nombre o token a consultar: {Color.END}").strip()
    
    if search in users:
        data = users[search]
        u_type = data.get('type', 'ssh').upper()
        display_name = data.get('display_name', 'N/A')
        
        # --- Cálculo de Tiempos ---
        expires = data.get('expires')
        if expires:
            expire_dt = datetime.fromisoformat(expires)
            now = datetime.now()
            if now > expire_dt:
                dias_restantes = f"{Color.RED}EXPIRADO{Color.END}"
                estado_visual = f"{Color.RED}● INACTIVO / CADUCADO{Color.END}"
            else:
                diff = (expire_dt - now).days
                # Si queda menos de 1 día pero no ha vencido
                dias_restantes = f"{Color.GREEN}{diff} días{Color.END}" if diff > 0 else f"{Color.YELLOW}Vence hoy{Color.END}"
                estado_visual = f"{Color.GREEN}● ACTIVO (Vence: {expire_dt.strftime('%d/%m/%Y %H:%M')}){Color.END}"
        else:
            dias_restantes = f"{Color.CYAN}ILIMITADO{Color.END}"
            estado_visual = f"{Color.GREEN}● ACTIVO PERMANENTE{Color.END}"

        # --- Interfaz de Información ---
        print(f" {Color.WHITE}┌──────────────────────────────────────────────────────────┐{Color.END}")
        print(f"   {Color.WHITE}Nombre/Etiqueta:{Color.END}  {Color.YELLOW}{display_name}{Color.END}")
        print(f"   {Color.WHITE}ID / Usuario:   {Color.END}  {Color.WHITE}{search}{Color.END}")
        print(f"   {Color.WHITE}Tipo de Acceso: {Color.END}  {Color.PURPLE}{u_type}{Color.END}")
        print(f"   {Color.WHITE}Password:       {Color.END}  {Color.GRAY}{data.get('password', '******')}{Color.END}")
        print(f"   {Color.WHITE}Creado el:      {Color.END}  {data.get('created', 'N/A')[:10]}")
        print(f" {Color.WHITE}├──────────────────────────────────────────────────────────┤{Color.END}")
        print(f"   {Color.WHITE}Días Restantes: {Color.END}  {dias_restantes}")
        print(f"   {Color.WHITE}Estado Actual:  {Color.END}  {estado_visual}")
        
        # --- Verificación en Tiempo Real ---
        # Verificamos si existe en Linux y si tiene procesos
        check_linux = subprocess.run(['id', search], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        check_online = subprocess.run(['pgrep', '-u', search], stdout=subprocess.DEVNULL)
        
        linux_status = f"{Color.GREEN}Sincronizado{Color.END}" if check_linux.returncode == 0 else f"{Color.RED}No existe en Linux{Color.END}"
        online_status = f"{Color.GREEN}CONECTADO AHORA{Color.END}" if check_online.returncode == 0 else f"{Color.GRAY}Desconectado{Color.END}"
        
        print(f"   {Color.WHITE}Sinc. Linux:    {Color.END}  {linux_status}")
        print(f"   {Color.WHITE}Conexión Live:  {Color.END}  {online_status}")
        print(f" {Color.WHITE}└──────────────────────────────────────────────────────────┘{Color.END}")

    else:
        print(f"\n {Color.RED}✗ Error: El usuario o token '{search}' no existe en la base de datos.{Color.END}")
        
    input(f"\n{Color.CYAN}Presiona Enter para volver al menú...{Color.END}")

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

def save_users(users_to_sync, full_database=None):
    """Versión con margen de seguridad para evitar bloqueo SSH prematuro"""
    import tempfile
    import os
    import shutil

    db_to_save = full_database if full_database is not None else users_to_sync

    try:
        for username, data in users_to_sync.items():
            # 1. Crear si no existe
            if subprocess.run(['id', username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
                subprocess.run(['useradd', '-M', '-s', '/bin/false', username], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 2. Actualizar Contraseña
            password = str(data.get('password', ''))
            subprocess.run(['chpasswd'], input=f"{username}:{password}\n", text=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Esto evita el error "Account expired" porque Linux vence al inicio del día.
            expires = data.get('expires')
            if expires:
                expire_dt = datetime.fromisoformat(expires)
                # Le damos +1 días de gracia a Linux
                linux_margin = (expire_dt + timedelta(days=1)).strftime('%Y-%m-%d')
                subprocess.run(['usermod', '-e', linux_margin, '-U', '-s', '/bin/false', username], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                # Si no tiene fecha, le quitamos la expiración en Linux
                subprocess.run(['usermod', '-e', '', '-U', username], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 4. Guardado atómico del JSON
        temp_fd, temp_path = tempfile.mkstemp(dir=str(CONFIG_DIR), text=True)
        with os.fdopen(temp_fd, 'w') as f:
            json.dump(db_to_save, f, indent=4)
        shutil.move(temp_path, str(USERS_FILE))
        return True
    except Exception:
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
        print(f" {Color.GREEN}[1]{Color.END} ➮ Respaldar usuarios [EN LÍNEA - CHUMO]")
        print(f" {Color.GREEN}[2]{Color.END} ➮ Restaurar usuarios [EN LÍNEA - CHUMO]")
        print(f" {Color.GREEN}[3]{Color.END} ➮ Restaurar usuarios [LOCALMENTE - CHUMO]")
        print(f" {Color.GREEN}[4]{Color.END} ➮ Ver backups locales")
        print_line()
        print(f" {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}Volver{Color.END}")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
        
        if choice == '1':
            backup_online_chumo()
        elif choice == '2':
            restore_online_chumo()
        elif choice == '3':
            restore_local_chumo()
        elif choice == '4':
            list_backups_chumo()
        elif choice == '0':
            break

# sistema de backups compatible con chumo

def backup_online_chumo():
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
                    days = max(0, (expire_date - datetime.now()).days + 1)
                else:
                    days = 0
                
                line = f"{username}:{password}:TOKEN:{days}:{display_name}"
            else:
                # Formato SSH: {nombre}:{contraseña}:{max_conexiones}:{dias}
                expires = data.get('expires')
                if expires:
                    expire_date = datetime.fromisoformat(expires)
                    days = max(0, (expire_date - datetime.now()).days + 1)
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

def restore_online_chumo():
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
                        
                        #expires = (datetime.now() + timedelta(days=days)).isoformat() if days > 0 else None

                        # AJUSTE: Restamos 1 día si el backup trae días de más (CHUMO)
                        real_days = max(0, days - 1)
                        expire_date = (datetime.now().date() + timedelta(days=real_days))
                        expires = datetime.combine(expire_date, datetime.min.time()).replace(hour=18, minute=0, second=0).isoformat()
                        
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
                        
                        #expires = (datetime.now() + timedelta(days=days)).isoformat() if days > 0 else None
                        real_days = max(0, days - 1)
                        expire_date = (datetime.now().date() + timedelta(days=real_days))
                        expires = datetime.combine(expire_date, datetime.min.time()).replace(hour=18, minute=0, second=0).isoformat()

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
                clear_screen()
                print_banner()
                total = len(users)
                print(f"\n {Color.YELLOW}🚀 Iniciando restauración masiva...{Color.END}")
                print(f" {Color.CYAN}Procesando {total} usuarios, por favor espera...{Color.END}\n")

                # Restaurar uno a uno para mostrar el progreso "bonito"
                exitos = 0
                for i, (username, data) in enumerate(users.items(), 1):
                    # Creamos un diccionario temporal con un solo usuario para save_users
                    single_user = {username: data}
                    # Mostramos el mensaje ANTES de procesar
                    dias_display = max(0, int((datetime.fromisoformat(data['expires']) - datetime.now()).days))
                    print(f"\r {Color.YELLOW}Restaurando: {Color.GREEN}{username}{Color.END} [{dias_display} días] ({i}/{total})...{' ' * 10}", end="", flush=True)

                    # Guardamos silenciando la salida de usermod
                    if save_users(single_user):
                        exitos += 1
                print(f"\n\n {Color.GREEN}✓ Proceso finalizado: {exitos} usuarios restaurados.{Color.END}")
                moratech.log_action("admin", f"Restauración online completada: {exitos} usuarios")
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

def restore_local_chumo():
    """Restaurar usuarios desde backup local (formato .txt Chumo) con progreso visual"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}RESTAURAR USUARIOS LOCALMENTE (FORMATO TXT){Color.END}")
    print_line()
    
    try:
        backup_dir = CONFIG_DIR / 'backups'
        
        if not backup_dir.exists():
            print(f"\n {Color.YELLOW}No hay directorio de backups{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        # BUSCAMOS ARCHIVOS .txt
        backups = sorted(backup_dir.glob('backup_*.txt'), reverse=True)
        
        if not backups:
            print(f"\n {Color.YELLOW}No hay backups .txt disponibles{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        print(f"\n {Color.YELLOW}Backups disponibles:{Color.END}\n")
        
        for i, backup in enumerate(backups[:10], 1):
            backup_time = datetime.fromtimestamp(backup.stat().st_mtime)
            # Contar líneas para saber cuántos usuarios hay
            with open(backup, 'r') as f:
                count = sum(1 for line in f if line.strip())
            
            print(f" {Color.GREEN}[{i}]{Color.END} {backup.name}")
            print(f"     {Color.CYAN}Fecha: {backup_time.strftime('%d/%m/%Y %H:%M')}{Color.END}")
            print(f"     {Color.CYAN}Usuarios: {count}{Color.END}\n")
        
        print_line()
        choice = input(f" {Color.GREEN}Selecciona backup a restaurar (0 = cancelar): {Color.END}").strip()
        
        if choice == '0' or not choice:
            return

        idx = int(choice) - 1
        if 0 <= idx < len(backups):
            selected_backup = backups[idx]
            
            # PROCESAR EL ARCHIVO TXT
            users = {}
            with open(selected_backup, 'r') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if not line: continue
                parts = line.split(':')

                # Identificar si es TOKEN o SSH
                if 'TOKEN' in line and len(parts) >= 5:
                    token, password, _, days, display_name = parts[0], parts[1], parts[2], int(parts[3]), parts[4]
                    real_days = max(0, days - 1)
                    expire_date = (datetime.now().date() + timedelta(days=real_days))
                    expires = datetime.combine(expire_date, datetime.min.time()).replace(hour=18, minute=0, second=0).isoformat()

                    users[token] = {
                        "password": password, "role": "user", "type": "token",
                        "display_name": display_name, "created": datetime.now().isoformat(),
                        "expires": expires, "max_connections": 1, "enabled": True
                    }
                elif len(parts) >= 4:
                    username, password, max_conn, days = parts[0], parts[1], int(parts[2]), int(parts[3])
                    real_days = max(0, days - 1)
                    expire_date = (datetime.now().date() + timedelta(days=real_days))
                    expires = datetime.combine(expire_date, datetime.min.time()).replace(hour=18, minute=0, second=0).isoformat()

                    users[username] = {
                        "password": password, "role": "user", "type": "ssh",
                        "created": datetime.now().isoformat(), "expires": expires,
                        "max_connections": max_conn, "enabled": True
                    }

            print(f"\n {Color.CYAN}Usuarios listos para restaurar: {len(users)}{Color.END}")
            confirm = input(f"\n {Color.YELLOW}¿Confirmar restauración local? (s/n): {Color.END}").strip().lower()
            
            if confirm == 's':
                clear_screen()
                print_banner()
                total = len(users)
                print(f"\n {Color.YELLOW}🔄 Restaurando desde backup local...{Color.END}")
                print(f" {Color.CYAN}Cargando usuarios en el sistema, espera...{Color.END}\n")
                
                exitos = 0
                for i, (username, data) in enumerate(users.items(), 1):
                    # Diccionario de un solo usuario para procesar uno a uno
                    single_user = {username: data}
                    
                    # Cálculo de días para el mensaje visual
                    exp_dt = datetime.fromisoformat(data['expires'])
                    dias_restantes = max(0, (exp_dt.date() - datetime.now().date()).days)
                    
                    # Mensaje dinámico elegante
                    # <15 ajusta el nombre a la izquierda, >2 ajusta los días a la derecha
                    print(f"\r {Color.CYAN}Restaurando: {Color.GREEN}{username:<15}{Color.END} | {Color.YELLOW}{dias_restantes:>2} días{Color.END} | ({i}/{total}){' '*5}", end="", flush=True)
                    
                    if save_users(single_user):
                        exitos += 1
                
                print(f"\n\n {Color.GREEN}✓ Restauración local finalizada: {exitos}/{total} exitosos.{Color.END}")
                moratech.log_action("admin", f"Restauración local realizada: {selected_backup.name}")
            else:
                print(f"\n {Color.YELLOW}Operación cancelada.{Color.END}")
        else:
            print(f"\n {Color.RED}✗ Opción inválida.{Color.END}")

    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
    
    input(f"\n {Color.CYAN}Presiona Enter para volver...{Color.END}")

def list_backups_chumo():
    """Listar backups locales (Formato TXT de Chumo)"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}LISTA DE BACKUPS LOCALES (.TXT){Color.END}")
    print_line()
    
    try:
        backup_dir = CONFIG_DIR / 'backups'
        
        if not backup_dir.exists():
            print(f"\n {Color.YELLOW}No hay backups locales{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        # 1) CAMBIO: Buscar archivos .txt en lugar de .json
        backups = sorted(backup_dir.glob('backup_*.txt'), reverse=True)
        
        if not backups:
            print(f"\n {Color.YELLOW}No hay backups .txt en el directorio{Color.END}")
        else:
            print(f"\n {Color.YELLOW}Total de backups encontrados: {len(backups)}{Color.END}\n")
            
            for backup in backups:
                backup_time = datetime.fromtimestamp(backup.stat().st_mtime)
                size = backup.stat().st_size / 1024  # KB
                
                # 2) CAMBIO: Como es TXT, contamos las líneas para saber los usuarios
                try:
                    with open(backup, 'r') as f:
                        # Contamos solo líneas que no estén vacías
                        users_count = sum(1 for line in f if line.strip())
                except:
                    users_count = '?'
                
                print(f" {Color.GREEN}{backup.name}{Color.END}")
                print(f" {Color.CYAN}Fecha: {backup_time.strftime('%d/%m/%Y %H:%M')}{Color.END}  |  "
                      f"{Color.CYAN}Usuarios: {users_count}{Color.END}  |  "
                      f"{Color.CYAN}Tamaño: {size:.1f} KB{Color.END}\n")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error al listar: {e}{Color.END}")
    
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

def start_api_general_server():
    """Iniciar servidor API General (VPS Central)"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INICIAR API GENERAL (Dashboard Central){Color.END}")
    print_line()
    
    port = input(f"\n {Color.GREEN}Puerto para API General (default: 9100): {Color.END}").strip()
    if not port:
        port = "9100"
    
    print(f"\n {Color.YELLOW}Iniciando API General...{Color.END}")
    
    try:
        import os
        api_script = os.path.join(os.path.dirname(__file__), 'api_general.py')
        
        if not os.path.exists(api_script):
            print(f" {Color.RED}✗ Error: api_general.py no encontrado{Color.END}")
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
        
        # Abrir puerto
        subprocess.run(['ufw', 'allow', port], stderr=subprocess.DEVNULL)
        
        # Iniciar servidor
        import time
        subprocess.run([
            'screen', '-dmS', 'moratech_api_general',
            'python3', api_script, port
        ])
        
        time.sleep(2)
        
        # Verificar
        check = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        if 'moratech_api_general' not in check.stdout:
            print(f"\n {Color.RED}✗ El servidor no pudo iniciar{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        # Obtener IP
        try:
            ip_result = subprocess.run(['curl', '-s', 'ifconfig.me'], 
                                     capture_output=True, text=True, timeout=3)
            server_ip = ip_result.stdout.strip()
        except:
            server_ip = "TU_IP"
        
        print(f"\n {Color.GREEN}✓ API General iniciado{Color.END}")
        print(f"\n {Color.CYAN}Configuración:{Color.END}")
        print(f" {Color.CYAN}Puerto: {Color.GREEN}{port}{Color.END}")
        print(f" {Color.CYAN}Dashboard: {Color.GREEN}http://{server_ip}:{port}/dashboard-global{Color.END}")
        print(f" {Color.CYAN}Panel Control: {Color.GREEN}http://{server_ip}:{port}/panel-control{Color.END}")
        
        moratech.log_action("admin", f"API General iniciado en puerto {port}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def start_api_server():
    """Iniciar servidor API"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INICIAR SERVIDOR API{Color.END}")
    print_line()
    
    # Verificar/Configurar nombre de VPS
    vps_name_file = CONFIG_DIR / 'vps_name.txt'
    
    if not vps_name_file.exists():
        print(f"\n {Color.YELLOW}═══════════════════════════════════════════════════{Color.END}")
        print(f" {Color.CYAN}CONFIGURACIÓN INICIAL{Color.END}")
        print(f" {Color.YELLOW}═══════════════════════════════════════════════════{Color.END}")
        vps_name = input(f"\n {Color.GREEN}Nombre de esta VPS (ej: Directo1, Directo2): {Color.END}").strip()
        
        if not vps_name:
            print(f" {Color.RED}✗ Nombre requerido{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        CONFIG_DIR.mkdir(exist_ok=True)
        with open(vps_name_file, 'w') as f:
            f.write(vps_name)
        
        print(f" {Color.GREEN}✓ Nombre configurado: {vps_name}{Color.END}")
    else:
        with open(vps_name_file, 'r') as f:
            vps_name = f.read().strip()
        print(f"\n {Color.CYAN}Nombre de VPS: {Color.GREEN}{vps_name}{Color.END}")
    
    port = input(f"\n {Color.GREEN}Puerto para API (default: 9000): {Color.END}").strip()
    if not port:
        port = "9000"
    
    print(f"\n {Color.YELLOW}Iniciando servidor API...{Color.END}")
    
    try:
        import os
        api_script = os.path.join(os.path.dirname(__file__), 'api_server.py')
        
        if not os.path.exists(api_script):
            print(f" {Color.RED}✗ Error: api_server.py no encontrado{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        check_flask = subprocess.run(['python3', '-c', 'import flask'], 
                                    capture_output=True, text=True)
        
        if check_flask.returncode != 0:
            print(f" {Color.YELLOW}Instalando Flask...{Color.END}")
            subprocess.run(['apt-get', 'install', '-y', 'python3-flask'],
                         capture_output=True, text=True)
            print(f" {Color.GREEN}✓ Flask instalado{Color.END}")
        else:
            print(f" {Color.GREEN}✓ Flask disponible{Color.END}")
        
        subprocess.run(['ufw', 'allow', port], stderr=subprocess.DEVNULL)
        
        import time
        subprocess.run([
            'screen', '-dmS', 'moratech_api',
            'python3', api_script, port
        ])
        
        time.sleep(2)
        
        check = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        if 'moratech_api' not in check.stdout:
            print(f"\n {Color.RED}✗ El servidor no pudo iniciar{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        port_file = CONFIG_DIR / 'api_port.txt'
        with open(port_file, 'w') as f:
            f.write(port)
        
        try:
            ip_result = subprocess.run(['curl', '-s', 'ifconfig.me'], 
                                     capture_output=True, text=True, timeout=3)
            server_ip = ip_result.stdout.strip()
        except:
            server_ip = "TU_IP"
        
        print(f"\n {Color.GREEN}✓ Servidor API iniciado{Color.END}")
        print(f"\n {Color.CYAN}Configuración:{Color.END}")
        print(f" {Color.CYAN}VPS: {Color.GREEN}{vps_name}{Color.END}")
        print(f" {Color.CYAN}Puerto: {Color.GREEN}{port}{Color.END}")
        print(f" {Color.CYAN}URL: {Color.GREEN}http://{server_ip}:{port}/api/{Color.END}")
        
        moratech.log_action("admin", f"API Server '{vps_name}' iniciado en puerto {port}")
        
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
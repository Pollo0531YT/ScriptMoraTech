#!/usr/bin/env python3
"""
Módulo USUARIOS  - Gestión de USUARIOS
"""
import time
import subprocess
import json
from datetime import datetime, timedelta, time, timezone
from pathlib import Path

from modules.common import Color, PROTOCOLS_FILE, clear_screen, print_banner, print_line
import moratech

CONFIG_DIR = Path.home() / '.moratech'
TOKEN_CONFIG_FILE = CONFIG_DIR / 'token_config.json'
USERS_FILE = CONFIG_DIR / 'users.json'

CR_TZ = timezone(timedelta(hours=-6))

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
            menu_api_general()
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
    """Agregar usuario SSH desde el menú - Llama a la función maestra"""
    print(f"\n{Color.CYAN}--- NUEVO USUARIO SSH ---{Color.END}\n")
    username = input(f"{Color.GREEN}Nombre de usuario: {Color.END}").strip()
    password = input(f"{Color.GREEN}Contraseña: {Color.END}").strip()
    days_input = input(f"{Color.GREEN}Días de duración (0 = hoy 6pm): {Color.END}").strip()
    max_conn = input(f"{Color.GREEN}Máximas conexiones: {Color.END}").strip()

    # Llamada a la función maestra
    success, msg, expires = ejecutar_creacion_usuario(
        username=username, 
        password=password, 
        dias=days_input, 
        user_type="ssh", 
        max_conn=max_conn
    )

    if success:
        print(f"\n{Color.GREEN}✓ {msg} (Expira: {expires}){Color.END}")
        moratech.log_action("admin", f"Usuario SSH creado: {username}")
    else:
        print(f"\n{Color.RED}✗ {msg}{Color.END}")
    
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def add_token_user():
    """Agregar usuario Token desde el menú - Llama a la función maestra"""
    token_config = load_token_config()
    print(f"\n{Color.CYAN}--- NUEVO USUARIO TOKEN ---{Color.END}\n")

    if not token_config.get('token_password'):
        token_pass = input(f"{Color.GREEN}Contraseña maestra para tokens: {Color.END}").strip()
        token_config['token_password'] = token_pass
        save_token_config(token_config)

    display_name = input(f"{Color.GREEN}Nombre del usuario: {Color.END}").strip()
    token_input = input(f"{Color.GREEN}Token de acceso: {Color.END}").strip()
    days_input = input(f"{Color.GREEN}Días de duración (0 = hoy 6pm): {Color.END}").strip()

    # Llamada a la función maestra
    success, msg, expires = ejecutar_creacion_usuario(
        username=token_input, 
        password=token_config['token_password'], 
        dias=days_input, 
        user_type="token", 
        display_name=display_name
    )

    if success:
        print(f"\n{Color.GREEN}✓ {msg}{Color.END}")
        moratech.log_action("admin", f"Token creado: {display_name} ({token_input})")
    else:
        print(f"\n{Color.RED}✗ {msg}{Color.END}")

    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def ejecutar_creacion_usuario(username, password, dias, user_type="ssh", max_conn=1, display_name=None):
    """Crea el usuario en memoria y llama a save_users para sincronizar Linux"""
    users = load_users()
    if not username or username in users:
        return False, "Usuario ya existe o nombre inválido", None

    try:
        days_int = int(dias)
        now = datetime.now(CR_TZ)
        # Expiración: Hoy + X días a las 18:00:00
        expire_date = (now.date() + timedelta(days=days_int))
        expires_dt = datetime.combine(expire_date, time(18, 0, 0)).replace(tzinfo=CR_TZ)
        expires_iso = expires_dt.isoformat()

        new_user_data = {
            "password": str(password),
            "role": "user",
            "type": user_type,
            "created": now.isoformat(),
            "expires": expires_iso,
            "max_connections": int(max_conn),
            "enabled": True
        }
        if user_type == "token" and display_name:
            new_user_data["display_name"] = display_name

        # save_users se encarga de useradd, chpasswd y usermod -e
        if save_users({username: new_user_data}, full_database=users):
            return True, "Sincronizado con éxito", expires_dt
    except Exception as e:
        return False, f"Error: {str(e)}", None

def ejecutar_renovacion_dias(username, days, referencia='', origen='manual'):
    users = load_users()
    if username not in users:
        return False, "Usuario no encontrado", None

    try:
        user_data = users[username]
        # SIEMPRE obtenemos la hora actual en Costa Rica
        now = datetime.now(CR_TZ)
        
        if user_data.get('expires'):
            # Convertimos lo guardado a objeto datetime con zona horaria
            current_expire = datetime.fromisoformat(user_data['expires']).replace(tzinfo=CR_TZ)
            # Si ya venció, sumamos desde hoy. Si no, desde su vencimiento actual.
            base_date = current_expire if current_expire > now else now
        else:
            base_date = now

        # Calculamos nueva fecha: +X días a las 6:00 PM
        new_expire_dt = datetime.combine((base_date + timedelta(days=days)).date(), time(18, 0, 0)).replace(tzinfo=CR_TZ)
        
        users[username]['expires'] = new_expire_dt.isoformat()
        users[username]['enabled'] = True
        
        # save_users se encarga de aplicar el +1 para Linux internamente
        if save_users({username: users[username]}, full_database=users):
            return True, "Renovación exitosa", new_expire_dt
        
        return False, "Error al guardar cambios", None
    except Exception as e:
        return False, f"Error: {str(e)}", None

def ejecutar_reinicio_dias(username, days):
    users = load_users()
    if username not in users:
        return False, "Usuario no encontrado", None

    try:
        now = datetime.now(CR_TZ)
        # Reiniciar: Hoy + X días a las 6:00 PM
        new_date = (now.date() + timedelta(days=days))
        new_expire_dt = datetime.combine(new_date, time(18, 0, 0)).replace(tzinfo=CR_TZ)
        
        users[username]['expires'] = new_expire_dt.isoformat()
        users[username]['enabled'] = True
        
        if save_users({username: users[username]}, full_database=users):
            return True, "Reinicio exitoso", new_expire_dt
        return False, "Error al guardar", None
    except Exception as e:
        return False, f"Error: {str(e)}", None
    
def editar_usuario():
    clear_screen()
    print_banner()
    print(f" {Color.CYAN}--- GESTIÓN DE USUARIOS ---{Color.END}")
    users = load_users()
    
    if not users:
        print(f"\n {Color.YELLOW}Base de datos vacía.{Color.END}")
        input(" Enter..."); return

    # Listar (evitando admin para edición de tiempo)
    u_list = [u for u in users.keys() if u != "admin"]
    for i, user in enumerate(u_list, 1):
        data = users[user]
        exp_str = data.get('expires', 'Nunca')
        # Visualización de días restantes
        if exp_str != 'Nunca':
            diff = (datetime.fromisoformat(exp_str).replace(tzinfo=CR_TZ) - datetime.now(CR_TZ)).days
            status = f"{Color.GREEN}{diff}d restantes{Color.END}" if diff >= 0 else f"{Color.RED}EXPIRADO{Color.END}"
        else: status = "Ilimitado"
        
        print(f" {Color.GREEN}[{i}]{Color.END} {user:<15} | {status}")

    print_line()
    idx = input(f" {Color.YELLOW}Selecciona número o escribe nombre: {Color.END}").strip()
    
    # Manejo de selección por índice o nombre
    target = None
    if idx.isdigit() and 0 < int(idx) <= len(u_list):
        target = u_list[int(idx)-1]
    elif idx in users:
        target = idx
        
    if not target or target == "admin":
        print(f" {Color.RED}Selección inválida.{Color.END}"); time.sleep(1); return

    # Menú de edición del usuario seleccionado
    print(f"\n {Color.CYAN}Editando: {Color.WHITE}{target}{Color.END}")
    print(f" [1] Sumar días | [2] Reiniciar días | [3] Cambiar Clave")
    opc = input(f" {Color.YELLOW}Opción: {Color.END}")

    if opc == '1':
        d = input(" Cantidad de días a sumar: ")
        if d.isdigit():
            res, msg, date = ejecutar_renovacion_dias(target, int(d))
            print(f" {Color.GREEN if res else Color.RED} {msg} -> {date.strftime('%Y-%m-%d') if date else ''}{Color.END}")
    
    elif opc == '2':
        d = input(" Nuevos días totales (desde hoy): ")
        if d.isdigit():
            res, msg, date = ejecutar_reinicio_dias(target, int(d))
            print(f" {Color.GREEN if res else Color.RED} {msg} -> {date.strftime('%Y-%m-%d') if date else ''}{Color.END}")

    elif opc == '3':
        new_p = input(" Nueva contraseña: ").strip()
        if new_p:
            users[target]['password'] = new_p
            if save_users({target: users[target]}, full_database=users):
                print(f" {Color.GREEN}Contraseña actualizada en Linux y JSON.{Color.END}")
    
    input(f"\n{Color.CYAN}Presiona Enter para volver...{Color.END}")


#ENCARGADO DE BORRADO DE USUARIOS#
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

def ejecutar_borrado_fisico(username, users_db=None):
    """
    ÚNICA FUNCIÓN MAESTRA DE BORRADO
    Borra en Linux (pkill + userdel) y actualiza el diccionario/JSON.
    """
    try:
        # 1. Expulsar al usuario y matar procesos (Desconexión inmediata)
        subprocess.run(['pkill', '-9', '-u', username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 2. Borrar de Linux (fuerza -f y borra home -r)
        subprocess.run(['userdel', '-f', '-r', username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 3. Gestión del JSON
        if users_db is not None:
            # Si viene de un proceso masivo (ej: una purga automática)
            if username in users_db:
                del users_db[username]
            return True, "Removido"
        else:
            # Borrado individual desde el Menú o API
            db = load_users()
            if username in db:
                del db[username]
                
                # --- AQUÍ ESTÁ EL CAMBIO ---
                # En lugar de usar save_users(), guardamos el JSON directamente.
                # Porque el usuario YA fue borrado de Linux en el paso 2.
                import os, tempfile, shutil
                temp_fd, temp_path = tempfile.mkstemp(dir=str(CONFIG_DIR), text=True)
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(db, f, indent=4)
                shutil.move(temp_path, str(USERS_FILE))
                # ---------------------------

                return True, "Usuario purgado correctamente"
            return False, "Usuario no encontrado en la base de datos"
            
    except Exception as e:
        return False, f"Error crítico: {str(e)}"
     
def borrar_usuario_especifico():
    """Opción 1: Borrar un solo usuario por nombre"""
    print(f"\n {Color.CYAN}--- BORRAR USUARIO ESPECÍFICO ---{Color.END}")
    username = input(f" {Color.GREEN}Nombre de usuario a eliminar: {Color.END}").strip()
    
    if username == "admin":
        print(f" {Color.RED}✗ No puedes eliminar al administrador.{Color.END}")
    else:
        print(f" {Color.YELLOW}⏳ Procesando borrado...{Color.END}", end="\r")
        success, msg = ejecutar_borrado_fisico(username)
        print(f" {' ' * 30}\r", end="") # Limpia la línea de carga
        if success:
            print(f" {Color.GREEN}✓ {msg}{Color.END}")
        else:
            print(f" {Color.RED}✗ {msg}{Color.END}")
            
    input(f"\n {Color.CYAN}Presiona Enter para continuar...{Color.END}")

def borrar_iterativo():
    """Opción 2: Preguntar uno por uno"""
    users = load_users()
    if not users:
        print(f" {Color.YELLOW}No hay usuarios registrados.{Color.END}")
        return

    deleted_count = 0
    print(f"\n {Color.CYAN}Iniciando revisión de usuarios...{Color.END}")
    
    for username in list(users.keys()):
        if username == "admin": continue
        
        print(f" {Color.YELLOW}USUARIO: {Color.WHITE}{username}{Color.END}")
        confirm = input(f" {Color.CYAN}¿Eliminar físicamente? (s/n): {Color.END}").strip().lower()

        if confirm == 's':
            print(f"   {Color.RED}✗ Eliminando {username}...{Color.END}", end="\r")
            ejecutar_borrado_fisico(username, users) # Llama a la maestra
            deleted_count += 1
            print(f"   {Color.GREEN}✓ {username} purgado del sistema.{Color.END}      ")

    if deleted_count > 0:
        save_users(users) # Guardamos el JSON final con los cambios masivos
        print(f"\n {Color.GREEN}✓ Proceso terminado. {deleted_count} usuarios purgados.{Color.END}")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def borrar_expirados():
    """Opción 3: Limpieza automática de caducados"""
    clear_screen()
    print_banner()
    users = load_users()
    now = datetime.now()
    
    # Buscamos quiénes ya pasaron su fecha
    vencidos = [u for u, d in users.items() if d.get('expires') and now > datetime.fromisoformat(d['expires'])]

    if not vencidos:
        print(f" {Color.GREEN}✨ El sistema está limpio. No hay usuarios caducados.{Color.END}")
    else:
        print(f" {Color.YELLOW}Se encontraron {len(vencidos)} usuarios expirados.{Color.END}")
        print(f" {Color.CYAN}Iniciando purga masiva...{Color.END}\n")
        
        for username in vencidos:
            print(f" {Color.GRAY}>> Purgando {username}...{Color.END}", end="\r")
            ejecutar_borrado_fisico(username, users) # Llama a la maestra
            print(f" {Color.RED}✗ {username} eliminado.{Color.END}           ")
            time.sleep(0.1) # Efecto visual de progreso
        
        save_users(users) # Actualiza el JSON de una vez
        print(f"\n {Color.GREEN}✓ Limpieza de expirados completada con éxito.{Color.END}")
        
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def borrar_todos():
    """Opción 4: Reset total"""
    print(f"\n {Color.RED}⚠️  ¡ATENCIÓN! ESTO ELIMINARÁ TODOS LOS USUARIOS DEL SISTEMA ⚠️{Color.END}")
    confirm = input(f" {Color.YELLOW}Escribe 'CONFIRMAR' para proceder: {Color.END}").strip()
    
    if confirm == "CONFIRMAR":
        users = load_users()
        total = len(users) - (1 if "admin" in users else 0)
        
        print(f"\n {Color.CYAN}Iniciando formateo de usuarios...{Color.END}")
        for username in list(users.keys()):
            if username != "admin":
                print(f" {Color.RED}✗ Eliminando: {username}{Color.END}", end="\r")
                ejecutar_borrado_fisico(username, users)
                print(f" {Color.RED}✗ {username} eliminado del servidor.{Color.END}")

        save_users(users) # En este punto users solo tiene a admin o está vacío
        print(f"\n {Color.GREEN}✓ Servidor totalmente limpio.{Color.END}")
    else:
        print(f" {Color.YELLOW}Operación cancelada.{Color.END}")
        
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

#ENCARGADO DE MOSTRAR USUARIOS REGISTRADOS O INFO EXACTA
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

#RE-INICIAR CONTRASEÑA DE TOKEN
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

def load_token_config():
    """Carga config de tokens"""
    with open(TOKEN_CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_token_config(config):
    """Guarda config de tokens"""
    with open(TOKEN_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

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
    """Restaurar usuarios desde servidor HTTP con progreso visual profesional"""
    clear_screen()
    print_banner()
    print(f" {Color.CYAN}RESTAURAR USUARIOS EN LÍNEA{Color.END}")
    print("-" * 45)
    
    # Mostrar última URL para facilitar la vida al usuario
    try:
        url_file = CONFIG_DIR / 'last_backup_url.txt'
        if url_file.exists():
            with open(url_file, 'r') as f:
                last_url = f.read().strip()
                print(f" {Color.YELLOW}Último backup detectado:{Color.END}")
                print(f" {Color.GRAY}{last_url}{Color.END}\n")
    except: pass
    
    backup_url = input(f" {Color.GREEN}Enlace del backup: {Color.END}").strip()
    if not backup_url: return

    print(f"\n {Color.YELLOW}⏳ Descargando base de datos...{Color.END}", end="\r")
    
    try:
        import requests # Si no tienes requests, usa subprocess con curl
        response = requests.get(backup_url, timeout=10)
        if response.status_code != 200:
            print(f" {Color.RED}✗ No se pudo descargar el archivo (Error {response.status_code}){Color.END}")
            return
        
        backup_content = response.text.strip()
        if not backup_content:
            print(f" {Color.RED}✗ El archivo de backup está vacío.{Color.END}")
            return

        # Cargamos DB actual para fusionar
        db_completa = load_users()
        lineas = backup_content.split('\n')
        total = len(lineas)
        exitos = 0

        print(f" {Color.GREEN}✓ Descarga exitosa. Procesando {total} usuarios...{Color.END}\n")

        for i, line in enumerate(lineas, 1):
            parts = line.split(':')
            if not parts or len(parts) < 4: continue
            
            # Identificar formato y parsear
            username = parts[0]
            if 'TOKEN' in line:
                # Formato TOKEN: {token}:{pass}:TOKEN:{dias}:{nombre}
                password, days, display_name = parts[1], int(parts[3]), parts[4]
                tipo = "token"
            else:
                # Formato SSH: {nombre}:{pass}:{conn}:{dias}
                password, max_conn, days = parts[1], int(parts[2]), int(parts[3])
                tipo = "ssh"
                display_name = username

            # Calcular expiración
            real_days = max(0, days - 1)
            expire_date = (datetime.now().date() + timedelta(days=real_days))
            expires = datetime.combine(expire_date, datetime.min.time()).replace(hour=18, minute=0).isoformat()

            # Estructura para el JSON
            user_data = {
                "password": password,
                "role": "user",
                "type": tipo,
                "display_name": display_name,
                "created": datetime.now().isoformat(),
                "expires": expires,
                "max_connections": int(parts[2]) if tipo == "ssh" else 1,
                "enabled": True
            }

            # EFECTO VISUAL: Actualiza la misma línea
            print(f"\r {Color.YELLOW}Restaurando: {Color.WHITE}{username[:12]:<12}{Color.END} [{days:2}d] ({i}/{total})", end="", flush=True)

            # SINCRONIZAR CON EL SISTEMA (Linux)
            # Llamamos a save_users pero solo para el usuario actual para que lo cree en Linux
            if save_users({username: user_data}, full_database=db_completa):
                db_completa[username] = user_data # Guardamos en nuestra copia local
                exitos += 1
            
        # Guardado final de la base de datos completa
        save_users({}, full_database=db_completa)
        
        print(f"\n\n {Color.GREEN}✓ Restauración finalizada. {exitos}/{total} usuarios en línea.{Color.END}")
        moratech.log_action("admin", f"Restauración Online: {exitos} usuarios")

    except Exception as e:
        print(f"\n {Color.RED}✗ Error crítico: {e}{Color.END}")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def restore_local_chumo():
    """Restaurar desde backup local .txt con progreso visual"""
    clear_screen()
    print_banner()
    print(f" {Color.CYAN}RESTAURAR BACKUP LOCAL (.TXT){Color.END}\n")
    
    backup_dir = CONFIG_DIR / 'backups'
    backups = sorted(backup_dir.glob('backup_*.txt'), reverse=True)

    if not backups:
        print(f" {Color.RED}No se encontraron archivos de backup.{Color.END}")
        input("\nEnter para volver..."); return

    for i, b in enumerate(backups[:10], 1):
        with open(b, 'r') as f: count = sum(1 for l in f if l.strip())
        print(f" {Color.GREEN}[{i}]{Color.END} {b.name} {Color.GRAY}({count} users){Color.END}")

    opc = input(f"\n {Color.YELLOW}Selecciona un archivo (0 para cancelar): {Color.END}")
    if not opc or opc == '0': return

    try:
        seleccionado = backups[int(opc)-1]
        with open(seleccionado, 'r') as f: lineas = f.readlines()
        
        db_completa = load_users()
        total = len(lineas)
        exitos = 0

        print(f"\n {Color.YELLOW}🚀 Restaurando {total} usuarios...{Color.END}")

        for i, line in enumerate(lineas, 1):
            line = line.strip()
            if not line: continue
            parts = line.split(':')
            username = parts[0]
            
            # --- Lógica de parseo (Igual a la online) ---
            if 'TOKEN' in line:
                days = int(parts[3])
                user_data = {
                    "password": parts[1], "role": "user", "type": "token",
                    "display_name": parts[4], "expires": (datetime.now() + timedelta(days=days)).isoformat(),
                    "max_connections": 1, "enabled": True
                }
            else:
                days = int(parts[3])
                user_data = {
                    "password": parts[1], "role": "user", "type": "ssh",
                    "expires": (datetime.now() + timedelta(days=days)).isoformat(),
                    "max_connections": int(parts[2]), "enabled": True
                }

            # Visual y Sincronización
            print(f"\r {Color.YELLOW}Cargando: {Color.WHITE}{username[:12]:<12}{Color.END} ({i}/{total})", end="", flush=True)
            
            if save_users({username: user_data}, full_database=db_completa):
                db_completa[username] = user_data
                exitos += 1

        save_users({}, full_database=db_completa)
        print(f"\n\n {Color.GREEN}✓ {exitos} Usuarios restaurados localmente.{Color.END}")

    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")

    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

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

# CHECK USER TRATAR DE MOVERLO A OTRA CARPETA
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

#api individual
def menu_api_server():
    """Menú del servidor API"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}SERVIDOR API REST{Color.END}")
    print_line()
    
    # Verificar si hay servidor corriendo
    check_server = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
    is_running = 'api_server_individual' in check_server.stdout
    
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
            'screen', '-dmS', 'api_server_individual',
            'python3', api_script, port
        ])
        
        time.sleep(2)
        
        check = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        if 'api_server_individual' not in check.stdout:
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
            subprocess.run(['screen', '-S', 'api_server_individual', '-X', 'quit'], 
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

#api general
def menu_api_general():
    """Menú del servidor API General (Dashboard Global)"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}SERVIDOR API GENERAL (Dashboard Global){Color.END}")
    print_line()
    
    # Verificar si hay servidor corriendo
    check_server = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
    is_running = 'servidor_global' in check_server.stdout
    
    if is_running:
        # Obtener puerto actual
        try:
            port_file = CONFIG_DIR / 'api_general_port.txt'
            if port_file.exists():
                with open(port_file, 'r') as f:
                    port = f.read().strip()
            else:
                port = "9100"
        except:
            port = "9100"
        
        print(f"\n {Color.GREEN}✓ API General activo en puerto {port}{Color.END}")
        print(f" {Color.CYAN}Clave: {Color.GREEN}moratech-key{Color.END}")
        
        # Obtener IP
        try:
            ip_result = subprocess.run(['curl', '-s', 'ifconfig.me'], 
                                     capture_output=True, text=True, timeout=3)
            server_ip = ip_result.stdout.strip()
            print(f" {Color.CYAN}Dashboard: {Color.GREEN}http://{server_ip}:{port}/dashboard-global{Color.END}")
            print(f" {Color.CYAN}Panel Control: {Color.GREEN}http://{server_ip}:{port}/panel-control{Color.END}")
        except:
            pass
        
        print_line()
        print(f" {Color.GREEN}[1]{Color.END} ➮ Ver logs")
        print(f" {Color.GREEN}[2]{Color.END} ➮ Detener servidor")
    else:
        print(f"\n {Color.YELLOW}Servidor detenido{Color.END}")
        print_line()
        print(f" {Color.GREEN}[1]{Color.END} ➮ Iniciar API General")
    
    print_line()
    print(f" {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}Volver{Color.END}")
    print_line()
    
    choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
    
    if choice == '1':
        if is_running:
            view_api_general_logs()
        else:
            start_api_general_server()
    elif choice == '2' and is_running:
        stop_api_general_server()
    elif choice == '0':
        return
    else:
        menu_api_general()

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
        # directorio raíz del proyecto (uno arriba del directorio 'modules')
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        
        api_module = 'modules.api_general'  # lanzaremos con -m para evitar colisiones con módulos locales
        
        # Verificar que exista el paquete / módulo (opcionalmente)
        api_path = os.path.join(project_root, 'modules', 'api_general.py')
        if not os.path.exists(api_path):
            print(f" {Color.RED}✗ Error: api_general.py no encontrado en {api_path}{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        # Verificar Flask (instalación mínima)
        check_flask = subprocess.run(['python3', '-c', 'import flask'], 
                                    capture_output=True, text=True)
        
        if check_flask.returncode != 0:
            print(f" {Color.YELLOW}Instalando Flask...{Color.END}")
            subprocess.run(['apt-get', 'install', '-y', 'python3-flask'],
                         capture_output=True, text=True)
            print(f" {Color.GREEN}✓ Flask instalado{Color.END}")
        
        # Abrir puerto
        try:
            subprocess.run(['ufw', 'allow', port], stderr=subprocess.DEVNULL)
        except Exception:
            pass
        
        # Iniciar servidor usando -m desde el root del proyecto (evita que 'modules' sea sys.path[0])
        import time
        cmd = ['python3', '-m', api_module, port]
        subprocess.run([
            'screen', '-dmS', 'servidor_global'
        ] + cmd, cwd=project_root)
        
        time.sleep(2)
        
        # Verificar si el screen se creó
        check = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        if 'servidor_global' not in check.stdout:
            print(f"\n {Color.RED}✗ El servidor no pudo iniciar{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        # Guardar puerto
        port_file = CONFIG_DIR / 'api_general_port.txt'
        CONFIG_DIR.mkdir(exist_ok=True)
        with open(port_file, 'w') as f:
            f.write(port)
        
        # Obtener IP para mostrar URLs (intentar curl, fallback a placeholder)
        try:
            ip_result = subprocess.run(['curl', '-s', 'ifconfig.me'], 
                                     capture_output=True, text=True, timeout=3)
            server_ip = ip_result.stdout.strip() or "TU_IP"
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
    menu_api_general()

def stop_api_general_server():
    """Detener servidor API General"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}DETENER API GENERAL{Color.END}")
    print_line()
    
    confirm = input(f"\n {Color.YELLOW}¿Detener API General? (s/n): {Color.END}").strip().lower()
    
    if confirm == 's':
        try:
            subprocess.run(['screen', '-S', 'servidor_global', '-X', 'quit'], 
                         stderr=subprocess.DEVNULL)
            print(f"\n {Color.GREEN}✓ API General detenido{Color.END}")
            moratech.log_action("admin", "API General detenido")
        except Exception as e:
            print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
    else:
        print(f"\n {Color.YELLOW}Operación cancelada{Color.END}")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
    menu_api_general()

def view_api_general_logs():
    """Ver logs del API General"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}LOGS DEL API GENERAL (Ctrl+C para salir){Color.END}")
    print_line()
    
    log_file = CONFIG_DIR / 'api_general.log'
    
    if not log_file.exists():
        print(f"\n {Color.YELLOW}No hay logs todavía{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        menu_api_general()
        return
    
    try:
        subprocess.run(['tail', '-f', str(log_file)])
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
    
    menu_api_general()
#!/usr/bin/env python3
"""
Módulo USUARIOS  - Gestión de USUARIOS
"""
import time
import os
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
    """Agregar usuario SSH desde el menú"""
    print(f"\n{Color.CYAN}--- NUEVO USUARIO SSH ---{Color.END}\n")
    username = input(f"{Color.GREEN}Nombre de usuario: {Color.END}").strip()
    password = input(f"{Color.GREEN}Contraseña: {Color.END}").strip()
    days = input(f"{Color.GREEN}Días de duración: {Color.END}").strip()
    max_conn = input(f"{Color.GREEN}Máximas conexiones: {Color.END}").strip()
    
    success, msg, expires = sincronizar_usuario(
        username=username,
        password=password,
        dias=days,
        operacion='crear',
        user_type='ssh',
        max_conn=max_conn
    )
    
    if success:
        print(f"\n{Color.GREEN}✓ {msg} (Expira: {expires.strftime('%Y-%m-%d %H:%M')}){Color.END}")
        moratech.log_action("admin", f"Usuario SSH creado: {username}")
    else:
        print(f"\n{Color.RED}✗ {msg}{Color.END}")
    
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def add_token_user():
    """Agregar usuario Token desde el menú"""
    token_config = load_token_config()
    print(f"\n{Color.CYAN}--- NUEVO USUARIO TOKEN ---{Color.END}\n")
    
    if not token_config.get('token_password'):
        token_pass = input(f"{Color.GREEN}Contraseña maestra para tokens: {Color.END}").strip()
        token_config['token_password'] = token_pass
        save_token_config(token_config)
    
    display_name = input(f"{Color.GREEN}Nombre del usuario: {Color.END}").strip()
    token = input(f"{Color.GREEN}Token de acceso: {Color.END}").strip()
    days = input(f"{Color.GREEN}Días de duración: {Color.END}").strip()
    
    success, msg, expires = sincronizar_usuario(
        username=token,
        password=token_config['token_password'],
        dias=days,
        operacion='crear',
        user_type='token',
        display_name=display_name
    )
    
    if success:
        print(f"\n{Color.GREEN}✓ {msg}{Color.END}")
        moratech.log_action("admin", f"Token creado: {display_name} ({token})")
    else:
        print(f"\n{Color.RED}✗ {msg}{Color.END}")
    
    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")
    
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

    if opc == '1':  # Sumar días
        d = input(" Cantidad de días a sumar: ")
        if d.isdigit():
            success, msg, new_date = sincronizar_usuario(
                username=target,
                dias=int(d),
                operacion='renovar'
            )
            if success:
                print(f" {Color.GREEN}✓ {msg} -> {new_date.strftime('%Y-%m-%d')}{Color.END}")
            else:
                print(f" {Color.RED}✗ {msg}{Color.END}")

    elif opc == '2':  # Reiniciar días
        d = input(" Nuevos días totales (desde hoy): ")
        if d.isdigit():
            success, msg, new_date = sincronizar_usuario(
                username=target,
                dias=int(d),
                operacion='reiniciar'
            )
            if success:
                print(f" {Color.GREEN}✓ {msg} -> {new_date.strftime('%Y-%m-%d')}{Color.END}")
            else:
                print(f" {Color.RED}✗ {msg}{Color.END}")

    elif opc == '3':  # Cambiar contraseña
        new_p = input(" Nueva contraseña: ").strip()
        if new_p:
            success, msg, _ = sincronizar_usuario(
                username=target,
                password=new_p,
                dias=0,  # Mantiene días actuales
                operacion='renovar'
            )
            if success:
                print(f" {Color.GREEN}✓ Contraseña actualizada{Color.END}")
            else:
                print(f" {Color.RED}✗ {msg}{Color.END}")
    
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

#BORRADO FISICO FUNCION PRINCIPAL
def ejecutar_borrado_fisico(username):
    """
    FUNCIÓN MAESTRA DE BORRADO - PUNTO ÚNICO DE ELIMINACIÓN
    
    Esta función hace TODO el proceso de borrado:
    1. Elimina del sistema Linux (userdel mata procesos automáticamente)
    2. Elimina del JSON
    3. Retorna éxito/fallo
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Validación básica
        if not username or username.strip() == '':
            return False, "Nombre de usuario vacío"
        
        if username == "admin":
            return False, "No se puede eliminar al administrador"
        
        # 0.1 KILL DEL USUARIO
        subprocess.run(
            ['pkill', '-9', '-u', username],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # 1. BORRADO DE LINUX
        # userdel con -f (fuerza) y -r (borra home) automáticamente mata procesos
        # No hace falta pkill por separado
        result = subprocess.run(
            ['userdel', '-f', '-r', username],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Note: userdel puede retornar != 0 si el usuario no existe en Linux
        # pero eso no es un error crítico, seguimos para limpiarlo del JSON
        
        # 2. BORRADO DEL JSON
        users = load_users()
        
        if username not in users:
            # No está en JSON pero intentamos borrarlo de Linux de todas formas
            # Retornamos advertencia pero no es error
            return True, f"Usuario no estaba en base de datos (limpiado de sistema)"
        
        # Eliminar del diccionario
        del users[username]
        
        # 3. GUARDAR JSON DIRECTAMENTE (sin usar save_users para evitar sync a Linux)
        # Ya lo borramos de Linux, solo actualizamos el archivo
        import tempfile
        import shutil
        
        temp_fd, temp_path = tempfile.mkstemp(dir=str(CONFIG_DIR), text=True)
        try:
            with os.fdopen(temp_fd, 'w') as f:
                json.dump(users, f, indent=4)
            shutil.move(temp_path, str(USERS_FILE))
        except Exception as e:
            # Si falla el guardado, intentar limpiar el temporal
            try:
                os.unlink(temp_path)
            except:
                pass
            return False, f"Error guardando JSON: {str(e)}"
        
        return True, "Usuario eliminado completamente"
        
    except Exception as e:
        return False, f"Error crítico: {str(e)}"

#funcion que borra a un usuario ESPECIFICO
def borrar_usuario_especifico():
    """Opción de menú: Borrar un solo usuario por nombre"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}BORRAR USUARIO ESPECÍFICO{Color.END}")
    print_line()
    
    username = input(f"\n {Color.GREEN}Nombre de usuario a eliminar: {Color.END}").strip()
    
    if not username:
        print(f" {Color.RED}✗ Nombre vacío{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    print(f"\n {Color.YELLOW}⏳ Eliminando {username}...{Color.END}", end="\r")
    
    success, message = ejecutar_borrado_fisico(username)
    
    print(f"{' ' * 50}\r", end="")  # Limpiar línea
    
    if success:
        print(f" {Color.GREEN}✓ {message}{Color.END}")
        moratech.log_action("admin", f"Usuario eliminado: {username}")
    else:
        print(f" {Color.RED}✗ {message}{Color.END}")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

#BORRADO ITERATIVO de 1x1
def borrar_iterativo():
    """Opción de menú: Preguntar uno por uno"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}BORRADO ITERATIVO{Color.END}")
    print_line()
    
    users = load_users()
    
    if len(users) <= 1:  # Solo admin
        print(f"\n {Color.YELLOW}No hay usuarios para eliminar{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    deleted_count = 0
    print(f"\n {Color.CYAN}Iniciando revisión de usuarios...{Color.END}\n")
    
    for username in list(users.keys()):
        if username == "admin":
            continue
        
        user_data = users[username]
        user_type = user_data.get('type', 'ssh')
        display_name = user_data.get('display_name', username)
        
        print(f" {Color.YELLOW}Usuario: {Color.WHITE}{display_name} ({user_type}){Color.END}")
        confirm = input(f" {Color.CYAN}¿Eliminar? (s/n): {Color.END}").strip().lower()
        
        if confirm == 's':
            print(f"   {Color.RED}Eliminando...{Color.END}", end="\r")
            success, message = ejecutar_borrado_fisico(username)
            
            if success:
                deleted_count += 1
                print(f"   {Color.GREEN}✓ Eliminado{Color.END}      ")
            else:
                print(f"   {Color.RED}✗ Error: {message}{Color.END}")
        else:
            print(f"   {Color.YELLOW}Omitido{Color.END}")
        print()
    
    if deleted_count > 0:
        print(f" {Color.GREEN}✓ Proceso terminado. {deleted_count} usuario(s) eliminado(s){Color.END}")
        moratech.log_action("admin", f"Borrado iterativo: {deleted_count} usuarios")
    else:
        print(f" {Color.YELLOW}No se eliminó ningún usuario{Color.END}")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

#BORRAR SOLO USUARIOS EXPIRADOS
def borrar_expirados():
    """Opción de menú: Limpiar usuarios expirados"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}LIMPIAR USUARIOS EXPIRADOS{Color.END}")
    print_line()
    
    users = load_users()
    now = datetime.now(CR_TZ)
    
    # Encontrar expirados
    expirados = []
    for username, user_data in users.items():
        if username == 'admin':
            continue
        
        expires = user_data.get('expires')
        if expires:
            exp_date = datetime.fromisoformat(expires).replace(tzinfo=CR_TZ)
            if now > exp_date:
                dias_vencido = (now - exp_date).days
                expirados.append((username, dias_vencido))
    
    if not expirados:
        print(f"\n {Color.GREEN}✨ No hay usuarios expirados{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    total = len(expirados)
    print(f"\n {Color.YELLOW}Se encontraron {total} usuario(s) expirado(s){Color.END}")
    print(f" {Color.CYAN}Iniciando limpieza...{Color.END}\n")
    
    eliminados = 0
    for i, (username, dias_vencido) in enumerate(expirados, 1):
        print(f"\r {Color.RED}Eliminando: {Color.WHITE}{username[:20]:<20}{Color.END} [vencido {dias_vencido}d] ({i}/{total})", end="", flush=True)
        
        success, _ = ejecutar_borrado_fisico(username)
        if success:
            eliminados += 1
    
    print(f"\n\n {Color.GREEN}✓ Limpieza completada: {eliminados}/{total} eliminados{Color.END}")
    moratech.log_action("admin", f"Limpieza de expirados: {eliminados} usuarios")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

#BORRAR TODOS LOS USUARIOS DEL SISTEMA
def borrar_todos():
    """Opción de menú: Eliminar TODOS los usuarios"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.RED}⚠️  ELIMINAR TODOS LOS USUARIOS ⚠️{Color.END}")
    print_line()
    
    users = load_users()
    total = len([u for u in users.keys() if u != "admin"])
    
    if total == 0:
        print(f"\n {Color.YELLOW}No hay usuarios para eliminar{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    print(f"\n {Color.RED}Esto eliminará {total} usuario(s) del sistema{Color.END}")
    confirm = input(f"\n {Color.YELLOW}Escribe 'CONFIRMAR' para proceder: {Color.END}").strip()
    
    if confirm != "CONFIRMAR":
        print(f" {Color.YELLOW}Operación cancelada{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    print(f"\n {Color.CYAN}Iniciando eliminación masiva...{Color.END}\n")
    
    a_borrar = [u for u in users.keys() if u != "admin"]
    eliminados = 0
    
    for i, username in enumerate(a_borrar, 1):
        print(f"\r {Color.RED}Eliminando: {Color.WHITE}{username[:20]:<20}{Color.END} ({i}/{total})", end="", flush=True)
        
        success, _ = ejecutar_borrado_fisico(username)
        if success:
            eliminados += 1
    
    print(f"\n\n {Color.GREEN}✓ Eliminación masiva completada: {eliminados}/{total}{Color.END}")
    moratech.log_action("admin", f"Borrado total: {eliminados} usuarios")
    
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

            # --- CÁLCULO DE STATUS ---
            if expires:
                expire_date = datetime.fromisoformat(expires).replace(tzinfo=CR_TZ)  
                now_cr = datetime.now(CR_TZ)
                fecha_txt = f"[{expire_date.strftime('%d/%m/%Y')}]"
                if now_cr > expire_date:
                    status = f"{Color.RED}EXPIRADO{Color.END}"
                else:
                    days = (expire_date - now_cr).days + 1
                    status = f"{Color.GREEN}{days} días{Color.END}"
            else:
                status = f"{Color.CYAN}ILIMITADO{Color.END}"
            
            # --- NIVEL 1: Nombre y Tipo ---
            if user_type == 'token':
                display_name = data.get('display_name', 'Sin Nombre')
                print(f" {Color.WHITE}{display_name:<18}{Color.END} - {Color.MAGENTA}(TOKEN){Color.END} - {Color.YELLOW}{fecha_txt}{Color.END}")
                #print(f" {Color.WHITE}{display_name}{Color.END} - {Color.MAGENTA}(TOKEN){Color.END}")
                detail_id = username
            else:
                print(f" {Color.WHITE}{username:<18}{Color.END} - {Color.BLUE}(SSH){Color.END} - {Color.YELLOW}{fecha_txt}{Color.END}")
                #print(f" {Color.WHITE}{username}{Color.END} - {Color.BLUE}(SSH){Color.END}")
                detail_id = username


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
            expire_dt = datetime.fromisoformat(expires).replace(tzinfo=CR_TZ)
            now = datetime.now(CR_TZ)

            # Formateamos la fecha para mostrarla SIEMPRE
            fecha_vence_str = expire_dt.strftime('%d/%m/%Y %H:%M')

            if now > expire_dt:
                # Caso: EXPIRADO (Aun así calculamos los días con el +1 por coherencia)
                diff = (expire_dt - now).days + 1
                dias_restantes = f"{Color.RED}EXPIRADO ({diff} días){Color.END}"
                estado_visual = f"{Color.RED}● INACTIVO / CADUCADO (Venció: {fecha_vence_str}){Color.END}"
            else:
                # Caso: ACTIVO (Aplicamos tu +1)
                diff = (expire_dt - now).days + 1
                dias_restantes = f"{Color.GREEN}{diff} días{Color.END}"
                estado_visual = f"{Color.GREEN}● ACTIVO (Vence: {fecha_vence_str}){Color.END}"
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

#RE-INICIAR CONTRASEÑA DE TOKEN #MEJORADA
def reset_token_password():
    """Resetear contraseña de tokens con progreso visual"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}RESETEAR CONTRASEÑA DE TOKENS{Color.END}")
    print_line()
    
    new_pass = input(f"\n {Color.GREEN}Nueva contraseña para tokens: {Color.END}").strip()
    
    if not new_pass:
        print(f" {Color.RED}✗ Contraseña vacía{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    # Guardar nueva contraseña maestra
    token_config = load_token_config()
    token_config['token_password'] = new_pass
    save_token_config(token_config)
    
    # Buscar todos los usuarios token
    users = load_users()
    tokens = [u for u, d in users.items() if d.get('type') == 'token']
    
    if not tokens:
        print(f"\n {Color.YELLOW}No hay usuarios token para actualizar{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    total = len(tokens)
    print(f"\n {Color.CYAN}Actualizando {total} token(s)...{Color.END}\n")
    
    actualizados = 0
    for i, username in enumerate(tokens, 1):
        print(f"\r {Color.YELLOW}Actualizando: {Color.WHITE}{username[:20]:<20}{Color.END} ({i}/{total})", end="", flush=True)
        
        # Actualizar contraseña en JSON y Linux
        users[username]['password'] = new_pass
        
        # Usar chpasswd para actualizar en Linux
        subprocess.run(
            ['chpasswd'],
            input=f"{username}:{new_pass}\n",
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        actualizados += 1
    
    # Guardar JSON actualizado
    import tempfile
    import shutil
    temp_fd, temp_path = tempfile.mkstemp(dir=str(CONFIG_DIR), text=True)
    try:
        with os.fdopen(temp_fd, 'w') as f:
            json.dump(users, f, indent=4)
        shutil.move(temp_path, str(USERS_FILE))
    except:
        try:
            os.unlink(temp_path)
        except:
            pass
    
    print(f"\n\n {Color.GREEN}✓ Contraseña actualizada en {actualizados}/{total} tokens{Color.END}")
    print(f" {Color.YELLOW}Nueva contraseña: {new_pass}{Color.END}")
    moratech.log_action("admin", f"Contraseña de tokens reseteada ({actualizados} usuarios)")
    
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

def sincronizar_usuario(username, password=None, dias=None, operacion='crear', user_type='ssh', max_conn=1, display_name=None):
    """
    FUNCIÓN MAESTRA UNIFICADA - Maneja crear/renovar/reiniciar usuarios
    
    Args:
        username: Nombre de usuario o token
        password: Contraseña (solo para crear/modificar)
        dias: Días de duración
        operacion: 'crear', 'renovar', 'reiniciar'
        user_type: 'ssh' o 'token'
        max_conn: Máximas conexiones (solo SSH)
        display_name: Nombre visible (solo tokens)
    
    Returns:
        tuple: (success: bool, message: str, expires_datetime: datetime)
    """
    try:
        users = load_users()
        now = datetime.now(CR_TZ)
        
        # ==================== VALIDACIONES ====================
        if not username or username.strip() == '':
            return False, "Nombre de usuario vacío", None
        
        if operacion == 'crear' and username in users:
            return False, "Usuario ya existe", None
        
        if operacion in ['renovar', 'reiniciar'] and username not in users:
            return False, "Usuario no encontrado", None
        
        # Convertir días a int
        try:
            dias_int = int(dias) if dias is not None else 0
        except:
            return False, "Días inválidos", None
        
        # ==================== CALCULAR FECHA DE EXPIRACIÓN ====================
        if operacion == 'crear':
            # CREAR: Hoy + X días a las 6pm
            expire_date = (now.date() + timedelta(days=dias_int))
            expires_dt = datetime.combine(expire_date, time(18, 0, 0)).replace(tzinfo=CR_TZ)
        
        elif operacion == 'renovar':
            # RENOVAR: Sumar días a la fecha actual o desde hoy si ya expiró
            user_data = users[username]
            if user_data.get('expires'):
                current_expire = datetime.fromisoformat(user_data['expires']).replace(tzinfo=CR_TZ)
                base_date = current_expire if current_expire > now else now
            else:
                base_date = now
            
            expire_date = (base_date + timedelta(days=dias_int)).date()
            expires_dt = datetime.combine(expire_date, time(18, 0, 0)).replace(tzinfo=CR_TZ)
        
        elif operacion == 'reiniciar':
            # REINICIAR: Desde hoy + X días a las 6pm
            expire_date = (now.date() + timedelta(days=dias_int))
            expires_dt = datetime.combine(expire_date, time(18, 0, 0)).replace(tzinfo=CR_TZ)
        
        expires_iso = expires_dt.isoformat()
        
        # ==================== PREPARAR DATOS DEL USUARIO ====================
        if operacion == 'crear':
            # Usuario nuevo
            user_data = {
                "password": str(password),
                "role": "user",
                "type": user_type,
                "created": now.isoformat(),
                "expires": expires_iso,
                "max_connections": int(max_conn),
                "enabled": True
            }
            
            if user_type == "token" and display_name:
                user_data["display_name"] = display_name
                user_data["original_token"] = username
            
            users[username] = user_data
        
        else:
            # Renovar o Reiniciar (solo actualizar fecha y activar)
            users[username]['expires'] = expires_iso
            users[username]['enabled'] = True
            
            # Si se pasa contraseña nueva, actualizarla
            if password:
                users[username]['password'] = str(password)
        
        # ==================== SINCRONIZAR A LINUX ====================
        # 1. Crear usuario en Linux si no existe
        check_user = subprocess.run(
            ['id', username],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        if check_user.returncode != 0:
            # Usuario no existe en Linux, crearlo
            subprocess.run(
                ['useradd', '-M', '-s', '/bin/false', username],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        
        # 2. Actualizar contraseña
        current_password = users[username]['password']
        subprocess.run(
            ['chpasswd'],
            input=f"{username}:{current_password}\n",
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # 3. Configurar expiración en Linux (+1 día de margen)
        linux_expire_date = (expires_dt + timedelta(days=1)).strftime('%Y-%m-%d')
        subprocess.run(
            ['usermod', '-e', linux_expire_date, '-U', '-s', '/bin/false', username],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # ==================== GUARDAR JSON ====================
        import tempfile
        import shutil
        
        temp_fd, temp_path = tempfile.mkstemp(dir=str(CONFIG_DIR), text=True)
        try:
            with os.fdopen(temp_fd, 'w') as f:
                json.dump(users, f, indent=4)
            shutil.move(temp_path, str(USERS_FILE))
        except Exception as e:
            try:
                os.unlink(temp_path)
            except:
                pass
            return False, f"Error guardando JSON: {str(e)}", None
        
        # ==================== RETORNO EXITOSO ====================
        mensaje = {
            'crear': 'Usuario creado correctamente',
            'renovar': 'Usuario renovado correctamente',
            'reiniciar': 'Días reiniciados correctamente'
        }
        
        return True, mensaje[operacion], expires_dt
    
    except Exception as e:
        return False, f"Error: {str(e)}", None

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
        print_line()
        print(f" {Color.GREEN}[2]{Color.END} ➮ Restaurar usuarios [EN LÍNEA - CHUMO - BORRON]")
        print(f" {Color.GREEN}[3]{Color.END} ➮ Restaurar usuarios [LOCALMENTE - CHUMO - BORRON]")
        print_line()
        print(f" {Color.GREEN}[4]{Color.END} ➮ Restaurar usuarios [EN LÍNEA - CHUMO - FUSIONAR]")
        print(f" {Color.GREEN}[5]{Color.END} ➮ Restaurar usuarios [LOCALMENTE - CHUMO - FUSIONAR]")
        print_line()
        print(f" {Color.GREEN}[6]{Color.END} ➮ Ver backups locales")
        print_line()
        print(f" {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}Volver{Color.END}")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
        
        if choice == '1':
            backup_online_chumo()
        elif choice == '2':
            restore_online_chumo_eliminar()
        elif choice == '3':
            restore_local_chumo_eliminar()
        elif choice == '4':
            restore_online_chumo_fusionar()
        elif choice == '5':
            restore_local_chumo_fusionar()
        elif choice == '6':
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
        
        timestamp = datetime.now(CR_TZ).strftime('%Y%m%d_%H%M%S')  # ← AGREGADO CR_TZ
        backup_filename = f'backup_{timestamp}.txt'
        backup_path = backup_dir / backup_filename
        
        # Leer usuarios actuales
        users = load_users()
        now_cr = datetime.now(CR_TZ)  # ← AGREGADO
        
        # Convertir a formato texto
        backup_lines = []
        for username, data in users.items():
            user_type = data.get('type', 'ssh')
            password = data.get('password', '')
            max_conn = data.get('max_connections', 1)
            
            # Calcular días restantes
            expires = data.get('expires')
            if expires:
                expire_date = datetime.fromisoformat(expires).replace(tzinfo=CR_TZ)  # ← AGREGADO
                
                # Días restantes desde AHORA hasta la expiración
                diff = (expire_date - now_cr).days  # ← CAMBIADO
                
                # IMPORTANTE: Sumar +1 para compatibilidad con script de chumo
                # El restore resta 1, así que guardamos con +1
                days = max(0, diff + 1)  # ← CAMBIADO
            else:
                days = 0
            
            if user_type == 'token':
                # Formato TOKEN: {token}:{contraseña_token}:TOKEN:{dias}:{nombre_visual}
                display_name = data.get('display_name', username)
                line = f"{username}:{password}:TOKEN:{days}:{display_name}"
            else:
                # Formato SSH: {nombre}:{contraseña}:{max_conexiones}:{dias}
                line = f"{username}:{password}:{max_conn}:{days}"
            
            backup_lines.append(line)
        
        # Guardar en archivo
        with open(backup_path, 'w') as f:
            f.write('\n'.join(backup_lines))
        
        print(f" {Color.GREEN}✓ Backup creado: {backup_filename}{Color.END}")
        print(f" {Color.CYAN}Total usuarios: {len(users)}{Color.END}")
        
        # Obtener IP del servidor
        try:
            ip_result = subprocess.run(['curl', '-s', '-4', 'ifconfig.me'], 
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

#RESTARACION COMPLETA BORRON Y CUENTA NUEVA"
def restore_online_chumo_eliminar():
    """Restaurar usuarios desde servidor HTTP - BORRÓN Y CUENTA NUEVA"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}RESTAURAR USUARIOS EN LÍNEA{Color.END}")
    print_line()
    
    # Mostrar última URL
    try:
        url_file = CONFIG_DIR / 'last_backup_url.txt'
        if url_file.exists():
            with open(url_file, 'r') as f:
                last_url = f.read().strip()
                print(f"\n {Color.YELLOW}Último backup:{Color.END}")
                print(f" {Color.GRAY}{last_url}{Color.END}")
    except:
        pass
    
    backup_url = input(f"\n {Color.GREEN}Enlace del backup: {Color.END}").strip()
    
    if not backup_url:
        print(f" {Color.YELLOW}Operación cancelada{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    # ⚠️ ADVERTENCIA DE BORRADO
    print(f"\n {Color.RED}⚠️  ADVERTENCIA ⚠️{Color.END}")
    print(f" {Color.YELLOW}Esto eliminará TODOS los usuarios actuales{Color.END}")
    print(f" {Color.YELLOW}y los reemplazará con el backup{Color.END}")
    confirm = input(f"\n {Color.RED}Escribe 'CONFIRMAR' para proceder: {Color.END}").strip()
    
    if confirm != "CONFIRMAR":
        print(f" {Color.YELLOW}Operación cancelada{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    print(f"\n {Color.YELLOW}⏳ Descargando backup...{Color.END}", end="\r")
    
    try:
        import requests
        response = requests.get(backup_url, timeout=10)
        
        if response.status_code != 200:
            print(f" {Color.RED}✗ Error descargando (HTTP {response.status_code}){Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        backup_content = response.text.strip()
        if not backup_content:
            print(f" {Color.RED}✗ Backup vacío{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        # ==================== PASO 1: BORRAR TODOS LOS USUARIOS ====================
        print(f" {Color.GREEN}✓ Descarga exitosa{Color.END}")
        print(f"\n {Color.RED}Eliminando usuarios actuales...{Color.END}\n")
        
        users_actuales = load_users()
        a_borrar = [u for u in users_actuales.keys() if u != "admin"]
        
        for i, username in enumerate(a_borrar, 1):
            print(f"\r {Color.RED}Eliminando: {Color.WHITE}{username[:20]:<20}{Color.END} ({i}/{len(a_borrar)})", end="", flush=True)
            ejecutar_borrado_fisico(username)
        
        if a_borrar:
            print(f"\n {Color.GREEN}✓ {len(a_borrar)} usuario(s) eliminado(s){Color.END}\n")
        
        # ==================== PASO 2: RESTAURAR DESDE BACKUP ====================
        lineas = backup_content.split('\n')
        total = len([l for l in lineas if l.strip()])
        exitos = 0
        
        print(f" {Color.CYAN}Restaurando {total} usuario(s)...{Color.END}\n")
        
        token_config = load_token_config()
        if not token_config.get('token_password'):
            token_config['token_password'] = 'default123'
            save_token_config(token_config)
        
        for i, line in enumerate(lineas, 1):
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(':')
            if len(parts) < 4:
                continue
            
            username = parts[0]
            
            # Parsear según tipo
            if 'TOKEN' in line and len(parts) >= 5:
                # TOKEN: {token}:{pass}:TOKEN:{dias}:{nombre}
                password = token_config['token_password']
                days = max(0, int(parts[3]) - 1)
                display_name = parts[4]
                user_type = 'token'
                max_conn = 1
            else:
                # SSH: {nombre}:{pass}:{conn}:{dias}
                password = parts[1]
                max_conn = int(parts[2])
                days = max(0, int(parts[3]) - 1)
                display_name = None
                user_type = 'ssh'
            
            # Visual
            print(f"\r {Color.YELLOW}Restaurando: {Color.WHITE}{username[:20]:<20}{Color.END} [{days:2}d] ({i}/{total})", end="", flush=True)
            
            # Sincronizar usando la función maestra
            success, msg, expires = sincronizar_usuario(
                username=username,
                password=password,
                dias=days,
                operacion='crear',
                user_type=user_type,
                max_conn=max_conn,
                display_name=display_name
            )
            
            if success:
                exitos += 1
        
        print(f"\n\n {Color.GREEN}✓ Restauración completada: {exitos}/{total} usuarios{Color.END}")
        moratech.log_action("admin", f"Restore Online: {exitos} usuarios (BORRÓN Y CUENTA NUEVA)")
        
        # Guardar URL para próxima vez
        try:
            with open(url_file, 'w') as f:
                f.write(backup_url)
        except:
            pass
    
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

#RESTAURACION FUSIONAR BACKUP (QUEDA LA DEL BACKUP)
def restore_online_chumo_fusionar():
    """Restaurar usuarios desde servidor HTTP - FUSIÓN INTELIGENTE"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}FUSIONAR BACKUP EN LÍNEA{Color.END}")
    print_line()
    
    # Mostrar última URL
    try:
        url_file = CONFIG_DIR / 'last_backup_url.txt'
        if url_file.exists():
            with open(url_file, 'r') as f:
                last_url = f.read().strip()
                print(f"\n {Color.YELLOW}Último backup:{Color.END}")
                print(f" {Color.GRAY}{last_url}{Color.END}")
    except:
        pass
    
    backup_url = input(f"\n {Color.GREEN}Enlace del backup: {Color.END}").strip()
    
    if not backup_url:
        print(f" {Color.YELLOW}Operación cancelada{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    # ⚠️ EXPLICACIÓN DE FUSIÓN
    print(f"\n {Color.CYAN}ℹ️  MODO FUSIÓN:{Color.END}")
    print(f" {Color.GREEN}• Actualiza días según backup (incluso si baja){Color.END}")
    print(f" {Color.GREEN}• Crea usuarios nuevos del backup{Color.END}")
    print(f" {Color.RED}• Elimina usuarios que NO están en el backup{Color.END}")
    confirm = input(f"\n {Color.YELLOW}¿Continuar? (s/n): {Color.END}").strip().lower()
    
    if confirm != 's':
        print(f" {Color.YELLOW}Operación cancelada{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    print(f"\n {Color.YELLOW}⏳ Descargando backup...{Color.END}", end="\r")
    
    try:
        import requests
        response = requests.get(backup_url, timeout=10)
        
        if response.status_code != 200:
            print(f" {Color.RED}✗ Error descargando (HTTP {response.status_code}){Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        backup_content = response.text.strip()
        if not backup_content:
            print(f" {Color.RED}✗ Backup vacío{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        print(f" {Color.GREEN}✓ Descarga exitosa{Color.END}")
        
        # ==================== PARSEAR BACKUP ====================
        lineas = backup_content.split('\n')
        usuarios_backup = {}
        
        token_config = load_token_config()
        if not token_config.get('token_password'):
            token_config['token_password'] = 'default123'
            save_token_config(token_config)
        
        for line in lineas:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(':')
            if len(parts) < 4:
                continue
            
            username = parts[0]
            
            if 'TOKEN' in line and len(parts) >= 5:
                usuarios_backup[username] = {
                    'password': token_config['token_password'],
                    'days': max(0, int(parts[3]) - 1),
                    'display_name': parts[4],
                    'user_type': 'token',
                    'max_conn': 1
                }
            else:
                usuarios_backup[username] = {
                    'password': parts[1],
                    'days': max(0, int(parts[3]) - 1),
                    'display_name': None,
                    'user_type': 'ssh',
                    'max_conn': int(parts[2])
                }
        
        # ==================== CARGAR USUARIOS ACTUALES ====================
        users_actuales = load_users()
        usuarios_sistema = {u: data for u, data in users_actuales.items() if u != "admin"}
        
        # ==================== CALCULAR DIFERENCIAS ====================
        en_backup = set(usuarios_backup.keys())
        en_sistema = set(usuarios_sistema.keys())
        
        a_crear = en_backup - en_sistema
        a_actualizar = en_backup & en_sistema
        a_eliminar = en_sistema - en_backup
        
        print(f"\n {Color.CYAN}📊 Análisis:{Color.END}")
        print(f" {Color.GREEN}Crear: {len(a_crear)}{Color.END}")
        print(f" {Color.YELLOW}Actualizar: {len(a_actualizar)}{Color.END}")
        print(f" {Color.RED}Eliminar: {len(a_eliminar)}{Color.END}")
        
        confirm = input(f"\n {Color.YELLOW}¿Ejecutar fusión? (s/n): {Color.END}").strip().lower()
        if confirm != 's':
            print(f" {Color.YELLOW}Operación cancelada{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        # ==================== EJECUTAR FUSIÓN ====================
        creados = 0
        actualizados = 0
        eliminados = 0
        
        # 1. CREAR NUEVOS
        if a_crear:
            print(f"\n {Color.GREEN}Creando usuarios nuevos...{Color.END}\n")
            for i, username in enumerate(a_crear, 1):
                data = usuarios_backup[username]
                print(f"\r {Color.GREEN}Creando: {Color.WHITE}{username[:20]:<20}{Color.END} [{data['days']:2}d] ({i}/{len(a_crear)})", end="", flush=True)
                
                success, msg, expires = sincronizar_usuario(
                    username=username,
                    password=data['password'],
                    dias=data['days'],
                    operacion='crear',
                    user_type=data['user_type'],
                    max_conn=data['max_conn'],
                    display_name=data['display_name']
                )
                
                if success:
                    creados += 1
            print()
        
        # 2. ACTUALIZAR EXISTENTES
        if a_actualizar:
            print(f"\n {Color.YELLOW}Actualizando usuarios...{Color.END}\n")
            for i, username in enumerate(a_actualizar, 1):
                data = usuarios_backup[username]
                print(f"\r {Color.YELLOW}Actualizando: {Color.WHITE}{username[:20]:<20}{Color.END} [{data['days']:2}d] ({i}/{len(a_actualizar)})", end="", flush=True)
                
                # Usar 'reiniciar' para sobrescribir días exactos del backup
                success, msg, expires = sincronizar_usuario(
                    username=username,
                    dias=data['days'],
                    operacion='reiniciar'
                )
                
                if success:
                    actualizados += 1
            print()
        
        # 3. ELIMINAR HUÉRFANOS
        if a_eliminar:
            print(f"\n {Color.RED}Eliminando usuarios huérfanos...{Color.END}\n")
            for i, username in enumerate(a_eliminar, 1):
                print(f"\r {Color.RED}Eliminando: {Color.WHITE}{username[:20]:<20}{Color.END} ({i}/{len(a_eliminar)})", end="", flush=True)
                ejecutar_borrado_fisico(username)
                eliminados += 1
            print()
        
        # ==================== RESUMEN ====================
        print(f"\n {Color.GREEN}✓ Fusión completada:{Color.END}")
        print(f" {Color.GREEN}Creados: {creados}/{len(a_crear)}{Color.END}")
        print(f" {Color.YELLOW}Actualizados: {actualizados}/{len(a_actualizar)}{Color.END}")
        print(f" {Color.RED}Eliminados: {eliminados}/{len(a_eliminar)}{Color.END}")
        
        moratech.log_action("admin", f"Fusión Online: +{creados} ~{actualizados} -{eliminados}")
        
        # Guardar URL
        try:
            with open(url_file, 'w') as f:
                f.write(backup_url)
        except:
            pass
    
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

#RESTARACION COMPLETA BORRON Y CUENTA NUEVA"
def restore_local_chumo_eliminar():
    """Restaurar desde backup local - BORRÓN Y CUENTA NUEVA"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}RESTAURAR BACKUP LOCAL (.TXT){Color.END}")
    print_line()
    
    backup_dir = CONFIG_DIR / 'backups'
    backups = sorted(backup_dir.glob('backup_*.txt'), reverse=True)
    
    if not backups:
        print(f"\n {Color.RED}No se encontraron backups locales{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    print(f"\n {Color.CYAN}Backups disponibles:{Color.END}\n")
    for i, b in enumerate(backups[:10], 1):
        with open(b, 'r') as f:
            count = sum(1 for l in f if l.strip())
        print(f" {Color.GREEN}[{i}]{Color.END} {b.name} {Color.GRAY}({count} usuarios){Color.END}")
    
    print(f"\n {Color.GREEN}[0]{Color.END} Cancelar")
    opc = input(f"\n {Color.YELLOW}Selecciona: {Color.END}").strip()
    
    if not opc or opc == '0':
        return
    
    try:
        seleccionado = backups[int(opc) - 1]
    except:
        print(f" {Color.RED}✗ Opción inválida{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    # ⚠️ ADVERTENCIA
    print(f"\n {Color.RED}⚠️  ADVERTENCIA ⚠️{Color.END}")
    print(f" {Color.YELLOW}Esto eliminará TODOS los usuarios actuales{Color.END}")
    print(f" {Color.YELLOW}Backup: {seleccionado.name}{Color.END}")
    confirm = input(f"\n {Color.RED}Escribe 'CONFIRMAR' para proceder: {Color.END}").strip()
    
    if confirm != "CONFIRMAR":
        print(f" {Color.YELLOW}Operación cancelada{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    try:
        # ==================== PASO 1: BORRAR USUARIOS ACTUALES ====================
        print(f"\n {Color.RED}Eliminando usuarios actuales...{Color.END}\n")
        
        users_actuales = load_users()
        a_borrar = [u for u in users_actuales.keys() if u != "admin"]
        
        for i, username in enumerate(a_borrar, 1):
            print(f"\r {Color.RED}Eliminando: {Color.WHITE}{username[:20]:<20}{Color.END} ({i}/{len(a_borrar)})", end="", flush=True)
            ejecutar_borrado_fisico(username)
        
        if a_borrar:
            print(f"\n {Color.GREEN}✓ {len(a_borrar)} usuario(s) eliminado(s){Color.END}\n")
        
        # ==================== PASO 2: RESTAURAR BACKUP ====================
        with open(seleccionado, 'r') as f:
            lineas = f.readlines()
        
        total = len([l for l in lineas if l.strip()])
        exitos = 0
        
        print(f" {Color.CYAN}Restaurando {total} usuario(s)...{Color.END}\n")
        
        token_config = load_token_config()
        if not token_config.get('token_password'):
            token_config['token_password'] = 'default123'
            save_token_config(token_config)
        
        for i, line in enumerate(lineas, 1):
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(':')
            if len(parts) < 4:
                continue
            
            username = parts[0]
            
            # Parsear
            if 'TOKEN' in line and len(parts) >= 5:
                password = token_config['token_password']
                days = max(0, int(parts[3]) - 1)
                display_name = parts[4]
                user_type = 'token'
                max_conn = 1
            else:
                password = parts[1]
                max_conn = int(parts[2])
                days = max(0, int(parts[3]) - 1)
                display_name = None
                user_type = 'ssh'
            
            # Visual
            print(f"\r {Color.YELLOW}Restaurando: {Color.WHITE}{username[:20]:<20}{Color.END} [{days:2}d] ({i}/{total})", end="", flush=True)
            
            # Sincronizar
            success, msg, expires = sincronizar_usuario(
                username=username,
                password=password,
                dias=days,
                operacion='crear',
                user_type=user_type,
                max_conn=max_conn,
                display_name=display_name
            )
            
            if success:
                exitos += 1
        
        print(f"\n\n {Color.GREEN}✓ Restauración completada: {exitos}/{total} usuarios{Color.END}")
        moratech.log_action("admin", f"Restore Local: {exitos} usuarios ({seleccionado.name})")
    
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

#FUSONAR BACKUP QUEDA EL BACKUP COMO ORIGINAL
def restore_local_chumo_fusionar():
    """Restaurar desde backup local - FUSIÓN INTELIGENTE"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}FUSIONAR BACKUP LOCAL{Color.END}")
    print_line()
    
    backup_dir = CONFIG_DIR / 'backups'
    backups = sorted(backup_dir.glob('backup_*.txt'), reverse=True)
    
    if not backups:
        print(f"\n {Color.RED}No se encontraron backups locales{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    print(f"\n {Color.CYAN}Backups disponibles:{Color.END}\n")
    for i, b in enumerate(backups[:10], 1):
        with open(b, 'r') as f:
            count = sum(1 for l in f if l.strip())
        print(f" {Color.GREEN}[{i}]{Color.END} {b.name} {Color.GRAY}({count} usuarios){Color.END}")
    
    print(f"\n {Color.GREEN}[0]{Color.END} Cancelar")
    opc = input(f"\n {Color.YELLOW}Selecciona: {Color.END}").strip()
    
    if not opc or opc == '0':
        return
    
    try:
        seleccionado = backups[int(opc) - 1]
    except:
        print(f" {Color.RED}✗ Opción inválida{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    # ⚠️ EXPLICACIÓN
    print(f"\n {Color.CYAN}ℹ️  MODO FUSIÓN:{Color.END}")
    print(f" {Color.GREEN}• Actualiza días según backup{Color.END}")
    print(f" {Color.GREEN}• Crea usuarios nuevos{Color.END}")
    print(f" {Color.RED}• Elimina usuarios no presentes{Color.END}")
    confirm = input(f"\n {Color.YELLOW}¿Continuar? (s/n): {Color.END}").strip().lower()
    
    if confirm != 's':
        return
    
    try:
        # Parsear backup
        with open(seleccionado, 'r') as f:
            lineas = f.readlines()
        
        usuarios_backup = {}
        token_config = load_token_config()
        if not token_config.get('token_password'):
            token_config['token_password'] = 'default123'
            save_token_config(token_config)
        
        for line in lineas:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(':')
            if len(parts) < 4:
                continue
            
            username = parts[0]
            
            if 'TOKEN' in line and len(parts) >= 5:
                usuarios_backup[username] = {
                    'password': token_config['token_password'],
                    'days': max(0, int(parts[3]) - 1),
                    'display_name': parts[4],
                    'user_type': 'token',
                    'max_conn': 1
                }
            else:
                usuarios_backup[username] = {
                    'password': parts[1],
                    'days': max(0, int(parts[3]) - 1),
                    'display_name': None,
                    'user_type': 'ssh',
                    'max_conn': int(parts[2])
                }
        
        # Analizar diferencias
        users_actuales = load_users()
        usuarios_sistema = {u: data for u, data in users_actuales.items() if u != "admin"}
        
        en_backup = set(usuarios_backup.keys())
        en_sistema = set(usuarios_sistema.keys())
        
        a_crear = en_backup - en_sistema
        a_actualizar = en_backup & en_sistema
        a_eliminar = en_sistema - en_backup
        
        print(f"\n {Color.CYAN}📊 Análisis:{Color.END}")
        print(f" {Color.GREEN}Crear: {len(a_crear)}{Color.END}")
        print(f" {Color.YELLOW}Actualizar: {len(a_actualizar)}{Color.END}")
        print(f" {Color.RED}Eliminar: {len(a_eliminar)}{Color.END}")
        
        confirm = input(f"\n {Color.YELLOW}¿Ejecutar? (s/n): {Color.END}").strip().lower()
        if confirm != 's':
            return
        
        # Ejecutar fusión (mismo código que online)
        creados = 0
        actualizados = 0
        eliminados = 0
        
        # CREAR
        if a_crear:
            print(f"\n {Color.GREEN}Creando usuarios...{Color.END}\n")
            for i, username in enumerate(a_crear, 1):
                data = usuarios_backup[username]
                print(f"\r {Color.GREEN}Creando: {Color.WHITE}{username[:20]:<20}{Color.END} [{data['days']:2}d] ({i}/{len(a_crear)})", end="", flush=True)
                
                success, msg, expires = sincronizar_usuario(
                    username=username,
                    password=data['password'],
                    dias=data['days'],
                    operacion='crear',
                    user_type=data['user_type'],
                    max_conn=data['max_conn'],
                    display_name=data['display_name']
                )
                
                if success:
                    creados += 1
            print()
        
        # ACTUALIZAR
        if a_actualizar:
            print(f"\n {Color.YELLOW}Actualizando usuarios...{Color.END}\n")
            for i, username in enumerate(a_actualizar, 1):
                data = usuarios_backup[username]
                print(f"\r {Color.YELLOW}Actualizando: {Color.WHITE}{username[:20]:<20}{Color.END} [{data['days']:2}d] ({i}/{len(a_actualizar)})", end="", flush=True)
                
                success, msg, expires = sincronizar_usuario(
                    username=username,
                    dias=data['days'],
                    operacion='reiniciar'
                )
                
                if success:
                    actualizados += 1
            print()
        
        # ELIMINAR
        if a_eliminar:
            print(f"\n {Color.RED}Eliminando huérfanos...{Color.END}\n")
            for i, username in enumerate(a_eliminar, 1):
                print(f"\r {Color.RED}Eliminando: {Color.WHITE}{username[:20]:<20}{Color.END} ({i}/{len(a_eliminar)})", end="", flush=True)
                ejecutar_borrado_fisico(username)
                eliminados += 1
            print()
        
        print(f"\n {Color.GREEN}✓ Fusión completada:{Color.END}")
        print(f" {Color.GREEN}Creados: {creados}{Color.END}")
        print(f" {Color.YELLOW}Actualizados: {actualizados}{Color.END}")
        print(f" {Color.RED}Eliminados: {eliminados}{Color.END}")
        
        moratech.log_action("admin", f"Fusión Local: +{creados} ~{actualizados} -{eliminados} ({seleccionado.name})")
    
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
            ip_result = subprocess.run(['curl', '-s', '-4', 'ifconfig.me'], 
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
                ip_result
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
            ip_result = subprocess.run(['curl', '-s', '-4', 'ifconfig.me'], 
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
            ip_result = subprocess.run(['curl', '-s', '-4', 'ifconfig.me'], 
                                     capture_output=True, text=True, timeout=3)
            server_ip = ip_result.stdout.strip()
            print(f" {Color.CYAN}URL: {Color.GREEN}http://{server_ip}:{port}/api/{Color.END}")
        except:
            pass
        
        print_line()
        print(f" {Color.GREEN}[1]{Color.END} ➮ Ver logs")
        print(f" {Color.GREEN}[2]{Color.END} ➮ Detener servidor")
        print(f" {Color.GREEN}[3]{Color.END} ➮ Reiniciar servidor")
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
    elif choice == '3' and is_running:
        restart_api_server()
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
            ip_result = subprocess.run(['curl', '-s', '-4', 'ifconfig.me'], 
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

def restart_api_server():
    """Reiniciar servidor API sin preguntar puerto"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}REINICIAR SERVIDOR API{Color.END}")
    print_line()
    
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
    
    print(f"\n {Color.YELLOW}⏳ Deteniendo servidor...{Color.END}")
    
    try:
        # Detener servidor
        subprocess.run(['screen', '-S', 'api_server_individual', '-X', 'quit'], 
                     stderr=subprocess.DEVNULL)
        
        import time
        time.sleep(1)
        
        print(f" {Color.GREEN}✓ Servidor detenido{Color.END}")
        print(f"\n {Color.YELLOW}⏳ Iniciando servidor en puerto {port}...{Color.END}")
        
        # Reiniciar servidor
        import os
        api_script = os.path.join(os.path.dirname(__file__), 'api_server.py')
        
        subprocess.run([
            'screen', '-dmS', 'api_server_individual',
            'python3', api_script, port
        ])
        
        time.sleep(2)
        
        # Verificar que inició correctamente
        check = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        if 'api_server_individual' in check.stdout:
            print(f" {Color.GREEN}✓ Servidor reiniciado correctamente{Color.END}")
            
            try:
                ip_result = subprocess.run(['curl', '-s', '-4', 'ifconfig.me'], 
                                         capture_output=True, text=True, timeout=3)
                server_ip = ip_result.stdout.strip()
                print(f"\n {Color.CYAN}URL: {Color.GREEN}http://{server_ip}:{port}/api/{Color.END}")
            except:
                pass
            
            moratech.log_action("admin", f"API Server reiniciado en puerto {port}")
        else:
            print(f"\n {Color.RED}✗ Error al reiniciar el servidor{Color.END}")
    
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
    
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
            ip_result = subprocess.run(['curl', '-s', '-4', 'ifconfig.me'], 
                                     capture_output=True, text=True, timeout=3)
            server_ip = ip_result.stdout.strip()
            print(f" {Color.CYAN}Dashboard: {Color.GREEN}http://{server_ip}:{port}/dashboard-global{Color.END}")
            print(f" {Color.CYAN}Panel Control: {Color.GREEN}http://{server_ip}:{port}/panel-control{Color.END}")
        except:
            pass
        
        print_line()
        print(f" {Color.GREEN}[1]{Color.END} ➮ Ver logs")
        print(f" {Color.GREEN}[2]{Color.END} ➮ Detener servidor")
        print(f" {Color.GREEN}[3]{Color.END} ➮ Reiniciar servidor")
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
    elif choice == '3' and is_running:
        restart_api_general_server()
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
            ip_result = subprocess.run(['curl', '-s', '-4', 'ifconfig.me'], 
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

def restart_api_general_server():
    """Reiniciar servidor API General sin preguntar puerto"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}REINICIAR API GENERAL{Color.END}")
    print_line()
    
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
    
    print(f"\n {Color.YELLOW}⏳ Deteniendo servidor...{Color.END}")
    
    try:
        # Detener servidor
        subprocess.run(['screen', '-S', 'servidor_global', '-X', 'quit'], 
                     stderr=subprocess.DEVNULL)
        
        import time
        time.sleep(1)
        
        print(f" {Color.GREEN}✓ Servidor detenido{Color.END}")
        print(f"\n {Color.YELLOW}⏳ Iniciando servidor en puerto {port}...{Color.END}")
        
        # Reiniciar servidor
        import os
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        api_module = 'modules.api_general'
        
        cmd = ['python3', '-m', api_module, port]
        subprocess.run([
            'screen', '-dmS', 'servidor_global'
        ] + cmd, cwd=project_root)
        
        time.sleep(2)
        
        # Verificar que inició correctamente
        check = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        if 'servidor_global' in check.stdout:
            print(f" {Color.GREEN}✓ Servidor reiniciado correctamente{Color.END}")
            
            try:
                ip_result = subprocess.run(['curl', '-s', '-4', 'ifconfig.me'], 
                                         capture_output=True, text=True, timeout=3)
                server_ip = ip_result.stdout.strip()
                print(f"\n {Color.CYAN}Dashboard: {Color.GREEN}http://{server_ip}:{port}/dashboard-global{Color.END}")
                print(f" {Color.CYAN}Panel Control: {Color.GREEN}http://{server_ip}:{port}/panel-control{Color.END}")
            except:
                pass
            
            moratech.log_action("admin", f"API General reiniciado en puerto {port}")
        else:
            print(f"\n {Color.RED}✗ Error al reiniciar el servidor{Color.END}")
    
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
    
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
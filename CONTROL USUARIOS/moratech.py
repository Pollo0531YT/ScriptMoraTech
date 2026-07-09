#!/usr/bin/env python3
"""
MORATECH - Panel de Administración VPS
Sistema de gestión de usuarios SSH
"""
import os
import sys
import json
import hashlib
import subprocess
import socket
import traceback
from datetime import datetime, timedelta
from pathlib import Path

from modules import common, users as users_module

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
    common.clear_screen()

def print_line():
    common.print_line()

def print_banner():
    common.print_banner()

def is_root():
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False

def atomic_write(path: Path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=4)
    os.replace(tmp, path)
    try:
        os.chmod(path, mode)
    except Exception:
        pass

def get_system_info():
    """Obtiene información del sistema"""
    info = {}
    try:
        try:
            with open('/etc/os-release') as f:
                for line in f:
                    if line.startswith('PRETTY_NAME'):
                        info['os'] = line.split('=')[1].strip().strip('"')
                        break
        except:
            info['os'] = "N/A"

        info['arch'] = subprocess.check_output("uname -m", shell=True).decode().strip()

        info['cpus'] = subprocess.check_output("nproc", shell=True).decode().strip()

        try:
            info['ip'] = subprocess.check_output(["curl", "-s", "-4", "ifconfig.me"], timeout=3).decode().strip()
        except:
            info['ip'] = "No disponible"

        info['date'] = datetime.now().strftime("%d/%m/%Y-%H:%M")

        info['hostname'] = socket.gethostname()

        try:
            mem = subprocess.check_output("free -m", shell=True).decode().split('\n')[1].split()
            info['ram_total'] = f"{float(mem[1])/1024:.1f}G"
            info['ram_used'] = f"{mem[2]}M"
            info['ram_free'] = f"{float(mem[3])/1024:.1f}G"
            info['ram_percent'] = f"{(int(mem[2])/int(mem[1])*100):.2f}%"
        except:
            info['ram_total'] = info['ram_used'] = info['ram_free'] = info['ram_percent'] = "N/A"

        try:
            cpu = subprocess.check_output("top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1}'",
                                          shell=True).decode().strip()
            info['cpu_percent'] = f"{float(cpu):.1f}%"
        except:
            info['cpu_percent'] = "N/A"

    except Exception as e:
        print(f"{Color.RED}Error obteniendo info del sistema: {e}{Color.END}")
        traceback.print_exc()

    return info

def init_system():
    """Inicializa el sistema: crea carpetas/archivos base y configura expiración."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not USERS_FILE.exists():
        atomic_write(USERS_FILE, {})

    if not CONFIG_FILE.exists():
        config = {
            "system_name": "Moratech Panel",
            "version": "2.0",
            "installed": datetime.now().isoformat()
        }
        atomic_write(CONFIG_FILE, config)

    if not LOGS_FILE.exists():
        atomic_write(LOGS_FILE, [])

    if not TOKEN_CONFIG_FILE.exists():
        atomic_write(TOKEN_CONFIG_FILE, {"token_password": None})

    if not CONNECTIONS_FILE.exists():
        atomic_write(CONNECTIONS_FILE, {})

    if not PROTOCOLS_FILE.exists():
        atomic_write(PROTOCOLS_FILE, {
            "ssl": {"enabled": False, "port": 443},
            "v2ray": {"enabled": False, "port": 0},
            "slowdns": {"enabled": False, "port": 0},
            "proxy": {"enabled": False, "port": 80},
            "badvpn": {"enabled": False, "port": 7300}
        })

def log_action(user, action):
    """Registra acción en logs"""
    try:
        logs = []
        if LOGS_FILE.exists():
            with open(LOGS_FILE, 'r') as f:
                logs = json.load(f)
        logs.append({
            "user": user,
            "action": action,
            "timestamp": datetime.now().isoformat()
        })
        atomic_write(LOGS_FILE, logs)
    except Exception:
        pass

def show_dashboard():
    """Muestra el dashboard principal"""
    clear_screen()
    print_banner()

    info = get_system_info()

    print_line()
    print(f" {Color.CYAN}∘{Color.END} S.O: {Color.GREEN}{info.get('os', 'N/A')}{Color.END}  {Color.CYAN}∘{Color.END} Base:{Color.GREEN}{info.get('arch', 'N/A')}{Color.END} {Color.CYAN}∘{Color.END} CPU's:{Color.GREEN}{info.get('cpus', 'N/A')}{Color.END}")
    print(f" {Color.CYAN}∘{Color.END} IP: {Color.GREEN}{info.get('ip', 'N/A')}{Color.END}  {Color.CYAN}∘{Color.END} FECHA: {Color.GREEN}{info.get('date', 'N/A')}{Color.END}")
    print_line()
    print(f" Key: {Color.GREEN}Verified{Color.END}【 {Color.YELLOW}MoraTech©{Color.END} 】(V2.0) ► {Color.CYAN}[{info.get('hostname', 'N/A')}]{Color.END}")
    print_line()
    print(f" {Color.CYAN}∘{Color.END} TOTAL: {Color.GREEN}{info.get('ram_total', 'N/A')}{Color.END} {Color.CYAN}∘{Color.END} M|LIBRE: {Color.GREEN}{info.get('ram_free', 'N/A')}{Color.END}  {Color.CYAN}∘{Color.END} EN USO: {Color.GREEN}{info.get('ram_used', 'N/A')}{Color.END}")
    print(f" {Color.CYAN}∘{Color.END} U/RAM: {Color.GREEN}{info.get('ram_percent', 'N/A')}{Color.END}  {Color.CYAN}∘{Color.END} U/CPU: {Color.GREEN}{info.get('cpu_percent', 'N/A')}{Color.END}")
    print_line()

# ==================== MENÚ PRINCIPAL ====================

def main_menu(username):
    """Menú principal"""
    while True:
        show_dashboard()

        print(f" {Color.GREEN}[01]{Color.END} ➮ CONTROL USUARIOS (SSH/TOKEN)")
        print_line()
        print(f" {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}[ SALIR ]{Color.END}")
        print_line()

        choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()

        if choice in ('1','01'):
            users_module.control_usuarios_menu()
        elif choice == '0':
            log_action(username, "Logout")
            print(f"\n {Color.GREEN}¡Hasta pronto!{Color.END}\n")
            sys.exit(0)

def main():
    """Función principal"""
    try:
        init_system()
        main_menu("admin")
    except KeyboardInterrupt:
        print(f"\n\n {Color.GREEN}¡Hasta pronto!{Color.END}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()

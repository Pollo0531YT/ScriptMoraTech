import os
import subprocess
import time
import json
import re
from modules.common import Color, print_line, print_banner, clear_screen

SLOW_DIR = "/etc/slowdns"
SERVER_BIN = f"{SLOW_DIR}/sldns-server"
KEY_FILE = f"{SLOW_DIR}/server.key"
CONFIG_FILE = f"{SLOW_DIR}/mora_conf.json"

# Tu Llave Privada Maestra
MASTER_PRIV = "b17a4ce4c0e8cc54e33ee70b5e5a11c1a3ba853fd3743897ee091f9fcb53f0e2"

def save_config(ns, port):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'ns': ns, 'port': port}, f)

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    return {'ns': 'No configurado', 'port': '22'}

def install_slowdns():
    clear_screen()
    print_banner()
    os.makedirs(SLOW_DIR, exist_ok=True)
    
    print(f" {Color.YELLOW}Reiniciando servicios de red...{Color.END}")
    os.system("pkill -f sldns-server")
    os.system("fuser -k 53/udp > /dev/null 2>&1")

    # Escribir la llave para persistencia
    with open(KEY_FILE, "w") as f:
        f.write(MASTER_PRIV)
    
    if not os.path.exists(SERVER_BIN):
        url = "https://raw.githubusercontent.com/NevermoreSSH/hopp/main/slowdns/sldns-server"
        os.system(f"wget -q -O {SERVER_BIN} {url}")
        os.system(f"chmod +x {SERVER_BIN}")

    # --- REGLAS DE IPTABLES QUE TE FUNCIONARON ---
    print(f" {Color.CYAN}Aplicando reglas de tráfico...{Color.END}")
    os.system("iptables -F")
    os.system("iptables -t nat -F")
    os.system("iptables -t nat -A PREROUTING -p udp --dport 53 -j REDIRECT --to-ports 5300")
    os.system("iptables -A INPUT -p udp --dport 5300 -j ACCEPT")
    
    # --- REPARAR SSH (Para evitar el Connection Refused) ---
    # Eliminamos líneas duplicadas y aseguramos que escuche en todo
    os.system("sed -i '/ListenAddress/d' /etc/ssh/sshd_config")
    os.system("echo 'ListenAddress 0.0.0.0' >> /etc/ssh/sshd_config")
    os.system("service ssh restart > /dev/null 2>&1")

    ns_domain = input(f"\n {Color.GREEN}Ingresa tu NS Domain: {Color.END}").strip()
    l_port = input(f" {Color.GREEN}Puerto SSH Local [22]: {Color.END}").strip() or "22"
    
    save_config(ns_domain, l_port)
    
    # Ejecución con la llave fija
    cmd = f"screen -dmS slowdns {SERVER_BIN} -udp :5300 -privkey-file {KEY_FILE} {ns_domain} 127.0.0.1:{l_port}"
    os.system(cmd)

    print(f"\n {Color.GREEN}✓ Configuración aplicada correctamente.{Color.END}")
    print(f" {Color.YELLOW}Key detectada: 9dbb...605{Color.END}")
    time.sleep(2)

def view_info():
    clear_screen()
    print_banner()
    conf = get_config()
    print(f" {Color.CYAN}INFO DE CONEXIÓN{Color.END}")
    print_line()
    print(f" {Color.WHITE}NS: {Color.YELLOW}{conf['ns']}{Color.END}")
    print(f" {Color.WHITE}Key: {Color.GREEN}9dbbfb7374360504a22e71b8ffda2c9c3c8ee62283d171fef9d881bd6b51b605{Color.END}")
    print(f" {Color.WHITE}Puerto: {Color.YELLOW}{conf['port']}{Color.END}")
    print_line()
    input(f"\n {Color.CYAN}Presiona Enter para volver...{Color.END}")

def menu_slowdns():
    while True:
        clear_screen()
        print_banner()
        check = subprocess.run(['pgrep', '-f', 'sldns-server'], capture_output=True, text=True)
        status = f"{Color.GREEN}ACTIVO{Color.END}" if check.stdout.strip() else f"{Color.RED}INACTIVO{Color.END}"
        print(f" PANEL SLOWDNS | ESTADO: {status}")
        print_line()
        print(" [1] Instalar / Iniciar")
        print(" [2] Detener")
        print(" [3] Ver Info")
        print(" [4] Ver Logs")
        print(" [0] Volver")
        op = input("\n ► Opcion : ").strip()
        if op == '1': install_slowdns()
        elif op == '2': os.system("pkill -f sldns-server")
        elif op == '3': view_info()
        elif op == '4': os.system("screen -r slowdns")
        elif op == '0': break


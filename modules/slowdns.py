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

# Tu Llave Privada del VPS1 (Sincronizada)
MASTER_PRIV = "b17a4ce4c0e8cc54e33ee70b5e5a11c1a3ba853fd3743897ee091f9fcb53f0e2"

def save_config(ns, port):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'ns': ns, 'port': port}, f)

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    return {'ns': 'No configurado', 'port': '22'}

def get_current_pubkey():
    try:
        os.system("screen -S slowdns -X hardcopy /tmp/sldns.log")
        if os.path.exists("/tmp/sldns.log"):
            with open("/tmp/sldns.log", "r") as f:
                content = f.read()
                match = re.search(r"pubkey ([a-f0-9]{64})", content)
                if match: return match.group(1)
    except: pass
    return "Cargando..."

def install_slowdns():
    clear_screen()
    print_banner()
    os.makedirs(SLOW_DIR, exist_ok=True)
    
    print(f" {Color.YELLOW}Deteniendo procesos previos...{Color.END}")
    os.system("pkill -f sldns-server")
    os.system("fuser -k 53/udp > /dev/null 2>&1")

    # Escribir la llave del VPS1 en el archivo local
    with open(KEY_FILE, "w") as f:
        f.write(MASTER_PRIV)
    
    if not os.path.exists(SERVER_BIN):
        print(f" {Color.CYAN}Descargando binario optimizado...{Color.END}")
        url = "https://raw.githubusercontent.com/NevermoreSSH/hopp/main/slowdns/sldns-server"
        os.system(f"wget -q -O {SERVER_BIN} {url}")
        os.system(f"chmod +x {SERVER_BIN}")

    # --- CONFIGURACIÓN DE RED (IPtables) ---
    os.system("iptables -F && iptables -t nat -F")
    os.system("iptables -I INPUT -p udp --dport 5300 -j ACCEPT")
    os.system("iptables -t nat -I PREROUTING -p udp --dport 53 -j REDIRECT --to-ports 5300")
    
    # Reglas de Forwarding (Navegación)
    os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")
    os.system("iptables -t nat -A POSTROUTING -j MASQUERADE")
    os.system("iptables -A FORWARD -j ACCEPT")

    ns_domain = input(f"\n {Color.GREEN}Ingresa tu NS Domain: {Color.END}").strip()
    l_port = input(f" {Color.GREEN}Puerto Local de Destino (ej. 22): {Color.END}").strip() or "22"
    
    save_config(ns_domain, l_port)
    
    # Lanzar el servidor con Screen
    cmd = f"screen -dmS slowdns {SERVER_BIN} -udp :5300 -privkey-file {KEY_FILE} {ns_domain} 127.0.0.1:{l_port}"
    os.system(cmd)

    print(f"\n {Color.GREEN}✓ SlowDNS sincronizado con la llave del VPS1.{Color.END}")
    print(f" {Color.YELLOW}Puerto local configurado: {l_port}{Color.END}")
    time.sleep(2)

def view_info():
    clear_screen()
    print_banner()
    conf = get_config()
    pub = get_current_pubkey()
    print(f" {Color.CYAN}CONFIGURACIÓN DE ESPEJO ACTIVA{Color.END}")
    print_line()
    print(f" {Color.WHITE}NS Domain:    {Color.YELLOW}{conf['ns']}{Color.END}")
    print(f" {Color.WHITE}Public Key:   {Color.GREEN}{pub}{Color.END}")
    print(f" {Color.WHITE}Puerto Destino: {Color.YELLOW}{conf['port']}{Color.END}")
    print(f" {Color.WHITE}Puerto DNS:    {Color.YELLOW}53 / 5300{Color.END}")
    print_line()
    input(f"\n {Color.CYAN}Presiona Enter para volver...{Color.END}")

def restart_service():
    conf = get_config()
    if conf['ns'] == 'No configurado':
        print(f" {Color.RED}Error: Ejecuta la instalación primero.{Color.END}")
        time.sleep(2); return
    os.system("pkill -f sldns-server")
    cmd = f"screen -dmS slowdns {SERVER_BIN} -udp :5300 -privkey-file {KEY_FILE} {conf['ns']} 127.0.0.1:{conf['port']}"
    os.system(cmd)
    print(f" {Color.GREEN}Servicio Reiniciado en puerto {conf['port']}.{Color.END}")
    time.sleep(2)

def menu_slowdns():
    while True:
        clear_screen()
        print_banner()
        check = subprocess.run(['pgrep', '-f', 'sldns-server'], capture_output=True, text=True)
        status = f"{Color.GREEN}ACTIVO{Color.END}" if check.stdout.strip() else f"{Color.RED}INACTIVO{Color.END}"
        print(f" PANEL SLOWDNS MORATECH | ESTADO: {status}")
        print_line()
        print(" [1] Instalar / Iniciar (Modo Espejo)")
        print(" [2] Detener Servicio")
        print(" [3] Ver Info (Public Key)")
        print(" [4] Reiniciar Servicio")
        print(" [5] Ver Logs en Vivo")
        print(" [0] Volver")
        op = input("\n ► Opcion : ").strip()
        if op == '1': install_slowdns()
        elif op == '2': os.system("pkill -f sldns-server")
        elif op == '3': view_info()
        elif op == '4': restart_service()
        elif op == '5': os.system("screen -r slowdns")
        elif op == '0': break

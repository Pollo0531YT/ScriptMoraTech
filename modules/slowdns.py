import os
import subprocess
import time
import json
import re
from modules.common import Color, print_line, print_banner, clear_screen

SLOW_DIR = "/etc/slowdns"
SERVER_BIN = f"{SLOW_DIR}/sldns-server"
CONFIG_FILE = f"{SLOW_DIR}/mora_conf.json"

def save_config(ns, port):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'ns': ns, 'port': port}, f)

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'ns': 'No configurado', 'port': '22'}

def get_current_pubkey():
    """Extrae la llave pública actual directamente del proceso en ejecución"""
    try:
        # Volcamos el log actual de screen a un archivo temporal
        os.system("screen -S slowdns -X hardcopy /tmp/sldns.log")
        if os.path.exists("/tmp/sldns.log"):
            with open("/tmp/sldns.log", "r") as f:
                content = f.read()
                # Buscamos el patrón de la pubkey (64 caracteres hexadecimales)
                match = re.search(r"pubkey ([a-f0-9]{64})", content)
                if match:
                    return match.group(1)
    except:
        pass
    return "No detectada (¿Está el servicio activo?)"

def install_slowdns():
    clear_screen()
    print_banner()
    os.makedirs(SLOW_DIR, exist_ok=True)
    
    print(f" {Color.YELLOW}Limpiando servicios y procesos...{Color.END}")
    os.system("pkill -f sldns-server")
    os.system("iptables -F")
    os.system("iptables -t nat -F")
    
    if not os.path.exists(SERVER_BIN):
        url = "https://raw.githubusercontent.com/NevermoreSSH/hopp/main/slowdns/sldns-server"
        os.system(f"wget -q -O {SERVER_BIN} {url}")
        os.system(f"chmod +x {SERVER_BIN}")

    # Configuración de Red
    os.system("systemctl stop systemd-resolved > /dev/null 2>&1")
    os.system("systemctl disable systemd-resolved > /dev/null 2>&1")
    os.system("iptables -A INPUT -p udp --dport 5300 -j ACCEPT")
    os.system("iptables -t nat -A PREROUTING -p udp --dport 53 -j REDIRECT --to-ports 5300")
    
    ns_domain = input(f"\n {Color.GREEN}Ingresa tu NS Domain: {Color.END}").strip()
    l_port = input(f" {Color.GREEN}Puerto Local (SSH/SSL) [22]: {Color.END}").strip() or "22"
    
    save_config(ns_domain, l_port)
    
    # EJECUCIÓN SIN LLAVES (Dejamos que el binario genere la suya)
    cmd = f"screen -dmS slowdns {SERVER_BIN} -udp :5300 {ns_domain} 127.0.0.1:{l_port}"
    os.system(cmd)

    print(f"\n {Color.GREEN}✓ Instalado. El binario generará una Key propia.{Color.END}")
    print(f" {Color.YELLOW}Espera 5 segundos y revisa 'Ver Info'.{Color.END}")
    time.sleep(3)

def view_info():
    clear_screen()
    print_banner()
    conf = get_config()
    current_key = get_current_pubkey()
    
    print(f" {Color.CYAN}INFORMACIÓN DE CONEXIÓN ACTUAL{Color.END}")
    print_line()
    print(f" {Color.WHITE}NS Domain:   {Color.YELLOW}{conf['ns']}{Color.END}")
    print(f" {Color.WHITE}Public Key:  {Color.GREEN}{current_key}{Color.END}")
    print(f" {Color.WHITE}Puerto Local: {Color.YELLOW}{conf['port']}{Color.END}")
    print(f" {Color.WHITE}Puerto DNS:   {Color.YELLOW}53 / 5300{Color.END}")
    print_line()
    print(f" {Color.GRAY}Nota: Si la Key no aparece, espera unos segundos y vuelve a entrar.{Color.END}")
    input(f"\n {Color.CYAN}Presiona Enter para volver...{Color.END}")

def restart_service():
    conf = get_config()
    if conf['ns'] == 'No configurado':
        print(f" {Color.RED}Error: Primero debes instalar.{Color.END}")
        time.sleep(2); return
        
    os.system("pkill -f sldns-server")
    cmd = f"screen -dmS slowdns {SERVER_BIN} -udp :5300 {conf['ns']} 127.0.0.1:{conf['port']}"
    os.system(cmd)
    print(f" {Color.GREEN}Servicio Reiniciado (Nueva Key generada).{Color.END}")
    time.sleep(2)

def view_logs():
    clear_screen()
    print(f" {Color.YELLOW}ENTRANDO A LOGS...{Color.END}")
    print(f" {Color.WHITE}Para salir sin apagar: {Color.GREEN}Ctrl + A y luego D{Color.END}")
    print_line()
    time.sleep(1)
    os.system("screen -r slowdns")

def menu_slowdns():
    while True:
        clear_screen()
        print_banner()
        check = subprocess.run(['pgrep', '-f', 'sldns-server'], capture_output=True, text=True)
        status = f"{Color.GREEN}ACTIVO{Color.END}" if check.stdout.strip() else f"{Color.RED}INACTIVO{Color.END}"
        
        print(f" PANEL SLOWDNS MORATECH | ESTADO: {status}")
        print_line()
        print(" [1] Instalar / Reinstalar (Limpio)")
        print(" [2] Detener Servicio")
        print(" [3] Ver Info (Capturar Key)")
        print(" [4] Reiniciar (Cambiar Key)")
        print(" [5] Ver Logs en Vivo")
        print(" [0] Volver")
        print_line()
        
        op = input(" ► Opcion : ").strip()
        if op == '1': install_slowdns()
        elif op == '2': 
            os.system("pkill -f sldns-server")
            print(f" {Color.RED}Servicio Detenido.{Color.END}"); time.sleep(1)
        elif op == '3': view_info()
        elif op == '4': restart_service()
        elif op == '5': view_logs()
        elif op == '0': break

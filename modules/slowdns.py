import os
import subprocess
import time
import json
from modules.common import Color, print_line, print_banner, clear_screen

SLOW_DIR = "/etc/slowdns"
SERVER_BIN = f"{SLOW_DIR}/sldns-server"
CONFIG_FILE = f"{SLOW_DIR}/mora_conf.json"

# Llaves Moratech Fijas
FIXED_PUB = "9dbbfb7374360504a22e71b8ffda2c9c3c8ee62283d171fef9d881bd6b51b605"
FIXED_PRIV = "19f56338b625039f9976378e6328325a75bd82f7c00620835f8e5695627f7f89"

def save_config(ns):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'ns': ns}, f)

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'ns': 'No configurado'}

def install_slowdns():
    clear_screen()
    print_banner()
    os.makedirs(SLOW_DIR, exist_ok=True)
    
    print(f" {Color.YELLOW}Iniciando instalación limpia...{Color.END}")
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
    
    # Asegurar SSH Local
    os.system("echo 'ListenAddress 127.0.0.1' >> /etc/ssh/sshd_config")
    os.system("service ssh restart > /dev/null 2>&1")

    ns_domain = input(f"\n {Color.GREEN}Ingresa tu NS Domain: {Color.END}").strip()
    save_config(ns_domain)
    
    # EJECUCIÓN CON LLAVE FIJA (Solución del log)
    cmd = f"screen -dmS slowdns {SERVER_BIN} -udp :5300 -privkey {FIXED_PRIV} {ns_domain} 127.0.0.1:22"
    os.system(cmd)

    print(f"\n {Color.GREEN}✓ Instalado y Corriendo con Key 605.{Color.END}")
    time.sleep(2)

def view_info():
    clear_screen()
    print_banner()
    conf = get_config()
    print(f" {Color.CYAN}INFORMACIÓN DE CONEXIÓN SLOWDNS{Color.END}")
    print_line()
    print(f" {Color.WHITE}NS Domain: {Color.YELLOW}{conf['ns']}{Color.END}")
    print(f" {Color.WHITE}Public Key: {Color.YELLOW}{FIXED_PUB}{Color.END}")
    print(f" {Color.WHITE}Puerto Local: {Color.YELLOW}22{Color.END}")
    print(f" {Color.WHITE}Puerto DNS: {Color.YELLOW}53 / 5300{Color.END}")
    print_line()
    input(f"\n {Color.CYAN}Presiona Enter para volver...{Color.END}")

def restart_service():
    conf = get_config()
    if conf['ns'] == 'No configurado':
        print(f" {Color.RED}Error: Primero debes instalar.{Color.END}")
        time.sleep(2)
        return
    os.system("pkill -f sldns-server")
    cmd = f"screen -dmS slowdns {SERVER_BIN} -udp :5300 -privkey {FIXED_PRIV} {conf['ns']} 127.0.0.1:22"
    os.system(cmd)
    print(f" {Color.GREEN}Servicio Reiniciado.{Color.END}")
    time.sleep(2)

def view_logs():
    clear_screen()
    print(f" {Color.RED}IMPORTANTE: {Color.WHITE}Para salir del log sin apagar el servidor:")
    print(f" {Color.GREEN}Presiona {Color.YELLOW}Ctrl + A {Color.WHITE}y luego la tecla {Color.YELLOW}D{Color.END}")
    print_line()
    time.sleep(2)
    os.system("screen -r slowdns")

def menu_slowdns():
    while True:
        clear_screen()
        print_banner()
        check = subprocess.run(['pgrep', '-f', 'sldns-server'], capture_output=True, text=True)
        status = f"{Color.GREEN}ACTIVO{Color.END}" if check.stdout.strip() else f"{Color.RED}INACTIVO{Color.END}"
        
        print(f" PANEL SLOWDNS MORATECH | ESTADO: {status}")
        print_line()
        print(" [1] Instalar / Reinstalar")
        print(" [2] Detener Servicio")
        print(" [3] Ver Info de Conexión")
        print(" [4] Reiniciar Servicio")
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

if __name__ == "__main__":
    menu_slowdns()
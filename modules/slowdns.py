import os
import subprocess
import time
import json
from modules.common import Color, print_line, print_banner, clear_screen

SLOW_DIR = "/etc/slowdns"
SERVER_BIN = f"{SLOW_DIR}/sldns-server"
KEY_PRIV = f"{SLOW_DIR}/server.key"
# Tu Key Pública Moratech
FIXED_PUB = "9dbbfb7374360504a22e71b8ffda2c9c3c8ee62283d171fef9d881bd6b51b605"
FIXED_PRIV = "19f56338b625039f9976378e6328325a75bd82f7c00620835f8e5695627f7f89"

def check_status():
    check = subprocess.run(['pgrep', '-f', 'sldns-server'], capture_output=True, text=True)
    return f"{Color.GREEN}ACTIVO{Color.END}" if check.stdout.strip() else f"{Color.RED}INACTIVO{Color.END}"

def view_logs():
    """Ver el log en tiempo real para diagnosticar"""
    clear_screen()
    print(f" {Color.YELLOW}Mostrando tráfico SlowDNS (Presiona CTRL+C para salir){Color.END}")
    print(f" {Color.WHITE}Si intentas conectar y NO sale nada aquí, el problema es tu NS Domain.{Color.END}")
    print_line()
    # Intentamos re-adjuntar a la sesión screen
    os.system("screen -r slowdns")

def install_slowdns():
    clear_screen()
    print_banner()
    os.makedirs(SLOW_DIR, exist_ok=True)

    # 1. Limpieza de procesos y puertos previos
    os.system("pkill -f sldns-server")
    os.system("systemctl stop systemd-resolved > /dev/null 2>&1")
    os.system("systemctl disable systemd-resolved > /dev/null 2>&1")

    # 2. Descarga (Si no existe)
    if not os.path.exists(SERVER_BIN):
        print(f" {Color.YELLOW}Descargando binario de emergencia...{Color.END}")
        url = "https://raw.githubusercontent.com/fisabiliyusri/SLDNS/main/slowdns/sldns-server"
        os.system(f"wget -q -O {SERVER_BIN} {url}")
        os.system(f"chmod +x {SERVER_BIN}")

    # 3. Guardar llaves
    with open(KEY_PRIV, "w") as f: f.write(FIXED_PRIV)

    # 4. NS Domain
    ns_domain = input(f" {Color.GREEN}Tu NS Domain (ej: ns.midominio.com): {Color.END}").strip()
    if not ns_domain: return

    # 5. Configuración de Red (IPTABLES REFORZADO)
    print(f" {Color.YELLOW}Aplicando reglas de IPTABLES...{Color.END}")
    os.system("iptables -F -t nat") # Limpiar tablas nat para evitar choques
    os.system("iptables -I INPUT -p udp --dport 5300 -j ACCEPT")
    os.system("iptables -t nat -I PREROUTING -p udp --dport 53 -j REDIRECT --to-ports 5300")

    # 6. Ejecución con LOGS habilitados
    # Usamos un archivo de log temporal para poder leerlo
    cmd = f"screen -dmS slowdns {SERVER_BIN} -udp :5300 -privkey-file {KEY_PRIV} {ns_domain} 127.0.0.1:22"
    os.system(cmd)
    
    print(f"\n {Color.GREEN}✓ SlowDNS Reinstalado.{Color.END}")
    time.sleep(2)

def menu_slowdns():
    while True:
        clear_screen()
        print_banner()
        status = check_status()
        print(f" PANEL SLOWDNS | ESTADO: {status}")
        print_line()
        print(f" [1] Instalar / Reinstalar")
        print(f" [2] Detener Servicio")
        print(f" [3] VER TRÁFICO (Logs en vivo)")
        print(f" [0] Volver")
        print_line()
        
        op = input(" ► Opcion : ").strip()
        if op == '1': install_slowdns()
        elif op == '2': os.system("pkill -f sldns-server")
        elif op == '3': view_logs()
        elif op == '0': break

if __name__ == "__main__":
    menu_slowdns()
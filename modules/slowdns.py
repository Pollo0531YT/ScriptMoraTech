import os
import subprocess
import time
import json
from modules.common import Color, print_line, print_banner, clear_screen

# Configuración de Rutas
SLOW_DIR = "/etc/slowdns"
SERVER_BIN = f"{SLOW_DIR}/sldns-server"
KEY_PRIV = f"{SLOW_DIR}/server.key"
KEY_PUB = f"{SLOW_DIR}/server.pub"
CONFIG_DATA = f"{SLOW_DIR}/slowdns_config.json"

# Tus Llaves Fijas Moratech
FIXED_PUB = "9dbbfb7374360504a22e71b8ffda2c9c3c8ee62283d171fef9d881bd6b51b605"
FIXED_PRIV = "19f56338b625039f9976378e6328325a75bd82f7c00620835f8e5695627f7f89"

def check_status():
    """Verifica si el proceso está corriendo"""
    check = subprocess.run(['pgrep', '-f', 'sldns-server'], capture_output=True, text=True)
    return f"{Color.GREEN}ACTIVO{Color.END}" if check.stdout.strip() else f"{Color.RED}INACTIVO{Color.END}"

def view_logs():
    """Muestra el tráfico en tiempo real para verificar la llave"""
    clear_screen()
    print(f" {Color.YELLOW}=== DIAGNÓSTICO SLOWDNS (CTRL+C para salir) ==={Color.END}")
    print(f" {Color.WHITE}Verifica que la 'pubkey' sea la terminada en 605.{Color.END}")
    print_line()
    os.system("screen -r slowdns")

def install_slowdns():
    clear_screen()
    print_banner()
    print_line()
    
    # 1. Crear directorio y detener procesos
    os.makedirs(SLOW_DIR, exist_ok=True)
    os.system("pkill -f sldns-server")
    os.system("systemctl stop systemd-resolved > /dev/null 2>&1")

    # 2. Descarga limpia del binario (si no existe)
    if not os.path.exists(SERVER_BIN):
        print(f" {Color.YELLOW}Descargando binario estable...{Color.END}")
        url = "https://raw.githubusercontent.com/fisabiliyusri/SLDNS/main/slowdns/sldns-server"
        os.system(f"wget -q -O {SERVER_BIN} {url}")
        os.system(f"chmod +x {SERVER_BIN}")

    # 3. FORZAR LLAVES MORATECH (Borramos las viejas y creamos las nuevas)
    print(f" {Color.CYAN}Sincronizando Llaves Moratech (terminación 605)...{Color.END}")
    os.system(f"rm -f {KEY_PRIV} {KEY_PUB}") # Borrado físico
    with open(KEY_PRIV, "w") as f:
        f.write(FIXED_PRIV)
    with open(KEY_PUB, "w") as f:
        f.write(FIXED_PUB)

    # 4. Configuración de NS Domain
    if os.path.exists(CONFIG_DATA):
        with open(CONFIG_DATA, 'r') as f:
            old_conf = json.load(f)
            last_ns = old_conf.get('ns', '')
    else: last_ns = ""

    ns_domain = input(f" {Color.GREEN}NS Domain [{last_ns}]: {Color.END}").strip() or last_ns
    if not ns_domain:
        print(f" {Color.RED}Error: NS Domain requerido.{Color.END}")
        time.sleep(2); return

    # 5. Reglas de Red (Iptables)
    print(f" {Color.YELLOW}Configurando Iptables (53 -> 5300)...{Color.END}")
    os.system("iptables -I INPUT -p udp --dport 5300 -j ACCEPT")
    os.system("iptables -t nat -I PREROUTING -p udp --dport 53 -j REDIRECT --to-ports 5300")

    # 6. Ejecución en Screen usando el archivo de llave
    # Importante: Usamos -privkey-file para obligar al binario a leer TU llave
    cmd = f"screen -dmS slowdns {SERVER_BIN} -udp :5300 -privkey-file {KEY_PRIV} {ns_domain} 127.0.0.1:22"
    os.system(cmd)

    # Guardar Config
    with open(CONFIG_DATA, 'w') as f:
        json.dump({"ns": ns_domain}, f)

    print(f"\n {Color.GREEN}✓ Instalación Finalizada.{Color.END}")
    print(f" {Color.WHITE}Usa la opción [3] para confirmar la llave en el log.{Color.END}")
    time.sleep(3)

def menu_slowdns():
    while True:
        clear_screen()
        print_banner()
        status = check_status()
        print(f" PANEL SLOWDNS MORATECH | ESTADO: {status}")
        print_line()
        print(f" {Color.GREEN}[1]{Color.END} > Reinstalar y Forzar Key 605")
        print(f" {Color.GREEN}[2]{Color.END} > Detener Servicio")
        print(f" {Color.GREEN}[3]{Color.END} > VER LOGS (Diagnóstico)")
        print(f" {Color.GREEN}[0]{Color.END} > Volver")
        print_line()
        
        op = input(" ► Opcion : ").strip()
        if op == '1': install_slowdns()
        elif op == '2':
            os.system("pkill -f sldns-server")
            print(f" {Color.RED}Servicio detenido.{Color.END}"); time.sleep(2)
        elif op == '3': view_logs()
        elif op == '0': break

if __name__ == "__main__":
    menu_slowdns()
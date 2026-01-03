import os
import subprocess
import time
import json
from modules.common import Color, print_line, print_banner, clear_screen

# Rutas y Enlaces extraídos del script de HideSSH
SLOW_DIR = "/etc/slowdns"
SERVER_BIN = f"{SLOW_DIR}/sldns-server"
# Usamos tu clave fija Moratech (Noise Protocol)
FIXED_PUB = "9dbbfb7374360504a22e71b8ffda2c9c3c8ee62283d171fef9d881bd6b51b605"
FIXED_PRIV = "19f56338b625039f9976378e6328325a75bd82f7c00620835f8e5695627f7f89"

def check_status():
    check = subprocess.run(['pgrep', '-f', 'sldns-server'], capture_output=True, text=True)
    return f"{Color.GREEN}ACTIVO{Color.END}" if check.stdout.strip() else f"{Color.RED}INACTIVO{Color.END}"

def install_slowdns():
    clear_screen()
    print_banner()
    
    # 1. Crear directorio y descargar binarios (Links de HideSSH)
    print(f" {Color.YELLOW}Descargando binario sldns-server desde repositorio HideSSH...{Color.END}")
    os.makedirs(SLOW_DIR, exist_ok=True)
    
    # Estos son los links que funcionan del script que pasaste
    url_bin = "https://raw.githubusercontent.com/fisabiliyusri/SLDNS/main/slowdns/sldns-server"
    
    os.system(f"wget -q -O {SERVER_BIN} {url_bin}")
    os.system(f"chmod +x {SERVER_BIN}")

    if not os.path.exists(SERVER_BIN) or os.path.getsize(SERVER_BIN) < 1000000:
        print(f" {Color.RED}✗ Error: El binario no se descargó. Link caído o sin red.{Color.END}")
        time.sleep(2); return

    # 2. Configuración de Llaves (Creamos los archivos .key y .pub para que sldns-server los lea)
    with open(f"{SLOW_DIR}/server.key", "w") as f: f.write(FIXED_PRIV)
    with open(f"{SLOW_DIR}/server.pub", "w") as f: f.write(FIXED_PUB)

    # 3. Datos del usuario
    ns_domain = input(f" {Color.GREEN}Introduce tu NS Domain (ej: ns.tu-web.com): {Color.END}").strip()
    if not ns_domain: return

    # 4. Configuración de Puertos e IPTABLES (Como el script SL)
    print(f" {Color.YELLOW}Configurando IPTABLES y puertos adicionales...{Color.END}")
    
    # Abrir puertos en SSH para evitar conflictos
    os.system("echo 'Port 2222' >> /etc/ssh/sshd_config")
    os.system("service ssh restart > /dev/null 2>&1")

    # IPTABLES (Copiado exacto del script SL)
    os.system("iptables -I INPUT -p udp --dport 5300 -j ACCEPT")
    os.system("iptables -t nat -I PREROUTING -p udp --dport 53 -j REDIRECT --to-ports 5300")
    
    # Liberar puerto 53 de systemd
    os.system("systemctl stop systemd-resolved > /dev/null 2>&1")
    os.system("systemctl disable systemd-resolved > /dev/null 2>&1")

    # 5. Ejecución (Usando el modo -privkey-file que usa HideSSH)
    os.system("pkill -f sldns-server")
    # Redirigimos al puerto 2222 que acabamos de abrir
    cmd = f"screen -dmS slowdns {SERVER_BIN} -udp :5300 -privkey-file {SLOW_DIR}/server.key {ns_domain} 127.0.0.1:22"
    os.system(cmd)

    print(f"\n {Color.GREEN}✓ SlowDNS instalado y funcionando (HideSSH Binaries).{Color.END}")
    print(f" {Color.CYAN}Llave Pública: {Color.WHITE}{FIXED_PUB}{Color.END}")
    time.sleep(3)

def menu_slowdns():
    while True:
        clear_screen()
        print_banner()
        status = check_status()
        print(f" {Color.WHITE}PANEL SLOWDNS | ESTADO: {status}{Color.END}")
        print_line()
        print(" [1] Instalar / Reinstalar")
        print(" [2] Detener Servicio")
        print(" [0] Volver")
        print_line()
        
        op = input(" ► Opcion : ").strip()
        if op == '1': install_slowdns()
        elif op == '2':
            os.system("pkill -f sldns-server")
            print(f" {Color.RED}Servicio detenido.{Color.END}"); time.sleep(2)
        elif op == '0': break

if __name__ == "__main__":
    menu_slowdns()
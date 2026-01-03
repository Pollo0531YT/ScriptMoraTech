import os
import subprocess
import json
import time
from modules.common import Color, print_line, print_banner, clear_screen

# Rutas de archivos
SLOW_DIR = "/etc/moratech/slowdns"
DNS_SERVER = f"{SLOW_DIR}/dnstt-server"
CONFIG_DATA = f"{SLOW_DIR}/slowdns_config.json"

# Llaves maestras Moratech (Verificadas con el algoritmo de main.go)
FIXED_PUB = "9dbbfb7374360504a22e71b8ffda2c9c3c8ee62283d171fef9d881bd6b51b605"
FIXED_PRIV = "19f56338b625039f9976378e6328325a75bd82f7c00620835f8e5695627f7f89"

def check_status():
    """Verifica si el binario dnstt-server está en la tabla de procesos"""
    try:
        check = subprocess.run(['pgrep', '-f', 'dnstt-server'], capture_output=True, text=True)
        return f"{Color.GREEN}ACTIVO{Color.END}" if check.stdout.strip() else f"{Color.RED}INACTIVO{Color.END}"
    except:
        return f"{Color.RED}INACTIVO{Color.END}"

def install_slowdns():
    clear_screen()
    print_banner()
    print_line()
    os.makedirs(SLOW_DIR, exist_ok=True)

    # 1. Descarga del binario compilado desde el main.go oficial
    print(f" {Color.YELLOW}Descargando binario dnstt-server (AMD64)...{Color.END}")
    url = "https://www.bamsoftware.com/software/dnstt/dnstt-server-linux-amd64"
    subprocess.run(['wget', '-q', '--show-progress', '-O', DNS_SERVER, url])
    subprocess.run(['chmod', '+x', DNS_SERVER])

    # Verificar que el archivo no sea de 0 bytes
    if not os.path.exists(DNS_SERVER) or os.path.getsize(DNS_SERVER) < 1000000:
        print(f" {Color.RED}✗ Error en descarga. Verifique su conexión.{Color.END}")
        time.sleep(2); return

    # 2. Configuración de Dominio
    if os.path.exists(CONFIG_DATA):
        with open(CONFIG_DATA, 'r') as f:
            conf = json.load(f)
            last_ns = conf.get('ns', '')
    else: last_ns = ""

    print(f" {Color.WHITE}Configure su subdominio NS (Ya debe estar apuntado al VPS){Color.END}")
    ns_domain = input(f" {Color.GREEN}NS Domain [{last_ns}]: {Color.END}").strip() or last_ns
    
    if not ns_domain:
        print(f" {Color.RED}✗ Se requiere un dominio NS.{Color.END}"); time.sleep(2); return

    # 3. Preparación del Sistema (Puerto 53)
    print(f" {Color.YELLOW}Liberando puerto 53 y configurando Iptables...{Color.END}")
    os.system("systemctl stop systemd-resolved > /dev/null 2>&1")
    os.system("systemctl disable systemd-resolved > /dev/null 2>&1")
    
    # Reglas NAT (Redirige tráfico DNS real al puerto del tunel)
    subprocess.run(['iptables', '-I', 'INPUT', '-p', 'udp', '--dport', '5300', '-j', 'ACCEPT'])
    subprocess.run(['iptables', '-t', 'nat', '-I', 'PREROUTING', '-p', 'udp', '--dport', '53', '-j', 'REDIRECT', '--to-ports', '5300'])

    # 4. Ejecución (Basado en Usage de main.go)
    subprocess.run(['pkill', '-f', 'dnstt-server'], stderr=subprocess.DEVNULL)
    
    # Comando: -udp (escucha) -privkey (llave hex) DOMAIN (filtro) TARGET (ssh)
    cmd = f"screen -dmS slowdns {DNS_SERVER} -udp :5300 -privkey {FIXED_PRIV} {ns_domain} 127.0.0.1:22"
    os.system(cmd)

    # Guardar configuración exitosa
    with open(CONFIG_DATA, 'w') as f:
        json.dump({"ns": ns_domain}, f)

    print(f"\n {Color.GREEN}✓ SlowDNS instalado y ACTIVO.{Color.END}")
    print(f" {Color.CYAN}Key Pública para la APP: {Color.WHITE}{FIXED_PUB}{Color.END}")
    time.sleep(4)

def menu_slowdns():
    while True:
        clear_screen()
        print_banner()
        status = check_status()
        print(f" {Color.WHITE}MÓDULO SLOWDNS | Estado: {status}{Color.END}")
        print_line()
        print(f" {Color.GREEN}[1]{Color.END} > Instalar / Reinstalar con Key Fija")
        print(f" {Color.GREEN}[2]{Color.END} > Detener Servicio")
        print(f" {Color.GREEN}[0]{Color.END} > Volver al Menú Principal")
        print_line()
        
        op = input(f" {Color.YELLOW}► Opcion : {Color.END}").strip()
        if op == '1': install_slowdns()
        elif op == '2':
            subprocess.run(['pkill', '-f', 'dnstt-server'])
            print(f" {Color.RED}Servicio detenido.{Color.END}"); time.sleep(2)
        elif op == '0': break

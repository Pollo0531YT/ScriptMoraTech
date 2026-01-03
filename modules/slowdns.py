import os
import subprocess
import json
import time
from modules.common import Color, print_line, print_banner, clear_screen

# --- RUTAS Y LLAVES (Según tu manual) ---
SLOW_DIR = "/etc/moratech/slowdns"
DNS_SERVER = f"{SLOW_DIR}/dnstt-server"
CONFIG_DATA = f"{SLOW_DIR}/slowdns_config.json"

# Key Fija Moratech (Noise Protocol_NK_25519)
FIXED_PUB = "9dbbfb7374360504a22e71b8ffda2c9c3c8ee62283d171fef9d881bd6b51b605"
FIXED_PRIV = "19f56338b625039f9976378e6328325a75bd82f7c00620835f8e5695627f7f89"

def check_status():
    """Verifica si dnstt-server está corriendo"""
    check = subprocess.run(['pgrep', '-f', 'dnstt-server'], capture_output=True, text=True)
    return f"{Color.GREEN}ACTIVO{Color.END}" if check.stdout.strip() else f"{Color.RED}INACTIVO{Color.END}"

def install_slowdns():
    clear_screen()
    print_banner()
    print_line()
    os.makedirs(SLOW_DIR, exist_ok=True)

    # 1. Descarga del binario compilado (AMD64 para VPS)
    print(f" {Color.YELLOW}Descargando binario oficial (David Fifield)...{Color.END}")
    url = "https://www.bamsoftware.com/software/dnstt/dnstt-server-linux-amd64"
    subprocess.run(['wget', '-q', '--show-progress', '-O', DNS_SERVER, url])
    subprocess.run(['chmod', '+x', DNS_SERVER])

    if not os.path.exists(DNS_SERVER) or os.path.getsize(DNS_SERVER) < 1000000:
        print(f" {Color.RED}✗ Error: El archivo no se descargó bien. Verifique su red.{Color.END}")
        time.sleep(2); return

    # 2. Configuración de Dominio NS
    print(f" {Color.WHITE}Configure su registro NS (ej: ns.midominio.com){Color.END}")
    ns_domain = input(f" {Color.GREEN}NS Domain: {Color.END}").strip()
    if not ns_domain: return

    # 3. Liberar Puerto 53 (Vital según manual)
    print(f" {Color.YELLOW}Liberando puerto 53 (systemd-resolved)...{Color.END}")
    os.system("systemctl stop systemd-resolved > /dev/null 2>&1")
    os.system("systemctl disable systemd-resolved > /dev/null 2>&1")
    
    # 4. Reglas de IPTABLES (Copiadas del manual que pasaste)
    print(f" {Color.YELLOW}Aplicando reglas de IPTABLES...{Color.END}")
    os.system("iptables -I INPUT -p udp --dport 5300 -j ACCEPT")
    os.system("iptables -t nat -I PREROUTING -p udp --dport 53 -j REDIRECT --to-ports 5300")
    # Para IPv6 (opcional)
    os.system("ip6tables -I INPUT -p udp --dport 5300 -j ACCEPT > /dev/null 2>&1")

    # 5. Ejecución (Estructura final: -udp -privkey DOMAIN TARGET)
    subprocess.run(['pkill', '-f', 'dnstt-server'], stderr=subprocess.DEVNULL)
    
    # Usamos -privkey para pasar el HEX directamente como dice el manual
    cmd = f"screen -dmS slowdns {DNS_SERVER} -udp :5300 -privkey {FIXED_PRIV} {ns_domain} 127.0.0.1:22"
    os.system(cmd)

    # Guardar config
    with open(CONFIG_DATA, 'w') as f:
        json.dump({"ns": ns_domain}, f)

    print(f"\n {Color.GREEN}✓ SlowDNS instalado y funcionando.{Color.END}")
    print(f" {Color.CYAN}Public Key: {Color.WHITE}{FIXED_PUB}{Color.END}")
    time.sleep(3)

def stop_slowdns():
    os.system("pkill -f dnstt-server")
    print(f" {Color.RED}✓ Servicio detenido.{Color.END}")
    time.sleep(2)

def menu_slowdns():
    while True:
        clear_screen()
        print_banner()
        status = check_status()
        print(f" SlowDNS + SSH | ESTADO -> {status}")
        print_line()
        print(f" {Color.GREEN}[1]{Color.END} > Instalar / Reinstalar")
        print(f" {Color.GREEN}[2]{Color.END} > Detener SlowDns")
        print(f" {Color.GREEN}[0]{Color.END} > Volver")
        print_line()
        
        op = input(f" {Color.YELLOW}► Opcion : {Color.END}").strip()
        if op == '1': install_slowdns()
        elif op == '2': stop_slowdns()
        elif op == '0': break

if __name__ == "__main__":
    menu_slowdns()
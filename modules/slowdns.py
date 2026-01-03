import os
import subprocess
import time
from modules.common import Color, print_line, print_banner, clear_screen

SLOW_DIR = "/etc/slowdns"
SERVER_BIN = f"{SLOW_DIR}/sldns-server"
# Llaves Moratech
FIXED_PUB = "9dbbfb7374360504a22e71b8ffda2c9c3c8ee62283d171fef9d881bd6b51b605"
FIXED_PRIV = "19f56338b625039f9976378e6328325a75bd82f7c00620835f8e5695627f7f89"

def install_slowdns():
    clear_screen()
    print_banner()
    os.makedirs(SLOW_DIR, exist_ok=True)
    
    # 1. Limpiar procesos
    os.system("pkill -f sldns-server")
    
    # 2. Descargar Binario Nevermore
    print(f" {Color.YELLOW}Descargando binario NevermoreSSH...{Color.END}")
    url = "https://raw.githubusercontent.com/NevermoreSSH/hopp/main/slowdns/sldns-server"
    os.system(f"wget -q -O {SERVER_BIN} {url}")
    os.system(f"chmod +x {SERVER_BIN}")

    # 3. Forzar Llaves Moratech (605)
    with open(f"{SLOW_DIR}/server.key", "w") as f: f.write(FIXED_PRIV)
    with open(f"{SLOW_DIR}/server.pub", "w") as f: f.write(FIXED_PUB)

    # 4. Configurar SSH para aceptar el túnel (Puertos Nevermore)
    print(f" {Color.YELLOW}Configurando puertos SSH (2269)...{Color.END}")
    os.system("echo 'Port 2269' >> /etc/ssh/sshd_config")
    os.system("sed -i 's/#AllowTcpForwarding yes/AllowTcpForwarding yes/g' /etc/ssh/sshd_config")
    os.system("service ssh restart > /dev/null 2>&1")

    # 5. IPTABLES Nevermore Style
    print(f" {Color.YELLOW}Aplicando IPTABLES 53 -> 5300...{Color.END}")
    os.system("systemctl stop systemd-resolved > /dev/null 2>&1")
    os.system("systemctl disable systemd-resolved > /dev/null 2>&1")
    os.system("iptables -F")
    os.system("iptables -t nat -F")
    os.system("iptables -I INPUT -p udp --dport 5300 -j ACCEPT")
    os.system("iptables -t nat -I PREROUTING -p udp --dport 53 -j REDIRECT --to-ports 5300")

    # 6. Ejecución Final
    ns_domain = input(f"\n {Color.GREEN}Ingresa tu NS Domain: {Color.END}").strip()
    
    # Comando usando el puerto 2269 que Nevermore requiere
    cmd = f"screen -dmS slowdns {SERVER_BIN} -udp :5300 -privkey-file {SLOW_DIR}/server.key {ns_domain} 127.0.0.1:2269"
    os.system(cmd)

    print(f"\n {Color.GREEN}✓ SlowDNS Listo en puerto 2269.{Color.END}")
    print(f" {Color.WHITE}Usa la Pubkey: {FIXED_PUB}{Color.END}")
    time.sleep(2)

def menu_slowdns():
    while True:
        clear_screen()
        print_banner()
        check = subprocess.run(['pgrep', '-f', 'sldns-server'], capture_output=True, text=True)
        status = f"{Color.GREEN}ACTIVO{Color.END}" if check.stdout.strip() else f"{Color.RED}INACTIVO{Color.END}"
        print(f" PANEL SLOWDNS | ESTADO: {status}")
        print_line()
        print(" [1] Instalar / Reparar (Nevermore Mode)")
        print(" [2] Detener Servicio")
        print(" [3] Ver Log (CTRL+A + D para salir)")
        print(" [0] Volver")
        op = input("\n ► Opcion : ").strip()
        if op == '1': install_slowdns()
        elif op == '2': os.system("pkill -f sldns-server")
        elif op == '3': os.system("screen -r slowdns")
        elif op == '0': break

if __name__ == "__main__":
    menu_slowdns()
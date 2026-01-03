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
    
    # 1. Limpiar todo rastro anterior
    os.system("pkill -f sldns-server")
    os.system("iptables -F")
    os.system("iptables -t nat -F")
    
    # 2. Descargar el binario Nevermore (que ya vimos que te conecta)
    if not os.path.exists(SERVER_BIN):
        url = "https://raw.githubusercontent.com/NevermoreSSH/hopp/main/slowdns/sldns-server"
        os.system(f"wget -q -O {SERVER_BIN} {url}")
        os.system(f"chmod +x {SERVER_BIN}")

    # 3. Configuración de IPtables EXACTA a tu VPS1
    print(f" {Color.YELLOW}Aplicando reglas de IPtables del VPS1...{Color.END}")
    os.system("systemctl stop systemd-resolved > /dev/null 2>&1")
    os.system("systemctl disable systemd-resolved > /dev/null 2>&1")
    
    # Regla Chain INPUT
    os.system("iptables -A INPUT -p udp --dport 5300 -j ACCEPT")
    # Regla Chain PREROUTING
    os.system("iptables -t nat -A PREROUTING -p udp --dport 53 -j REDIRECT --to-ports 5300")

    # 4. Asegurar que el SSH escuche en el 127.0.0.1
    # Sin esto, el tunel llega al VPS pero el SSH le dice "lárgate"
    os.system("echo 'ListenAddress 127.0.0.1' >> /etc/ssh/sshd_config")
    os.system("echo 'ListenAddress 0.0.0.0' >> /etc/ssh/sshd_config")
    os.system("service ssh restart > /dev/null 2>&1")

    # 5. NS Domain
    ns_domain = input(f"\n {Color.GREEN}Ingresa tu NS Domain: {Color.END}").strip()
    
    # 6. Ejecución
    # Usamos el puerto 22 que es el estándar en tu VPS1
    cmd = f"screen -dmS slowdns {SERVER_BIN} -udp :5300 {ns_domain} 127.0.0.1:22"
    os.system(cmd)

    print(f"\n {Color.GREEN}✓ Configuración del VPS1 aplicada con éxito.{Color.END}")
    print(f" {Color.YELLOW}Recuerda usar la Key 0ae7...7a69 en tu celular.{Color.END}")
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
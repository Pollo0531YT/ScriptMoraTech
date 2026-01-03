import os
import subprocess
import time
from modules.common import Color, print_line, print_banner, clear_screen

SLOW_DIR = "/etc/slowdns"
SERVER_BIN = f"{SLOW_DIR}/sldns-server"

def view_logs():
    clear_screen()
    print(f" {Color.YELLOW}=== LOGS EN VIVO (Presiona CTRL+A y luego D para salir sin matar el proceso) ==={Color.END}")
    print(f" {Color.CYAN}Si usas CTRL+C matas el servidor. Usa CTRL+A + D para minimizar.{Color.END}")
    print_line()
    os.system("screen -r slowdns")

def install_slowdns():
    clear_screen()
    print_banner()
    os.makedirs(SLOW_DIR, exist_ok=True)
    
    # 1. Matar procesos viejos
    os.system("pkill -f sldns-server")
    os.system("systemctl stop systemd-resolved > /dev/null 2>&1")

    # 2. Descargar binario si no existe
    if not os.path.exists(SERVER_BIN):
        url = "https://raw.githubusercontent.com/fisabiliyusri/SLDNS/main/slowdns/sldns-server"
        os.system(f"wget -q -O {SERVER_BIN} {url}")
        os.system(f"chmod +x {SERVER_BIN}")

    # 3. ARREGLAR SSH (El problema del Connection Refused)
    # Nos aseguramos que SSH acepte conexiones de localhost
    os.system("sed -i 's/#ListenAddress 0.0.0.0/ListenAddress 0.0.0.0/g' /etc/ssh/sshd_config")
    os.system("service ssh restart > /dev/null 2>&1")

    # 4. NS Domain
    ns_domain = input(f" {Color.GREEN}Introduce NS Domain: {Color.END}").strip()
    
    # 5. Redirección de Puertos
    os.system("iptables -I INPUT -p udp --dport 5300 -j ACCEPT")
    os.system("iptables -t nat -I PREROUTING -p udp --dport 53 -j REDIRECT --to-ports 5300")

    # 6. EJECUCIÓN (Sin forzar llaves externas, dejaremos que use la suya interna para evitar errores)
    # Redirigimos al puerto 22. Si falla, probaremos con el 110 o 143.
    cmd = f"screen -dmS slowdns {SERVER_BIN} -udp :5300 {ns_domain} 127.0.0.1:22"
    os.system(cmd)

    print(f"\n {Color.GREEN}✓ Servidor Iniciado.{Color.END}")
    print(f" {Color.YELLOW}IMPORTANTE: Usa la Key que termina en '7a69' en tu celular.{Color.END}")
    time.sleep(2)

def menu_slowdns():
    while True:
        clear_screen()
        print_banner()
        check = subprocess.run(['pgrep', '-f', 'sldns-server'], capture_output=True, text=True)
        status = f"{Color.GREEN}ACTIVO{Color.END}" if check.stdout.strip() else f"{Color.RED}INACTIVO{Color.END}"
        print(f" PANEL SLOWDNS | ESTADO: {status}")
        print_line()
        print(" [1] Instalar y Arreglar SSH")
        print(" [2] Detener Servicio")
        print(" [3] VER LOGS (No uses CTRL+C para salir)")
        print(" [0] Volver")
        op = input("\n ► Opcion : ").strip()
        if op == '1': install_slowdns()
        elif op == '2': os.system("pkill -f sldns-server")
        elif op == '3': view_logs()
        elif op == '0': break

if __name__ == "__main__":
    menu_slowdns()
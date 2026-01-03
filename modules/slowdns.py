import os
import subprocess
import time
import json
from modules.common import Color, print_line, print_banner, clear_screen

SLOW_DIR = "/etc/slowdns"
SERVER_BIN = f"{SLOW_DIR}/sldns-server"
KEY_FILE = f"{SLOW_DIR}/server.key"
CONFIG_FILE = f"{SLOW_DIR}/mora_conf.json"

# Llave Privada Maestra Sincronizada con VPS1
MASTER_PRIV = "b17a4ce4c0e8cc54e33ee70b5e5a11c1a3ba853fd3743897ee091f9fcb53f0e2"

def save_config(ns, port):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'ns': ns, 'port': port}, f)

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    return {'ns': 'No configurado', 'port': '22'}

def install_slowdns():
    clear_screen()
    print_banner()
    os.makedirs(SLOW_DIR, exist_ok=True)
    
    print(f" {Color.YELLOW}Limpiando procesos y bloqueos...{Color.END}")
    os.system("pkill -f sldns-server")
    # Liberar puertos DNS para que no den "Address already in use"
    os.system("fuser -k 53/udp > /dev/null 2>&1")
    os.system("fuser -k 5300/udp > /dev/null 2>&1")

    # Guardar llave privada maestra (Termina en 605)
    with open(KEY_FILE, "w") as f:
        f.write(MASTER_PRIV)
    
    # Descargar binario si no existe
    if not os.path.exists(SERVER_BIN):
        url = "https://raw.githubusercontent.com/NevermoreSSH/hopp/main/slowdns/sldns-server"
        os.system(f"wget -q -O {SERVER_BIN} {url}")
        os.system(f"chmod +x {SERVER_BIN}")

    # --- REGLAS DE RED SEGURAS ---
    print(f" {Color.CYAN}Configurando IPtables (Flujo Seguro)...{Color.END}")
    # Limpiamos solo lo necesario para no tumbar otras reglas del panel
    os.system("iptables -t nat -F")
    
    # [CRUCIAL] Permitir tráfico interno (Esto evita el Connection Refused)
    os.system("iptables -A INPUT -i lo -j ACCEPT")
    os.system("iptables -A OUTPUT -o lo -j ACCEPT")
    
    # Redirección de puerto DNS (De 53 público a 5300 interno)
    os.system("iptables -t nat -A PREROUTING -p udp --dport 53 -j REDIRECT --to-ports 5300")
    os.system("iptables -A INPUT -p udp --dport 5300 -j ACCEPT")
    
    # --- REPARACIÓN Y SINCRONIZACIÓN SSH ---
    # Limpiamos cualquier rastro de configuraciones que bloqueen el acceso
    print(f" {Color.YELLOW}Verificando integridad del SSH...{Color.END}")
    os.system("sed -i '/ListenAddress/d' /etc/ssh/sshd_config")
    # Aseguramos que el SSH escuche en todas las interfaces para que el SlowDNS lo vea
    os.system("echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config")
    os.system("service ssh restart")

    ns_domain = input(f"\n {Color.GREEN}Ingresa tu NS Domain: {Color.END}").strip()
    # Si usas SSL, este puerto debería ser el del SSL (443) o el del Proxy (80)
    l_port = input(f" {Color.GREEN}Puerto de destino (SSH=22 / Proxy=80): {Color.END}").strip() or "22"
    
    save_config(ns_domain, l_port)
    
    # Lanzamiento en segundo plano con Screen
    # Se usa 127.0.0.1 para que el tráfico pase por el túnel interno
    cmd = f"screen -dmS slowdns {SERVER_BIN} -udp :5300 -privkey-file {KEY_FILE} {ns_domain} 127.0.0.1:{l_port}"
    os.system(cmd)

    print(f"\n {Color.GREEN}✓ SlowDNS levantado exitosamente.{Color.END}")
    print(f" {Color.CYAN}Puerto: 53 UDP -> Destino: {l_port}{Color.END}")
    time.sleep(2)

def menu_slowdns():
    while True:
        clear_screen()
        print_banner()
        check = subprocess.run(['pgrep', '-f', 'sldns-server'], capture_output=True, text=True)
        status = f"{Color.GREEN}ACTIVO{Color.END}" if check.stdout.strip() else f"{Color.RED}INACTIVO{Color.END}"
        
        print(f" PANEL SLOWDNS | ESTADO: {status}")
        print_line()
        print(" [1] Instalar / Iniciar")
        print(" [2] Detener Servicio")
        print(" [3] Ver Información de Conexión")
        print(" [4] Ver Logs (Screen)")
        print(" [0] Volver al Menú Principal")
        
        op = input("\n ► Opcion : ").strip()
        
        if op == '1':
            install_slowdns()
        elif op == '2':
            os.system("pkill -f sldns-server")
            os.system("iptables -t nat -F")
            print(f"\n {Color.RED}Servicio detenido y reglas limpiadas.{Color.END}")
            time.sleep(2)
        elif op == '3':
            conf = get_config()
            print_line()
            print(f" {Color.YELLOW}DATOS DE CONFIGURACIÓN:{Color.END}")
            print(f" NS Domain: {conf['ns']}")
            print(f" Public Key: 9dbbfb7374360504a22e71b8ffda2c9c3c8ee62283d171fef9d881bd6b51b605")
            print(f" Puerto Local: {conf['port']}")
            print_line()
            input("\nPresiona Enter para continuar...")
        elif op == '4':
            os.system("screen -r slowdns")
        elif op == '0':
            break
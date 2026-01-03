import os
import subprocess
import json
import time
from common import Color, print_line, print_banner, clear_screen, PROTOCOLS_FILE

# --- CONFIGURACIÓN DE RUTAS ---
SLOW_DIR = "/etc/moratech/slowdns"
DNS_SERVER = f"{SLOW_DIR}/dnstt-server"
CONFIG_DATA = f"{SLOW_DIR}/slowdns_config.json"
PRIV_KEY_FILE = f"{SLOW_DIR}/server.priv"
PUB_KEY_FILE = f"{SLOW_DIR}/server.pub"

# --- LLAVES MAESTRAS (Pareja de la que me pasaste) ---
FIXED_PUB = "9dbbfb7374360504a22e71b8ffda2c9c3c8ee62283d171fef9d881bd6b51b605"
FIXED_PRIV = "19f56338b625039f9976378e6328325a75bd82f7c00620835f8e5695627f7f89"

# --- FUNCIONES DE APOYO ---

def get_local_ports():
    """Detecta puertos en escucha para ofrecer como destino"""
    ports = []
    try:
        cmd = "ss -tulpn | grep -E 'sshd|dropbear|python|stunnel'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if line:
                parts = line.split()
                port = parts[4].split(':')[-1]
                if port not in ports: ports.append(port)
    except: pass
    if "22" not in ports: ports.append("22")
    return sorted(list(set(ports)))

def load_slow_config():
    if os.path.exists(CONFIG_DATA):
        with open(CONFIG_DATA, 'r') as f: return json.load(f)
    return {"ns": "", "port": "22", "key_type": "fija"}

def save_slow_config(ns, port, key_type):
    with open(CONFIG_DATA, 'w') as f:
        json.dump({"ns": ns, "port": port, "key_type": key_type}, f)

def check_status():
    check = subprocess.run(['pgrep', 'dnstt-server'], capture_output=True, text=True)
    return f"{Color.GREEN}ACTIVO{Color.END}" if check.stdout.strip() else f"{Color.RED}INACTIVO{Color.END}"

# --- FUNCIONES PRINCIPALES ---

def install_slowdns():
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INSTALADOR INTELIGENTE SLOWDNS{Color.END}")
    print_line()

    os.makedirs(SLOW_DIR, exist_ok=True)
    conf = load_slow_config()

    # 1. Dominio NS
    last_ns = conf.get('ns', '')
    ns_domain = input(f" {Color.GREEN}Dominio NS{f' ({last_ns})' if last_ns else ''}: {Color.END}").strip() or last_ns
    if not ns_domain:
        print(f" {Color.RED}✗ Error: NS requerido.{Color.END}"); time.sleep(2); return

    # 2. Puerto Local
    print(f"\n {Color.YELLOW}Puertos activos detectados:{Color.END}")
    available = get_local_ports()
    for i, p in enumerate(available, 1):
        print(f" [{i}] Puerto {p}")
    
    p_sel = input(f" {Color.YELLOW}Selecciona destino [1]: {Color.END}").strip() or "1"
    try: local_port = available[int(p_sel)-1]
    except: local_port = "22"

    # 3. Key
    print_line()
    print(f" [1] Usar KEY FIJA (9dbbfb73...)")
    print(f" [2] Generar KEY ALEATORIA")
    k_choice = input(f"\n {Color.YELLOW}Opción [1]: {Color.END}").strip() or "1"

    if k_choice == "1":
        with open(PRIV_KEY_FILE, 'w') as f: f.write(FIXED_PRIV)
        with open(PUB_KEY_FILE, 'w') as f: f.write(FIXED_PUB)
        key_type = "fija"
    else:
        print(f" {Color.YELLOW}Generando llaves...{Color.END}")
        subprocess.run([DNS_SERVER, "-gen-key", "-privkey-file", PRIV_KEY_FILE, "-pubkey-file", PUB_KEY_FILE], capture_output=True)
        key_type = "random"

    # 4. Binarios e Iptables
    if not os.path.exists(DNS_SERVER):
        print(f" {Color.YELLOW}Descargando binario...{Color.END}")
        url = "https://github.com/m0ratech/binarios/raw/main/dnstt-server" # Ajustar URL
        subprocess.run(['wget', '-O', DNS_SERVER, url], stderr=subprocess.DEVNULL)
        subprocess.run(['chmod', '+x', DNS_SERVER])

    subprocess.run(['iptables', '-I', 'INPUT', '-p', 'udp', '--dport', '5300', '-j', 'ACCEPT'])
    subprocess.run(['iptables', '-t', 'nat', '-I', 'PREROUTING', '-p', 'udp', '--dport', '53', '-j', 'REDIRECT', '--to-ports', '5300'])

    # 5. Ejecución
    stop_slowdns(silent=True)
    cmd = f"screen -dmS slowdns {DNS_SERVER} -udp :5300 -privkey-file {PRIV_KEY_FILE} {ns_domain} 127.0.0.1:{local_port}"
    os.system(cmd)

    save_slow_config(ns_domain, local_port, key_type)
    print(f"\n {Color.GREEN}✓ Instalado y corriendo en Screen 'slowdns'{Color.END}")
    input(f"\n {Color.CYAN}Presiona Enter para continuar...{Color.END}")

def stop_slowdns(silent=False):
    subprocess.run(['pkill', '-f', 'dnstt-server'], stderr=subprocess.DEVNULL)
    if not silent:
        print(f" {Color.RED}✓ SlowDNS Detenido.{Color.END}")
        time.sleep(2)

def restart_slowdns():
    conf = load_slow_config()
    if not conf.get('ns'):
        print(f" {Color.RED}✗ No hay configuración previa.{Color.END}")
        time.sleep(2); return
    
    stop_slowdns(silent=True)
    cmd = f"screen -dmS slowdns {DNS_SERVER} -udp :5300 -privkey-file {PRIV_KEY_FILE} {conf['ns']} 127.0.0.1:{conf['port']}"
    os.system(cmd)
    print(f" {Color.GREEN}✓ SlowDNS Reiniciado.{Color.END}")
    time.sleep(2)

def remove_slowdns():
    stop_slowdns(silent=True)
    if os.path.exists(SLOW_DIR):
        import shutil
        shutil.rmtree(SLOW_DIR)
    # Limpiar iptables básico
    subprocess.run(['iptables', '-t', 'nat', '-F'], stderr=subprocess.DEVNULL)
    print(f" {Color.YELLOW}✓ SlowDNS eliminado del sistema.{Color.END}")
    time.sleep(2)

def show_info():
    clear_screen()
    print_banner()
    conf = load_slow_config()
    print_line()
    print(f" {Color.CYAN}INFORMACIÓN DE CONEXIÓN{Color.END}")
    print_line()
    if os.path.exists(PUB_KEY_FILE):
        with open(PUB_KEY_FILE, 'r') as f: pub = f.read().strip()
        print(f" {Color.WHITE}NS Domain: {Color.YELLOW}{conf.get('ns')}{Color.END}")
        print(f" {Color.WHITE}Puerto Local: {Color.YELLOW}{conf.get('port')}{Color.END}")
        print(f" {Color.WHITE}Public Key: {Color.GREEN}{pub}{Color.END}")
    else:
        print(f" {Color.RED}No hay servicios instalados.{Color.END}")
    print_line()
    input(f" {Color.CYAN}Presiona Enter para volver...{Color.END}")

# --- MENÚ PRINCIPAL ---

def menu_slowdns():
    while True:
        clear_screen()
        print_banner()
        status = check_status()
        print(f" SlowDNS + SSHD/Proxy | ESTADO -> {status}")
        print_line()
        print(f" {Color.GREEN}[1]{Color.END} > Instalar SlowDns")
        print(f" {Color.GREEN}[2]{Color.END} > Ver Información")
        print(f" {Color.GREEN}[3]{Color.END} > Reiniciar SlowDns")
        print(f" {Color.GREEN}[4]{Color.END} > Detener SlowDns")
        print(f" {Color.GREEN}[5]{Color.END} > Remover SlowDns")
        print_line()
        print(f" {Color.GREEN}[0]{Color.END} =>>  Volver")
        print_line()
        
        opc = input(f" {Color.YELLOW}► Opcion : {Color.END}").strip()

        if opc == '1': install_slowdns()
        elif opc == '2': show_info()
        elif opc == '3': restart_slowdns()
        elif opc == '4': stop_slowdns()
        elif opc == '5': remove_slowdns()
        elif opc == '0': break

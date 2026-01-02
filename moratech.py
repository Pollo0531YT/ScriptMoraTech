#!/usr/bin/env python3
"""
MORATECH - Panel de Administración VPS
Sistema de gestión de usuarios SSH y protocolos
"""

import os
import sys
import json
import hashlib
import subprocess
import socket
from datetime import datetime, timedelta
from pathlib import Path

from modules import common, extras, users, ssl, phyton, badvpn, v2ray

# Colores para terminal
class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

# Configuración
CONFIG_DIR = Path.home() / '.moratech'
CONFIG_FILE = CONFIG_DIR / 'config.json'
USERS_FILE = CONFIG_DIR / 'users.json'
LOGS_FILE = CONFIG_DIR / 'logs.json'
TOKEN_CONFIG_FILE = CONFIG_DIR / 'token_config.json'
CONNECTIONS_FILE = CONFIG_DIR / 'connections.json'
PROTOCOLS_FILE = CONFIG_DIR / 'protocols.json'

def clear_screen():
    common.clear_screen()

def print_line():
    common.print_line()

def print_banner():
    common.print_banner()

def get_system_info():
    """Obtiene información del sistema"""
    info = {}
    try:
        # Sistema Operativo
        with open('/etc/os-release') as f:
            for line in f:
                if line.startswith('PRETTY_NAME'):
                    info['os'] = line.split('=')[1].strip().strip('"')
                    break
        
        # Arquitectura
        info['arch'] = subprocess.check_output("uname -m", shell=True).decode().strip()
        
        # CPUs
        info['cpus'] = subprocess.check_output("nproc", shell=True).decode().strip()
        
        # IP Pública
        try:
            info['ip'] = subprocess.check_output("curl -s ifconfig.me", shell=True, timeout=3).decode().strip()
        except:
            info['ip'] = "No disponible"
        
        # Fecha actual
        info['date'] = datetime.now().strftime("%d/%m/%Y-%H:%M")
        
        # Hostname
        info['hostname'] = socket.gethostname()
        
        # RAM
        mem = subprocess.check_output("free -m", shell=True).decode().split('\n')[1].split()
        info['ram_total'] = f"{float(mem[1])/1024:.1f}G"
        info['ram_used'] = f"{mem[2]}M"
        info['ram_free'] = f"{float(mem[3])/1024:.1f}G"
        info['ram_percent'] = f"{(int(mem[2])/int(mem[1])*100):.2f}%"
        
        # CPU usage
        try:
            cpu = subprocess.check_output("top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1}'", shell=True).decode().strip()
            info['cpu_percent'] = f"{float(cpu):.1f}%"
        except:
            info['cpu_percent'] = "N/A"
        
    except Exception as e:
        print(f"{Color.RED}Error obteniendo info del sistema: {e}{Color.END}")
    
    return info

def get_active_ports():
    """Obtiene puertos activos - DETECCIÓN AUTOMÁTICA - Solo muestra activos"""
    ports = {}
    port_counter = {}  # Contador para nombres duplicados
    
    try:
        result = subprocess.run(['ss', '-tulpn'], capture_output=True, text=True)
        output = result.stdout
        import re
        
        # Función auxiliar para agregar puertos
        def add_port(name, port_num):
            if name not in port_counter:
                port_counter[name] = 0
            port_counter[name] += 1
            key = f"{name}_{port_counter[name]}"
            ports[key] = (name, port_num)
        
        # Detectar SSH
        if ':22 ' in output or ':22\n' in output:
            add_port('SSH', '22')
        
        # Detectar SSL/Stunnel
        stunnel_check = subprocess.run(['pgrep', '-f', 'stunnel'], capture_output=True, text=True)
        if stunnel_check.stdout.strip():
            ssl_ports = []
            for line in output.split('\n'):
                if 'stunnel' in line:
                    match = re.search(r':(\d+)\s', line)
                    if match:
                        ssl_ports.append(match.group(1))
            for port in sorted(set(ssl_ports)):
                add_port('SSL', port)
        
        # Detectar Proxy Python
        proxy_check = subprocess.run(['pgrep', '-f', 'proxy.py'], capture_output=True, text=True)
        if proxy_check.stdout.strip():
            proxy_ports = []
            for line in output.split('\n'):
                if 'python' in line.lower() and 'proxy' in line:
                    match = re.search(r':(\d+)\s', line)
                    if match and match.group(1) != '22':
                        proxy_ports.append(match.group(1))
            for port in sorted(set(proxy_ports)):
                add_port('Proxy', port)
        
        # Detectar BadVPN
        badvpn_check = subprocess.run(['pgrep', '-f', 'badvpn-udpgw'], capture_output=True, text=True)
        if badvpn_check.stdout.strip():
            badvpn_ports = []
            for line in output.split('\n'):
                if 'badvpn' in line:
                    match = re.search(r'127\.0\.0\.1:(\d+)', line)
                    if match:
                        badvpn_ports.append(match.group(1))
            for port in sorted(set(badvpn_ports)):
                add_port('BadVPN', port)
        
        # Detectar V2Ray/3X-UI
        v2ray_check = subprocess.run(['systemctl', 'is-active', 'x-ui'], capture_output=True, text=True)
        if 'active' in v2ray_check.stdout:
            v2ray_ports = []
            for line in output.split('\n'):
                if 'xray' in line.lower() or 'x-ui' in line.lower():
                    match = re.search(r':(\d+)\s', line)
                    if match:
                        v2ray_ports.append(match.group(1))
            
            xray_ps = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            for ps_line in xray_ps.stdout.split('\n'):
                if 'xray' in ps_line.lower():
                    port_matches = re.findall(r':(\d{4,5})', ps_line)
                    for port in port_matches:
                        if port not in ['127.0', '0.0.0']:
                            v2ray_ports.append(port)
            
            for port in sorted(set(v2ray_ports)):
                add_port('V2Ray', port)
        
        # Detectar SlowDNS
        if ':5300 ' in output or ':5300\n' in output:
            add_port('SlowDNS', '5300')
            
    except Exception:
        pass
    
    return ports

def init_system():
    """Inicializa el sistema"""
    CONFIG_DIR.mkdir(exist_ok=True)
    
    if not USERS_FILE.exists():
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)
    
    if not CONFIG_FILE.exists():
        config = {
            "system_name": "Moratech Panel",
            "version": "2.0",
            "installed": datetime.now().isoformat()
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    
    if not LOGS_FILE.exists():
        with open(LOGS_FILE, 'w') as f:
            json.dump([], f)
    
    if not TOKEN_CONFIG_FILE.exists():
        with open(TOKEN_CONFIG_FILE, 'w') as f:
            json.dump({"token_password": None}, f)
    
    if not CONNECTIONS_FILE.exists():
        with open(CONNECTIONS_FILE, 'w') as f:
            json.dump({}, f)
    
    if not PROTOCOLS_FILE.exists():
        with open(PROTOCOLS_FILE, 'w') as f:
            json.dump({
                "ssl": {"enabled": False, "port": 443},
                "v2ray": {"enabled": False, "port": 0},
                "slowdns": {"enabled": False, "port": 0},
                "proxy": {"enabled": False, "port": 80},
                "badvpn": {"enabled": False, "port": 7300}
            }, f, indent=4)


def log_action(user, action):
    """Registra acción en logs"""
    with open(LOGS_FILE, 'r') as f:
        logs = json.load(f)
    
    logs.append({
        "user": user,
        "action": action,
        "timestamp": datetime.now().isoformat()
    })
    
    with open(LOGS_FILE, 'w') as f:
        json.dump(logs, f, indent=4)

def show_dashboard():
    """Muestra el dashboard principal"""
    clear_screen()
    print_banner()
    
    # Información del sistema
    info = get_system_info()
    ports = get_active_ports()
    
    print_line()
    print(f" {Color.CYAN}∘{Color.END} S.O: {Color.GREEN}{info.get('os', 'N/A')}{Color.END}  {Color.CYAN}∘{Color.END} Base:{Color.GREEN}{info.get('arch', 'N/A')}{Color.END} {Color.CYAN}∘{Color.END} CPU's:{Color.GREEN}{info.get('cpus', 'N/A')}{Color.END}")
    print(f" {Color.CYAN}∘{Color.END} IP: {Color.GREEN}{info.get('ip', 'N/A')}{Color.END}  {Color.CYAN}∘{Color.END} FECHA: {Color.GREEN}{info.get('date', 'N/A')}{Color.END}")
    print_line()
    print(f" Key: {Color.GREEN}Verified{Color.END}【 {Color.YELLOW}MoraTech©{Color.END} 】(V2.0) ► {Color.CYAN}[{info.get('hostname', 'N/A')}]{Color.END}")
    print_line()
    
    # Puertos en formato de 2 columnas - SOLO ACTIVOS
    if ports:
        port_items = [(name, port) for key, (name, port) in ports.items()]
        
        for i in range(0, len(port_items), 2):
            left_name, left_port = port_items[i]
            
            if i+1 < len(port_items):
                right_name, right_port = port_items[i+1]
                left_text = f" {Color.CYAN}∘{Color.END} {left_name}: {Color.GREEN}{left_port}{Color.END}"
                right_text = f"{Color.CYAN}∘{Color.END} {right_name}: {Color.GREEN}{right_port}{Color.END}"
                print(f"{left_text:<45} {right_text}")
            else:
                left_text = f" {Color.CYAN}∘{Color.END} {left_name}: {Color.GREEN}{left_port}{Color.END}"
                print(f"{left_text}")
    else:
        print(f" {Color.YELLOW}No hay protocolos activos{Color.END}")
    
    print_line()
    print(f" {Color.CYAN}∘{Color.END} TOTAL: {Color.GREEN}{info.get('ram_total', 'N/A')}{Color.END} {Color.CYAN}∘{Color.END} M|LIBRE: {Color.GREEN}{info.get('ram_free', 'N/A')}{Color.END}  {Color.CYAN}∘{Color.END} EN USO: {Color.GREEN}{info.get('ram_used', 'N/A')}{Color.END}")
    print(f" {Color.CYAN}∘{Color.END} U/RAM: {Color.GREEN}{info.get('ram_percent', 'N/A')}{Color.END}  {Color.CYAN}∘{Color.END} U/CPU: {Color.GREEN}{info.get('cpu_percent', 'N/A')}{Color.END}")
    print_line()

# ==================== MENÚ DE PROTOCOLOS ====================

def protocols_menu():
    """Menú de protocolos"""
    while True:
        clear_screen()
        print_line()
        print(f" {Color.CYAN}>> INSTALACION DE PROTOCOLOS <<{Color.END}")
        print_line()
  
        print(f"{Color.GREEN}1.{Color.END} ➮ SSL/TLS")
        print(f"{Color.GREEN}2.{Color.END} ➮ PROXY PYTHON")
        print(f"{Color.GREEN}3.{Color.END} ➮ V2RAY SWITCH")
        print(f"{Color.GREEN}4.{Color.END} ➮ SlowDNS (desarrollo...)")

        print_line()
        print(f" {Color.CYAN}HERRAMIENTAS Y SERVICIOS{Color.END}")
        print_line()

        print(f"{Color.GREEN}5.{Color.END} ➮ BadVPN")
        print(f"{Color.GREEN}6.{Color.END} ➮ EXTRAS")
        

        print_line()
        print(f"{Color.GREEN}0.{Color.END} Volver")
        
        choice = input(f"\n{Color.YELLOW}Selecciona: {Color.END}").strip()
        if choice == '1':
            ssl.menu_ssl()
        elif choice == '2':
            phyton.menu_phyton() 
        elif choice == '3':
            v2ray.menu_v2ray()
        elif choice == '5':
            badvpn.menu_badvpn() 
        elif choice == '6':
            extras.menu_extras()
        elif choice == '0':
            break
        else:
            print(f"\n{Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

# ==================== FUNCIONES DE PROTOCOLOS ====================


# ==================== EXTRAS ====================

def check_and_free_port(port):
    
    """Verifica y libera un puerto"""
    try:
        # Ver qué proceso usa el puerto
        result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
        pids = result.stdout.strip().split('\n')
        
        if pids and pids[0]:
            print(f" {Color.YELLOW}Puerto {port} en uso. Liberando...{Color.END}")
            for pid in pids:
                if pid:
                    subprocess.run(['kill', '-9', pid], stderr=subprocess.DEVNULL)
            import time
            time.sleep(1)
    except:
        pass

def configure_forwarding():
    """Configura IP forwarding y NAT para Ubuntu (iptables + ufw aware)"""
    import shutil, traceback, time
    try:
        if os.geteuid() != 0:
            raise RuntimeError("Necesitas ejecutar como root.")

        # Habilitar ip_forward inmediatamente
        subprocess.run(['sysctl','-w','net.ipv4.ip_forward=1'], check=False)

        # Hacer permanente (usar /etc/sysctl.d/99-moratech.conf para no tocar sysctl.conf directo)
        conf_path = '/etc/sysctl.d/99-moratech.conf'
        with open(conf_path, 'w') as f:
            f.write('# Habilitado por Moratech\nnet.ipv4.ip_forward=1\n')
        subprocess.run(['sysctl','--system'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Detectar interfaz de salida por default
        route = subprocess.run(['ip','route','show','default'], capture_output=True, text=True)
        ext_if = 'eth0'
        if route.returncode == 0 and route.stdout:
            parts = route.stdout.split()
            if 'dev' in parts:
                idx = parts.index('dev')
                if idx + 1 < len(parts):
                    ext_if = parts[idx+1]

        # Determinar interfaz TUN (tun0 o similar) para reglas FORWARD; no obligatoria si proxy solo usa NAT universal
        tun_if = 'tun0'
        links = subprocess.run(['ip','-o','link','show'], capture_output=True, text=True)
        for line in links.stdout.splitlines():
            name = line.split(':')[1].split('@')[0].strip()
            if name.startswith('tun') or name.startswith('tap') or name.startswith('wg') or name.startswith('vmnet'):
                tun_if = name
                break

        # Reglas iptables:
        # Aceptar conexiones RELATED/ESTABLISHED entrantes desde internet al tun y viceversa
        subprocess.run(['iptables','-A','FORWARD','-i',ext_if,'-o',tun_if,'-m','state','--state','RELATED,ESTABLISHED','-j','ACCEPT'])
        subprocess.run(['iptables','-A','FORWARD','-i',tun_if,'-o',ext_if,'-j','ACCEPT'])
        # MASQUERADE en salida por interfaz externa
        subprocess.run(['iptables','-t','nat','-A','POSTROUTING','-o',ext_if,'-j','MASQUERADE'])

        # Si ufw está activo, ajustar DEFAULT_FORWARD_POLICY y before.rules
        if shutil.which('ufw'):
            ufw_status = subprocess.run(['ufw','status','verbose'], capture_output=True, text=True)
            if 'Status: active' in ufw_status.stdout:
                # Cambiar politica forward a ACCEPT en /etc/default/ufw
                dpath = '/etc/default/ufw'
                if os.path.exists(dpath):
                    with open(dpath,'r') as f:
                        d = f.read()
                    d = d.replace('DEFAULT_FORWARD_POLICY="DROP"','DEFAULT_FORWARD_POLICY="ACCEPT"')
                    with open(dpath,'w') as f:
                        f.write(d)
                # Añadir bloque NAT si no existe en before.rules
                before = '/etc/ufw/before.rules'
                if os.path.exists(before):
                    with open(before,'r') as f:
                        b = f.read()
                    if '*nat' not in b:
                        nat_block = f"\n# NAT table rules (added by Moratech)\n*nat\n:POSTROUTING ACCEPT [0:0]\n-A POSTROUTING -o {ext_if} -j MASQUERADE\nCOMMIT\n"
                        with open(before,'a') as f:
                            f.write(nat_block)
                        # reload ufw
                        subprocess.run(['ufw','disable'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        time.sleep(0.5)
                        subprocess.run(['ufw','enable'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Persistir reglas (iptables-persistent / netfilter-persistent)
        if shutil.which('netfilter-persistent'):
            subprocess.run(['netfilter-persistent','save'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # fallback: iptables-save to /etc/iptables/rules.v4 si existe paquete
            if os.path.exists('/etc/iptables'):
                subprocess.run(['iptables-save'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return True
    except Exception as e:
        print("Error en configure_forwarding:", e)
        traceback.print_exc()
        return False

# ==================== MENÚ PRINCIPAL ====================

def main_menu(username):
    """Menú principal"""
    while True:
        show_dashboard()

        print(f" {Color.GREEN}[01]{Color.END} ➮ CONTROL USUARIOS (SSH/TOKEN)")
        print(f" {Color.GREEN}[02]{Color.END} ➮ INSTALADOR DE PROTOCOLOS")
        print(f" {Color.GREEN}[03]{Color.END} ➮ OPTIMIZAR VPS")
        print(f" {Color.GREEN}[04]{Color.END} ➮ ESTADÍSTICAS Y LOGS")
        print_line()
        print(f" {Color.GREEN}[05]{Color.END} ➮ UPDATE / REMOVE  |  {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}[ SALIR ]{Color.END}")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
        
        if choice == '1' or choice == '01':
            users.control_usuarios_menu()
        elif choice == '2' or choice == '02':
            protocols_menu()
        elif choice == '3' or choice == '03':
            print(f"\n {Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        elif choice == '4' or choice == '04':
            print(f"\n {Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        elif choice == '5' or choice == '05':
            print(f"\n {Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        elif choice == '0':
            log_action(username, "Logout")
            print(f"\n {Color.GREEN}¡Hasta pronto!{Color.END}\n")
            sys.exit(0)

def main():
    """Función principal"""
    init_system()
    main_menu("admin")


if __name__ == "__main__":
    main()
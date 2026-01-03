#!/usr/bin/env python3
"""
Módulo SPHYTONSL - Gestión de PROXY
"""
import subprocess
import json
import os
from pathlib import Path

from modules.common import Color, PROTOCOLS_FILE, clear_screen, print_banner, print_line
import moratech

def menu_phyton():
    """Menu de phyton"""
    while True:
        #show_dashboard()

        # Mostrar estado actual - DETECCIÓN AUTOMÁTICA
        try:
            result = subprocess.run(['ss', '-tulpn'], capture_output=True, text=True)
            output = result.stdout
            
            # Detectar Proxy Python
            proxy_ports = []
            proxy_check = subprocess.run(['pgrep', '-f', 'proxy.py'], capture_output=True, text=True)
            if proxy_check.stdout.strip():
                for line in output.split('\n'):
                    if 'python' in line.lower():
                        import re
                        match = re.search(r':(\d+)\s', line)
                        if match and match.group(1) not in ['22']:
                            proxy_ports.append(match.group(1))
            
            if proxy_ports:
                ports_str = ", ".join(set(proxy_ports))
                proxy_status = f"{Color.GREEN}ACTIVO - Puerto(s) {ports_str}{Color.END}"
            else:
                proxy_status = f"{Color.YELLOW}INACTIVO{Color.END}"
            
            print(f" {Color.CYAN}∘{Color.END} CONFIGURACION PHYTON: {proxy_status}")
            print_line()
        except:
            pass
  
        print(f"{Color.GREEN}1.{Color.END} Agregar puerto")
        print(f"{Color.GREEN}2.{Color.END} Detener puerto")
        print(f"{Color.GREEN}0.{Color.END} Volver")
        
        choice = input(f"\n{Color.YELLOW}Selecciona: {Color.END}").strip()
        if choice == '1':
            install_proxy()
        elif choice == '2':
            stop_proxy()    
        elif choice == '0':
            break
        else:
            print(f"\n{Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def install_proxy():
    """Instalar Proxy Python con respuesta HTTP corregida"""
    import subprocess
    import json
    import time
    
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}REPARANDO PROXY PYTHON{Color.END}")
    print_line()

    # 1. Datos
    port = input(f"\n {Color.GREEN}Puerto para Proxy (default 80): {Color.END}").strip() or "80"
    local_port = input(f" {Color.GREEN}Puerto Local de Destino (SSH) [22]: {Color.END}").strip() or "22"
    
    print(f"\n {Color.YELLOW}--- CONFIGURACIÓN ---{Color.END}")
    status_code = input(f" {Color.GREEN}Status (101 o 200) [101]: {Color.END}").strip() or "101"
    mini_banner = input(f" {Color.GREEN}Mini-Banner (opcional): {Color.END}").strip()

    # Formatear el Banner para el script de Python
    # NOTA: Usamos r'' para que no haya líos con los escapes
    banner_payload = f"<br><font color='green'>{mini_banner}</font><br>" if mini_banner else ""
    
    if status_code == "101":
        response_data = f"HTTP/1.1 101 Switching Protocols!\\r\\n\\r\\n{banner_payload}"
    else:
        response_data = f"HTTP/1.1 {status_code} Connection Established\\r\\n\\r\\n{banner_payload}"

    # 2. Limpieza extrema del puerto
    print(f" {Color.YELLOW}Limpiando puerto {port}...{Color.END}")
    os.system(f"fuser -k {port}/tcp > /dev/null 2>&1")
    os.system("pkill -f proxy.py")
    time.sleep(1)

    # 3. Construcción del Script (El corazón del proxy)
    proxy_script = r"""#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import socket, threading, select, sys, time

LISTENING_ADDR = '0.0.0.0'
LISTENING_PORT = """ + port + r"""
DEFAULT_HOST = "127.0.0.1:""" + local_port + r""""
RESPONSE = '""" + response_data + r"""'
BUFLEN = 4096 * 4

class Server(threading.Thread):
    def __init__(self, host, port):
        threading.Thread.__init__(self)
        self.running = False
        self.host = host
        self.port = port
        self.threads = []

    def run(self):
        self.soc = socket.socket(socket.AF_INET)
        self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.soc.bind((self.host, self.port))
        self.soc.listen(0)
        self.running = True
        try:
            while self.running:
                c, addr = self.soc.accept()
                conn = ConnectionHandler(c, self, addr)
                conn.start()
                self.threads.append(conn)
        finally:
            self.soc.close()

class ConnectionHandler(threading.Thread):
    def __init__(self, socClient, server, addr):
        threading.Thread.__init__(self)
        self.client = socClient
        self.server = server

    def run(self):
        try:
            data = self.client.recv(BUFLEN)
            # Enviar el Response HTTP real (decodificando los \r\n)
            self.target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.target.connect(("127.0.0.1", """ + local_port + r"""))
            
            # El truco: mandar la respuesta con los saltos de línea correctos
            self.client.sendall(RESPONSE.decode('string_escape'))
            
            self.do_proxy()
        except: pass
        finally: self.client.close()

    def do_proxy(self):
        socs = [self.client, self.target]
        while True:
            recv, _, err = select.select(socs, [], socs, 3)
            if err or not recv: break
            for in_ in recv:
                data = in_.recv(BUFLEN)
                if not data: return
                if in_ is self.target: self.client.send(data)
                else: self.target.send(data)

def main():
    print "Proxy iniciado en puerto " + str(LISTENING_PORT)
    server = Server(LISTENING_ADDR, LISTENING_PORT)
    server.start()
    while True: time.sleep(10)

if __name__ == '__main__':
    main()
"""

    # 4. Guardar y Lanzar
    with open('/root/proxy.py', 'w') as f:
        f.write(proxy_script)
    
    os.system("chmod +x /root/proxy.py")
    print(f" {Color.YELLOW}Iniciando en Screen...{Color.END}")
    os.system("screen -dmS pythonwe python2 /root/proxy.py")
    
    # Firewall
    os.system(f"iptables -I INPUT -p tcp --dport {port} -j ACCEPT")
    
    print(f"\n {Color.GREEN}✓ PROXY REPARADO EN PUERTO {port}{Color.END}")
    print(f" {Color.CYAN}Si usas TLS/SSL, recuerda que el Stunnel debe apuntar al puerto {port}{Color.END}")
    input("\nPresiona Enter...")
    
def stop_proxy():
    """Detener Proxy Python"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}DETENER PROXY PYTHON{Color.END}")
    print_line()
    
    try:
        # Mostrar proxies activos
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        proxy_processes = []
        
        for line in result.stdout.split('\n'):
            if 'proxy.py' in line or 'pythonwe' in line:
                if 'grep' not in line:
                    # Extraer puerto del proceso
                    import re
                    match = re.search(r'proxy\.py\s+(\d+)', line)
                    if match:
                        port = match.group(1)
                    else:
                        # Verificar en netstat
                        net_result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
                        for net_line in net_result.stdout.split('\n'):
                            if 'python' in net_line:
                                port_match = re.search(r':(\d+)\s', net_line)
                                if port_match:
                                    port = port_match.group(1)
                                    break
                        else:
                            port = "desconocido"
                    
                    pid = line.split()[1]
                    proxy_processes.append({'pid': pid, 'port': port, 'line': line})
        
        if not proxy_processes:
            print(f"\n {Color.YELLOW}No hay proxies Python activos{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        # Mostrar proxies encontrados
        print(f"\n {Color.YELLOW}Proxies Python activos:{Color.END}")
        unique_ports = {}
        for proc in proxy_processes:
            if proc['port'] not in unique_ports:
                unique_ports[proc['port']] = proc['pid']
        
        ports_list = list(unique_ports.keys())
        for i, port in enumerate(ports_list, 1):
            pid = unique_ports[port]
            print(f" {Color.GREEN}[{i}]{Color.END} Puerto {port} (PID: {pid})")
        
        print(f"\n {Color.GREEN}[0]{Color.END} Detener TODOS los proxies")
        print(f" {Color.RED}[X]{Color.END} Cancelar")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Selecciona opción: ").strip()
        
        if choice.upper() == 'X':
            return
        
        if choice == '0':
            # Detener todos
            confirm = input(f"\n {Color.YELLOW}¿Detener TODOS los proxies? (s/n): {Color.END}").strip().lower()
            if confirm != 's':
                return
            
            subprocess.run(['pkill', '-f', 'pythonwe'], stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'proxy.py'], stderr=subprocess.DEVNULL)
            subprocess.run(['screen', '-S', 'pythonwe', '-X', 'quit'], stderr=subprocess.DEVNULL)
            
            # Limpiar config
            with open(PROTOCOLS_FILE, 'r') as f:
                protocols = json.load(f)
            
            protocols['proxy']['enabled'] = False
            
            with open(PROTOCOLS_FILE, 'w') as f:
                json.dump(protocols, f, indent=4)
            
            print(f"\n {Color.GREEN}✓ Todos los proxies detenidos{Color.END}")
            moratech.log_action("admin", "Todos los proxies detenidos")
            
        else:
            # Detener proxy específico
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(ports_list):
                    port = ports_list[idx]
                    pid = unique_ports[port]
                    
                    # Matar proceso específico
                    subprocess.run(['kill', '-9', pid], stderr=subprocess.DEVNULL)
                    
                    # Cerrar puerto en firewall
                    subprocess.run(['iptables', '-D', 'INPUT', '-p', 'tcp', '--dport', port, '-j', 'ACCEPT'], stderr=subprocess.DEVNULL)
                    
                    print(f"\n {Color.GREEN}✓ Proxy en puerto {port} detenido{Color.END}")
                    moratech.log_action("admin", f"Proxy puerto {port} detenido")
                else:
                    print(f" {Color.RED}✗ Opción inválida{Color.END}")
            except ValueError:
                print(f" {Color.RED}✗ Opción inválida{Color.END}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
 
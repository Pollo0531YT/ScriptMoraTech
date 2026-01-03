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
    """Instalar Proxy Python con configuración dinámica (Websocket/Direct)"""
    import subprocess
    import json
    import time
    
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INSTALADOR PROXY PYTHON DINÁMICO{Color.END}")
    print_line()

    # 1. Recolección de Datos
    port = input(f"\n {Color.GREEN}Puerto para Proxy (default 80): {Color.END}").strip() or "80"
    
    local_port = input(f" {Color.GREEN}Puerto Local de Destino (SSH/Dropbear) [22]: {Color.END}").strip() or "22"
    
    print(f"\n {Color.YELLOW}--- CONFIGURACIÓN DE RESPUESTA ---{Color.END}")
    print(" [101] Para OVER WEBSOCKET")
    print(" [200] Para Connection Established")
    status_code = input(f" {Color.GREEN}Status de Respuesta [101]: {Color.END}").strip() or "101"

    print(f"\n {Color.YELLOW}--- MINI BANNER (Opcional) ---{Color.END}")
    mini_banner = input(f" {Color.GREEN}Texto o HTML para el banner: {Color.END}").strip()

    # Formatear Response y Banner
    banner_payload = f"<br><font color='green'>{mini_banner}</font><br>" if mini_banner else ""
    
    if status_code == "101":
        response_str = f"HTTP/1.1 101 Switching Protocols!\\r\\n\\r\\n{banner_payload}"
    else:
        response_str = f"HTTP/1.1 {status_code} Connection Established\\r\\n\\r\\n{banner_payload}"

    # 2. Liberar puerto si está ocupado
    try:
        result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
        pids = result.stdout.strip()
        if pids:
            print(f"\n {Color.RED}⚠ Liberando puerto {port}...{Color.END}")
            for pid in pids.split('\n'):
                subprocess.run(['kill', '-9', pid], stderr=subprocess.DEVNULL)
            time.sleep(1)
    except:
        pass

    print(f"\n {Color.YELLOW}Instalando dependencias...{Color.END}")
    try:
        # Detener procesos previos
        subprocess.run(['pkill', '-f', 'pythonwe'], stderr=subprocess.DEVNULL)
        
        # Instalación de paquetes necesarios
        subprocess.run(['apt-get', 'update'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['apt-get', 'install', 'python2', 'screen', 'lsof', '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 3. Construcción del Script Proxy.py
        proxy_script = f"""#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import socket, threading, thread, select, signal, sys, time, getopt

# CONFIG
LISTENING_ADDR = '0.0.0.0'
LISTENING_PORT = {port}
PASS = ''

# CONST
BUFLEN = 4096 * 4
TIMEOUT = 60
DEFAULT_HOST = "127.0.0.1:{local_port}"
RESPONSE = '{response_str}'
 
class Server(threading.Thread):
    def __init__(self, host, port):
        threading.Thread.__init__(self)
        self.running = False
        self.host = host
        self.port = port
        self.threads = []
        self.threadsLock = threading.Lock()
        self.logLock = threading.Lock()

    def run(self):
        self.soc = socket.socket(socket.AF_INET)
        self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.soc.settimeout(2)
        self.soc.bind((self.host, self.port))
        self.soc.listen(0)
        self.running = True

        try:                    
            while self.running:
                try:
                    c, addr = self.soc.accept()
                    c.setblocking(1)
                except socket.timeout:
                    continue
                
                conn = ConnectionHandler(c, self, addr)
                conn.start();
                self.addConn(conn)
        finally:
            self.running = False
            self.soc.close()
            
    def printLog(self, log):
        self.logLock.acquire()
        print log
        self.logLock.release()
    
    def addConn(self, conn):
        try:
            self.threadsLock.acquire()
            if self.running:
                self.threads.append(conn)
        finally:
            self.threadsLock.release()
                    
    def removeConn(self, conn):
        try:
            self.threadsLock.acquire()
            self.threads.remove(conn)
        finally:
            self.threadsLock.release()
                
    def close(self):
        try:
            self.running = False
            self.threadsLock.acquire()
            threads = list(self.threads)
            for c in threads:
                c.close()
        finally:
            self.threadsLock.release()
            

class ConnectionHandler(threading.Thread):
    def __init__(self, socClient, server, addr):
        threading.Thread.__init__(self)
        self.clientClosed = False
        self.targetClosed = True
        self.client = socClient
        self.client_buffer = ''
        self.server = server
        self.log = 'Connection: ' + str(addr)

    def close(self):
        try:
            if not self.clientClosed:
                self.client.shutdown(socket.SHUT_RDWR)
                self.client.close()
        except: pass
        finally: self.clientClosed = True
            
        try:
            if not self.targetClosed:
                self.target.shutdown(socket.SHUT_RDWR)
                self.target.close()
        except: pass
        finally: self.targetClosed = True

    def run(self):
        try:
            self.client_buffer = self.client.recv(BUFLEN)
            hostPort = self.findHeader(self.client_buffer, 'X-Real-Host')
            
            if hostPort == '': hostPort = DEFAULT_HOST

            split = self.findHeader(self.client_buffer, 'X-Split')
            if split != '': self.client.recv(BUFLEN)
            
            if hostPort != '':
                passwd = self.findHeader(self.client_buffer, 'X-Pass')
                if len(PASS) != 0 and passwd == PASS:
                    self.method_CONNECT(hostPort)
                elif len(PASS) != 0 and passwd != PASS:
                    self.client.send('HTTP/1.1 400 WrongPass!\\r\\n\\r\\n')
                elif hostPort.startswith('127.0.0.1') or hostPort.startswith('localhost'):
                    self.method_CONNECT(hostPort)
                else:
                    self.client.send('HTTP/1.1 403 Forbidden!\\r\\n\\r\\n')
            else:
                self.client.send('HTTP/1.1 400 NoXRealHost!\\r\\n\\r\\n')
        except Exception as e:
            self.log += ' - error: ' + str(e)
            self.server.printLog(self.log)
        finally:
            self.close()
            self.server.removeConn(self)

    def findHeader(self, head, header):
        aux = head.find(header + ': ')
        if aux == -1: return ''
        aux = head.find(':', aux)
        head = head[aux+2:]
        aux = head.find('\\r\\n')
        if aux == -1: return ''
        return head[:aux];

    def connect_target(self, host):
        i = host.find(':')
        if i != -1:
            port = int(host[i+1:])
            host = host[:i]
        else: port = 80
        (soc_family, soc_type, proto, _, address) = socket.getaddrinfo(host, port)[0]
        self.target = socket.socket(soc_family, soc_type, proto)
        self.targetClosed = False
        self.target.connect(address)

    def method_CONNECT(self, path):
        self.log += ' - CONNECT ' + path
        self.connect_target(path)
        self.client.sendall(RESPONSE)
        self.client_buffer = ''
        self.server.printLog(self.log)
        self.doCONNECT()

    def doCONNECT(self):
        socs = [self.client, self.target]
        count = 0
        error = False
        while True:
            count += 1
            (recv, _, err) = select.select(socs, [], socs, 3)
            if err: error = True
            if recv:
                for in_ in recv:
                    try:
                        data = in_.recv(BUFLEN)
                        if data:
                            if in_ is self.target: self.client.send(data)
                            else:
                                while data:
                                    byte = self.target.send(data)
                                    data = data[byte:]
                            count = 0
                        else: break
                    except:
                        error = True
                        break
            if count == TIMEOUT or error: break

def main():
    print "\\n=============================="
    print "      PYTHON PROXY DINAMICO"
    print "=============================="
    print "Puerto Proxy: " + str(LISTENING_PORT)
    print "Puerto Local: " + DEFAULT_HOST
    print "Iniciado correctamente\\n"
    server = Server(LISTENING_ADDR, LISTENING_PORT)
    server.start()
    while True:
        try: time.sleep(2)
        except KeyboardInterrupt:
            server.close()
            break

if __name__ == '__main__':
    main()
"""

        # 4. Guardar e Iniciar
        with open('/root/proxy.py', 'w') as f:
            f.write(proxy_script)
        
        subprocess.run(['chmod', '+x', '/root/proxy.py'])
        
        print(f" {Color.YELLOW}Iniciando en Screen 'pythonwe'...{Color.END}")
        subprocess.run(['screen', '-dmS', 'pythonwe', 'python2', '/root/proxy.py'])
        time.sleep(2)

        # 5. Firewall y Configuración Final
        subprocess.run(['ufw', 'allow', port], stderr=subprocess.DEVNULL)
        
        # Guardar en archivo de protocolos
        with open(PROTOCOLS_FILE, 'r') as f:
            protocols = json.load(f)
        protocols['proxy']['enabled'] = True
        protocols['proxy']['port'] = int(port)
        with open(PROTOCOLS_FILE, 'w') as f:
            json.dump(protocols, f, indent=4)

        print(f"\n {Color.GREEN}✓ PROXY INSTALADO EXITOSAMENTE{Color.END}")
        print(f" {Color.CYAN}Puerto: {port} -> Destino Local: {local_port}{Color.END}")
        print(f" {Color.CYAN}Response: {status_code}{Color.END}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error crítico: {e}{Color.END}")

    input(f"\n {Color.CYAN}Presiona Enter para volver...{Color.END}")

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
 
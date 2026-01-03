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
    """Instalar Proxy Python (Python 2) - versión que funciona"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INSTALANDO PROXY PYTHON{Color.END}")
    print_line()

    port = input(f"\n {Color.GREEN}Puerto para Proxy (default 80): {Color.END}").strip()
    if not port:
        port = "80"

    # Verificar y liberar puerto si está ocupado
    try:
        result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
        pids = result.stdout.strip()
        if pids:
            print(f"\n {Color.RED}⚠ Puerto {port} está en uso:{Color.END}")
            result_process = subprocess.run(['lsof', '-i', f':{port}'], capture_output=True, text=True)
            print(result_process.stdout)
            confirm = input(f"\n {Color.YELLOW}¿Liberar el puerto {port}? (s/n): {Color.END}").strip().lower()
            if confirm == 's':
                for pid in pids.split('\n'):
                    if pid:
                        subprocess.run(['kill', '-9', pid], stderr=subprocess.DEVNULL)
                import time
                time.sleep(2)
            else:
                print(f" {Color.RED}Instalación cancelada{Color.END}")
                input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                return
    except:
        pass

    print(f"\n {Color.YELLOW}Instalando Proxy Python en puerto {port}...{Color.END}")

    try:
        # Detener procesos previos
        subprocess.run(['pkill', '-f', 'pythonwe'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-f', 'proxy.py'], stderr=subprocess.DEVNULL)

        # Instalar dependencias
        print(f" {Color.YELLOW}Instalando dependencias...{Color.END}")
        subprocess.run(['apt-get', 'update'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['apt-get', 'install', 'python2', '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['apt-get', 'install', 'python', '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['apt-get', 'install', 'screen', '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['apt-get', 'install', 'lsof', '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Detectar puerto SSH
        ssh_port = '22'
        print(f" {Color.YELLOW}Puerto SSH: {ssh_port}{Color.END}")

        # Script Python 2 ORIGINAL que funciona
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
DEFAULT_HOST = "127.0.0.1:{ssh_port}"
RESPONSE = 'HTTP/1.1 101 Switching Protocols! \\r\\n\\r\\n'
 
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
        except:
            pass
        finally:
            self.clientClosed = True
            
        try:
            if not self.targetClosed:
                self.target.shutdown(socket.SHUT_RDWR)
                self.target.close()
        except:
            pass
        finally:
            self.targetClosed = True

    def run(self):
        try:
            self.client_buffer = self.client.recv(BUFLEN)
        
            hostPort = self.findHeader(self.client_buffer, 'X-Real-Host')
            
            if hostPort == '':
                hostPort = DEFAULT_HOST

            split = self.findHeader(self.client_buffer, 'X-Split')

            if split != '':
                self.client.recv(BUFLEN)
            
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
    
        if aux == -1:
            return ''

        aux = head.find(':', aux)
        head = head[aux+2:]
        aux = head.find('\\r\\n')

        if aux == -1:
            return ''

        return head[:aux];

    def connect_target(self, host):
        i = host.find(':')
        if i != -1:
            port = int(host[i+1:])
            host = host[:i]
        else:
            port = 80

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
            if err:
                error = True
            if recv:
                for in_ in recv:
                    try:
                        data = in_.recv(BUFLEN)
                        if data:
                            if in_ is self.target:
                                self.client.send(data)
                            else:
                                while data:
                                    byte = self.target.send(data)
                                    data = data[byte:]
                            count = 0
                        else:
                            break
                    except:
                        error = True
                        break
            if count == TIMEOUT:
                error = True

            if error:
                break


def main():
    print "\\n=============================="
    print "      PYTHON PROXY"
    print "=============================="
    print "IP: " + LISTENING_ADDR
    print "Puerto: " + str(LISTENING_PORT)
    print "Iniciado correctamente\\n"
    
    server = Server(LISTENING_ADDR, LISTENING_PORT)
    server.start()

    while True:
        try:
            time.sleep(2)
        except KeyboardInterrupt:
            print 'Deteniendo...'
            server.close()
            break

if __name__ == '__main__':
    main()
"""

        # Guardar script
        with open('/root/proxy.py', 'w') as f:
            f.write(proxy_script)
        
        subprocess.run(['chmod', '+x', '/root/proxy.py'])

        # Iniciar proxy en screen con Python 2
        print(f" {Color.YELLOW}Iniciando proxy en segundo plano...{Color.END}")
        subprocess.run(['screen', '-wipe'], stderr=subprocess.DEVNULL)
        subprocess.run(['screen', '-dmS', 'pythonwe', 'python2', '/root/proxy.py'])

        import time
        time.sleep(2)

        # Verificar si inició
        result = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        if 'pythonwe' in result.stdout:
            print(f" {Color.GREEN}✓ Proxy iniciado en screen{Color.END}")
        else:
            print(f" {Color.RED}⚠ Proxy pudo no iniciar correctamente{Color.END}")

        # Abrir puerto
        subprocess.run(['iptables', '-I', 'INPUT', '-p', 'tcp', '--dport', port, '-j', 'ACCEPT'])
        subprocess.run(['ufw', 'allow', port], stderr=subprocess.DEVNULL)

        # Configurar forwarding
        print(f" {Color.YELLOW}Configurando forwarding...{Color.END}")
        moratech.configure_forwarding()
        print(f" {Color.GREEN}✓ Forwarding configurado{Color.END}")

        # Guardar en config
        with open(PROTOCOLS_FILE, 'r') as f:
            protocols = json.load(f)

        protocols['proxy']['enabled'] = True
        protocols['proxy']['port'] = int(port)

        with open(PROTOCOLS_FILE, 'w') as f:
            json.dump(protocols, f, indent=4)

        print(f"\n {Color.GREEN}✓ Proxy Python instalado en puerto {port}{Color.END}")
        print(f" {Color.YELLOW}Para ver logs: screen -r pythonwe{Color.END}")
        moratech.log_action("admin", f"Proxy Python configurado en puerto {port}")

    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()

    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def stop_proxy():
    """Detener Proxy Python (robusto: usa pgrep + lsof/ss, no depende de netstat)."""
    import re
    from pathlib import Path
    import shutil
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}DETENER PROXY PYTHON{Color.END}")
    print_line()

    try:
        # 1) Encontrar PIDs relevantes (proxy.py / pythonwe)
        pids = set()

        def safe_run(cmd):
            try:
                return subprocess.run(cmd, capture_output=True, text=True, check=False)
            except Exception:
                return None

        # pgrep first (fast)
        for pattern in ['pythonwe', 'proxy.py']:
            r = safe_run(['pgrep', '-f', pattern])
            if r and r.stdout.strip():
                for ln in r.stdout.splitlines():
                    ln = ln.strip()
                    if ln.isdigit():
                        pids.add(ln)

        # fallback: ps aux search
        if not pids:
            r = safe_run(['ps', 'aux'])
            if r and r.stdout:
                for line in r.stdout.splitlines():
                    if ('proxy.py' in line or 'pythonwe' in line) and 'grep' not in line:
                        parts = line.split()
                        if len(parts) >= 2 and parts[1].isdigit():
                            pids.add(parts[1])

        if not pids:
            print(f"\n {Color.YELLOW}No hay proxies Python activos (no se encontraron pids){Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return

        # 2) Para cada PID intentar detectar puertos (lsof preferible, si no -> ss)
        pid_to_ports = {}
        lsof_ok = shutil.which('lsof') is not None

        ss_output = None
        if not lsof_ok:
            # obtener ss output una sola vez para fallback
            ss_r = safe_run(['ss', '-tlnp'])
            ss_output = ss_r.stdout if ss_r and ss_r.stdout else ''

        for pid in pids:
            ports = set()
            if lsof_ok:
                r = safe_run(['lsof', '-Pan', '-p', pid, '-iTCP', '-sTCP:LISTEN'])
                if r and r.stdout:
                    for ln in r.stdout.splitlines()[1:]:
                        m = re.search(r':(\d+)->|:(\d+)\s', ln)
                        if m:
                            port = m.group(1) or m.group(2)
                            if port:
                                ports.add(port)
            # fallback using ss output (pid=1234 in the "users:" field)
            if not ports and ss_output is not None:
                for ln in ss_output.splitlines():
                    if f"pid={pid}" in ln or f"pid={pid}," in ln:
                        m = re.search(r':(\d+)\s', ln)
                        if m:
                            ports.add(m.group(1))
            if not ports:
                ports.add("desconocido")

            pid_to_ports[pid] = sorted(list(ports))

        # 3) Mostrar opciones al usuario
        print(f"\n {Color.YELLOW}Proxies Python detectados:{Color.END}")
        # construir lista única de (port->pid) priorizando puertos reales
        unique = {}
        for pid, ports in pid_to_ports.items():
            for port in ports:
                if port not in unique:
                    unique[port] = pid

        ports_list = list(unique.keys())
        for i, port in enumerate(ports_list, 1):
            pid = unique[port]
            print(f" {Color.GREEN}[{i}]{Color.END} Puerto {port} (PID: {pid})")

        print(f"\n {Color.GREEN}[0]{Color.END} Detener TODOS los proxies")
        print(f" {Color.RED}[X]{Color.END} Cancelar")
        print_line()

        choice = input(f" {Color.CYAN}►{Color.END} Selecciona opción: ").strip()
        if choice.upper() == 'X':
            return

        # 4) Ejecución de la acción
        def safe_kill(pid):
            try:
                subprocess.run(['kill', '-9', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass

        def remove_iptables_port(port):
            try:
                subprocess.run(['iptables', '-D', 'INPUT', '-p', 'tcp', '--dport', str(port), '-j', 'ACCEPT'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass
            try:
                subprocess.run(['ufw', 'delete', 'allow', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass

        if choice == '0':
            confirm = input(f"\n {Color.YELLOW}¿Detener TODOS los proxies? (s/n): {Color.END}").strip().lower()
            if confirm != 's':
                return
            # kill by name + screen quit
            subprocess.run(['pkill', '-f', 'pythonwe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'proxy.py'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['screen', '-S', 'pythonwe', '-X', 'quit'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # remove iptables for detected ports
            for port in ports_list:
                if port != "desconocido":
                    remove_iptables_port(port)
            # update config
            try:
                with open(PROTOCOLS_FILE, 'r') as f:
                    protocols = json.load(f)
                protocols.setdefault('proxy', {})['enabled'] = False
                protocols['proxy'].pop('port', None)
                with open(PROTOCOLS_FILE, 'w') as f:
                    json.dump(protocols, f, indent=4)
            except Exception:
                pass
            print(f"\n {Color.GREEN}✓ Todos los proxies detenidos{Color.END}")
            moratech.log_action("admin", "Todos los proxies detenidos")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return

        # user selected single
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(ports_list):
                port = ports_list[idx]
                pid = unique[port]
                # kill and clean
                safe_kill(pid)
                remove_iptables_port(port)
                # try to also quit screen session
                subprocess.run(['screen', '-S', 'pythonwe', '-X', 'quit'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                # update config: if the port matches protocols.json remove it
                try:
                    with open(PROTOCOLS_FILE, 'r') as f:
                        protocols = json.load(f)
                    if protocols.get('proxy', {}).get('port') == int(port):
                        protocols['proxy']['enabled'] = False
                        protocols['proxy'].pop('port', None)
                        with open(PROTOCOLS_FILE, 'w') as f:
                            json.dump(protocols, f, indent=4)
                except Exception:
                    pass

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

#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Template del Proxy Python - MORATECH
Este archivo es solo una plantilla, no se ejecuta directamente
"""

PROXY_SCRIPT = """#!/usr/bin/env python
# encoding: utf-8
import socket, threading, thread, select, signal, sys, time, getopt, resource

# Subir limite de archivos abiertos (default 1024 se agota con muchos clientes)
try:
    resource.setrlimit(resource.RLIMIT_NOFILE, (65535, 65535))
except Exception:
    pass

# Listen
LISTENING_ADDR = '0.0.0.0'
if sys.argv[1:]:
  LISTENING_PORT = sys.argv[1]
else:
  LISTENING_PORT = 80  
#Pass
PASS = ''
# CONST
BUFLEN = 4096 * 4
TIMEOUT = 60
DEFAULT_HOST = '127.0.0.1:22'
MSG = '<span style=color: #ff0000;><strong><span style=color: #ff0000;>A</span><span style=color: #ff9900;>D</span><span style=color: #008000;>M</span><span style=color: #0000ff;>c</span><span style=color: #ff0000;>g</span><span style=color: #ff9900;>h</span><span style=color: #008000;>+</span></strong></span>'
STATUS_RESP = '101'
FTAG = '\\r\\nContent-length: 0\\r\\n\\r\\nHTTP/1.1 200 Connection Established\\r\\n\\r\\n'

if STATUS_RESP == '101':
    STATUS_TXT = '<font color="green">Web Socket Protocol</font>'
else:
    STATUS_TXT = '<font color="red">Connection established</font>'

#RESPONSE = "HTTP/1.1 " + str(STATUS_RESP) + ' ' + str(STATUS_TXT) + ' ' +  str(MSG) + ' ' +  str(FTAG)
RESPONSE = "HTTP/1.1 " + str(STATUS_RESP) + ' ' +  str(MSG) + ' ' +  str(FTAG)


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
        intport = int(self.port)
        self.soc.bind((self.host, intport))
        self.soc.listen(0)
        self.running = True

        try:
            while self.running:
                try:
                    c, addr = self.soc.accept()
                    c.setblocking(1)
                except socket.timeout:
                    continue
                except socket.error as e:
                    # Ej: Too many open files. Esperar y seguir, no matar el servidor
                    self.printLog('accept error: ' + str(e))
                    time.sleep(1)
                    continue

                conn = ConnectionHandler(c, self, addr)
                # Agregar ANTES de start: si la conexion muere al instante,
                # removeConn ya la encuentra y no queda colgada en la lista
                self.addConn(conn)
                conn.start()
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
            if conn in self.threads:
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
        # shutdown falla si el otro lado ya cerro; close() debe correr igual
        if not self.clientClosed:
            try:
                self.client.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                self.client.close()
            except:
                pass
            self.clientClosed = True

        if not self.targetClosed:
            try:
                self.target.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                self.target.close()
            except:
                pass
            self.targetClosed = True

    def run(self):
        try:
            # Clientes que conectan y no mandan nada no dejan el hilo colgado
            self.client.settimeout(TIMEOUT)
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
                print '- No X-Real-Host!'
                self.client.send('HTTP/1.1 400 NoXRealHost!\\r\\n\\r\\n')

        except Exception as e:
            self.log += ' - error: ' + str(e)
            self.server.printLog(self.log)
            pass
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
            if self.method=='CONNECT':
                port = 22
            else:
                port = sys.argv[1]

        (soc_family, soc_type, proto, _, address) = socket.getaddrinfo(host, port)[0]

        self.target = socket.socket(soc_family, soc_type, proto)
        self.targetClosed = False
        self.target.connect(address)

    def method_CONNECT(self, path):
        self.log += ' - CONNECT ' + path

        self.connect_target(path)
        self.client.sendall(RESPONSE)
        self.client_buffer = ''
        # Tunel establecido: sin timeout, el control de inactividad lo hace doCONNECT
        self.client.settimeout(None)

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
                                self.client.sendall(data)
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


def print_usage():
    print 'Usage: proxy.py -p <port>'
    print '       proxy.py -b <bindAddr> -p <port>'
    print '       proxy.py -b 0.0.0.0 -p 80'

def parse_args(argv):
    global LISTENING_ADDR
    global LISTENING_PORT
    
    try:
        opts, args = getopt.getopt(argv,"hb:p:",["bind=","port="])
    except getopt.GetoptError:
        print_usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print_usage()
            sys.exit()
        elif opt in ("-b", "--bind"):
            LISTENING_ADDR = arg
        elif opt in ("-p", "--port"):
            LISTENING_PORT = int(arg)


def main(host=LISTENING_ADDR, port=LISTENING_PORT):
    
    print "\\033[0;34m•"*8,"\\033[1;32m PROXY PYTHON WEBSOCKET","\\033[0;34m•"*8,"\\n"
    print "\\033[1;33mIP:\\033[1;32m " + LISTENING_ADDR
    print "\\033[1;33mPORTA:\\033[1;32m " + str(LISTENING_PORT) + "\\n"
    print "\\033[0;34m•"*10,"\\033[1;32m ChumoGH ADMcgh Plus","\\033[0;34m•\\033[1;37m"*11,"\\n"
    
    server = Server(LISTENING_ADDR, LISTENING_PORT)
    server.start()

    while True:
        try:
            time.sleep(2)
        except KeyboardInterrupt:
            print 'Parando...'
            server.close()
            break
    
if __name__ == '__main__':
    parse_args(sys.argv[1:])
    main()
"""

# Vigilante: cron cada minuto. Si el proxy no corre o su socket de escucha murio
# (proceso vivo pero puerto cerrado), lo reinicia.
WATCHDOG_PATH = '/usr/local/bin/moratech-proxy-watchdog'
WATCHDOG_CRON = '/etc/cron.d/moratech-proxy'

WATCHDOG_SCRIPT = r"""#!/bin/bash
# MORATECH - vigilante del Proxy Python
[ -f /root/proxy.py ] || exit 0
PID=$(pgrep -f '^python[0-9.]* /root/proxy.py' | head -1)
if [ -n "$PID" ] && ss -tlnp | grep -q "pid=$PID,"; then
    exit 0
fi
[ -n "$PID" ] && kill -9 $PID 2>/dev/null
screen -S pythonwe -X quit >/dev/null 2>&1
screen -wipe >/dev/null 2>&1
PY=$(command -v python2 || command -v python)
screen -dmS pythonwe $PY /root/proxy.py
echo "$(date '+%Y-%m-%d %H:%M:%S') proxy reiniciado (pid previo: ${PID:-ninguno})" >> /var/log/moratech-proxy-watchdog.log
"""

WATCHDOG_CRON_LINE = "* * * * * root /bin/bash " + WATCHDOG_PATH + " >/dev/null 2>&1\n"

#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Template del Proxy Python - MORATECH
Este archivo es solo una plantilla, no se ejecuta directamente
"""

PROXY_SCRIPT = """#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import socket
try:
    import thread
except ImportError:
    import _thread as thread

LISTENING_ADDR = '0.0.0.0'
LISTENING_PORT = {port}
PASS = ''

BUFLEN = 8196 * 8

def forward(dst, target):
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.connect(target)
    
    def recv(source, dest):
        string = ' '
        while True:
            try:
                data = source.recv(BUFLEN)
            except:
                break
            if not data: break
            dest.sendall(data)
        source.close()
        dest.close()
    
    thread.start_new_thread(recv, (dst, soc))
    thread.start_new_thread(recv, (soc, dst))

class ServerThread:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr

    def run(self):
        first_data = self.conn.recv(BUFLEN)
        
        if not first_data:
            self.conn.close()
            return

        first_line = first_data.split(b'\\n')[0].decode('utf-8', errors='ignore')
        parts = first_line.split(' ')
        if len(parts) < 2:
            self.conn.close()
            return
            
        url = parts[1]
        
        http_pos = url.find("://")
        if http_pos == -1:
            temp = url
        else:
            temp = url[(http_pos + 3):]
        
        port_pos = temp.find(":")
        webserver_pos = temp.find("/")
        
        if webserver_pos == -1:
            webserver_pos = len(temp)
        
        webserver = ""
        port = -1
        
        if port_pos == -1 or webserver_pos < port_pos:
            port = 22
            webserver = temp[:webserver_pos]
        else:
            try:
                port = int((temp[(port_pos + 1):])[:webserver_pos - port_pos - 1])
            except:
                port = 22
            webserver = temp[:port_pos]
        
        try:
            forward(self.conn, (webserver, port))
        except Exception as e:
            self.conn.close()

def start_server():
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    soc.bind((LISTENING_ADDR, LISTENING_PORT))
    soc.listen(0)
    
    print("[*] Server started on %s:%d" % (LISTENING_ADDR, LISTENING_PORT))
    
    try:
        while True:
            conn, addr = soc.accept()
            t = ServerThread(conn, addr)
            thread.start_new_thread(t.run, ())
    except KeyboardInterrupt:
        print("\\n[*] Shutting down...")
        soc.close()

if __name__ == '__main__':
    start_server()
"""
#!/usr/bin/env python3
"""
Módulo SSL - Gestión de Stunnel
"""
import subprocess
import json
import os
from pathlib import Path

from modules.common import Color, PROTOCOLS_FILE, clear_screen, print_banner, print_line
import moratech

def menu_ssl():
    """Menu de ssl"""
    while True:
        #show_dashboard()

        # Mostrar estado actual - DETECCIÓN AUTOMÁTICA
        try:
            result = subprocess.run(['ss', '-tulpn'], capture_output=True, text=True)
            output = result.stdout
            
            # Detectar todos los puertos SSL/Stunnel
            ssl_ports = []
            for line in output.split('\n'):
                if 'stunnel' in line:
                    import re
                    match = re.search(r':(\d+)\s', line)
                    if match:
                        ssl_ports.append(match.group(1))
            
            if ssl_ports:
                ports_str = ", ".join(ssl_ports)
                ssl_status = f"{Color.GREEN}ACTIVO - Puerto(s) {ports_str}{Color.END}"
            else:
                ssl_status = f"{Color.YELLOW}INACTIVO{Color.END}"
        
            print(f" {Color.CYAN}∘{Color.END} CONFIGURACION SSL: {ssl_status}")
            print_line()
        except:
            pass
  
        print(f"{Color.GREEN}1.{Color.END} Agregar puerto")
        print(f"{Color.GREEN}2.{Color.END} Detener puerto")
        print(f"{Color.GREEN}0.{Color.END} Volver")
        
        choice = input(f"\n{Color.YELLOW}Selecciona: {Color.END}").strip()
        if choice == '1':
            install_ssl()
        elif choice == '2':
            stop_ssl()    
        elif choice == '0':
            break
        else:
            print(f"\n{Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

def install_ssl():
    """Instalar SSL con Let's Encrypt o Añadir puertos adicionales dinámicamente"""
    import os
    import subprocess
    import json
    import time

    clear_screen()
    print_banner()
    print_line()
    
    cert_file = '/etc/stunnel/stunnel.pem'
    conf_file = '/etc/stunnel/stunnel.conf'
    
    # 1. DETECCIÓN DE CERTIFICADO EXISTENTE
    if os.path.exists(cert_file):
        print(f" {Color.GREEN}✓ Certificado SSL detectado (Let's Encrypt).{Color.END}")
        print(f" {Color.CYAN}MODO: AÑADIR NUEVO PUERTO{Color.END}")
        domain = "EXISTENTE"
    else:
        print(f" {Color.CYAN}MODO: INSTALACIÓN INICIAL (Certbot){Color.END}")
        domain = input(f"\n {Color.GREEN}Dominio (ej: vps.midominio.com): {Color.END}").strip()
        if not domain:
            print(f" {Color.RED}✗ Dominio requerido.{Color.END}")
            time.sleep(2)
            return

    # 2. DATOS DEL PUERTO
    port = input(f" {Color.GREEN}Puerto SSL a abrir (ej: 443, 444): {Color.END}").strip()
    if not port: port = "443"
    
    # Verificar si el puerto ya está configurado en el archivo para evitar duplicados
    if os.path.exists(conf_file):
        with open(conf_file, 'r') as f:
            if f"accept = {port}" in f.read():
                print(f"\n {Color.RED}✗ El puerto {port} ya está configurado en Stunnel.{Color.END}")
                input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                return

    local_port = input(f" {Color.GREEN}Puerto Local de destino (SSH) [22]: {Color.END}").strip() or "22"

    try:
        # 3. PROCESO DE CERTBOT (SOLO SI NO EXISTE CERTIFICADO)
        if domain != "EXISTENTE":
            print(f"\n {Color.YELLOW}Obteniendo certificado Let's Encrypt...{Color.END}")
            
            # Detener servicios que usen el puerto 80
            subprocess.run(['pkill', '-f', 'pythonwe'], stderr=subprocess.DEVNULL)
            subprocess.run(['systemctl', 'stop', 'nginx'], stderr=subprocess.DEVNULL)
            
            # Instalar paquetes si no están
            subprocess.run(['apt-get', 'install', '-y', 'stunnel4', 'certbot'], stdout=subprocess.DEVNULL)

            result = subprocess.run([
                'certbot', 'certonly', '--standalone', 
                '-d', domain, 
                '--non-interactive', 
                '--agree-tos', 
                '--register-unsafely-without-email'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
                key_path = f"/etc/letsencrypt/live/{domain}/privkey.pem"
                # Crear el .pem combinado
                subprocess.run(f'cat {cert_path} {key_path} > {cert_file}', shell=True)
                subprocess.run(['chmod', '600', cert_file])
                print(f" {Color.GREEN}✓ Certificado generado exitosamente.{Color.END}")
            else:
                print(f" {Color.RED}✗ Fallo en Certbot: {result.stderr}{Color.END}")
                input(" Presiona Enter..."); return

        # 4. CONFIGURACIÓN DEL ARCHIVO STUNNEL.CONF
        # Si el archivo no existe o está vacío, creamos la cabecera global
        if not os.path.exists(conf_file) or os.path.getsize(conf_file) == 0:
            stunnel_conf = f"""cert = /etc/stunnel/stunnel.pem
client = no
socket = a:SO_REUSEADDR=1
socket = l:TCP_NODELAY=1
socket = r:TCP_NODELAY=1

[ssl-{port}]
connect = 127.0.0.1:{local_port}
accept = {port}
TIMEOUTclose = 0
"""
            with open(conf_file, 'w') as f:
                f.write(stunnel_conf)
        else:
            # Si ya existe, solo añadimos el nuevo bloque al final
            nuevo_bloque = f"""
[ssl-{port}]
connect = 127.0.0.1:{local_port}
accept = {port}
TIMEOUTclose = 0
"""
            with open(conf_file, 'a') as f:
                f.write(nuevo_bloque)

        # 5. ACTIVACIÓN Y REINICIO
        print(f" {Color.YELLOW}Reiniciando servicios...{Color.END}")
        
        # Asegurar que stunnel4 esté habilitado en /etc/default/stunnel4
        with open('/etc/default/stunnel4', 'w') as f:
            f.write('ENABLED=1\nFILES="/etc/stunnel/*.conf"\n')

        subprocess.run(['systemctl', 'daemon-reload'])
        subprocess.run(['systemctl', 'restart', 'stunnel4'])
        subprocess.run(['systemctl', 'enable', 'stunnel4'], stderr=subprocess.DEVNULL)

        # Abrir puertos en Firewall
        subprocess.run(['ufw', 'allow', port], stderr=subprocess.DEVNULL)
        subprocess.run(['iptables', '-I', 'INPUT', '-p', 'tcp', '--dport', port, '-j', 'ACCEPT'])

        # Guardar en JSON (opcional para tu panel)
        try:
            with open(PROTOCOLS_FILE, 'r') as f:
                protocols = json.load(f)
            protocols['ssl']['enabled'] = True
            protocols['ssl']['port'] = int(port) # Registra el último puerto agregado
            with open(PROTOCOLS_FILE, 'w') as f:
                json.dump(protocols, f, indent=4)
        except: pass

        print(f"\n {Color.GREEN}✓ PUERTO {port} CONFIGURADO CORRECTAMENTE{Color.END}")
        print(f" {Color.CYAN}Destino: 127.0.0.1:{local_port}{Color.END}")

    except Exception as e:
        print(f"\n {Color.RED}✗ Error en la instalación: {e}{Color.END}")

    input(f"\n {Color.CYAN}Presiona Enter para volver...{Color.END}")
    
def stop_ssl():
    
    """Detener SSL/Stunnel"""
    clear_screen()
    print_line()
    print(f" {Color.CYAN}DETENER SSL/STUNNEL{Color.END}")
    print_line()
    
    try:
        # Mostrar puertos SSL activos
        result = subprocess.run(['ss', '-tulpn'], capture_output=True, text=True)
        ssl_ports = []
        
        for line in result.stdout.split('\n'):
            if 'stunnel' in line:
                import re
                match = re.search(r':(\d+)\s', line)
                if match:
                    ssl_ports.append(match.group(1))
        
        if not ssl_ports:
            print(f"\n {Color.YELLOW}No hay puertos SSL activos{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        # Eliminar duplicados y ordenar
        ssl_ports = sorted(list(set(ssl_ports)))
        
        print(f"\n {Color.YELLOW}Puertos SSL activos:{Color.END}")
        for i, port in enumerate(ssl_ports, 1):
            print(f" {Color.GREEN}[{i}]{Color.END} Puerto {port}")
        
        print(f"\n {Color.GREEN}[0]{Color.END} Detener TODOS los puertos SSL")
        print(f" {Color.RED}[X]{Color.END} Cancelar")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Selecciona opción: ").strip()
        
        if choice.upper() == 'X':
            return
        
        if choice == '0':
            # Detener todo
            confirm = input(f"\n {Color.YELLOW}¿Detener TODOS los servicios SSL? (s/n): {Color.END}").strip().lower()
            if confirm != 's':
                return
            
            subprocess.run(['pkill', '-f', 'stunnel4'], stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'stunnel'], stderr=subprocess.DEVNULL)
            subprocess.run(['service', 'stunnel4', 'stop'], stderr=subprocess.DEVNULL)
            
            # Limpiar config
            with open(PROTOCOLS_FILE, 'r') as f:
                protocols = json.load(f)
            
            protocols['ssl']['enabled'] = False
            
            with open(PROTOCOLS_FILE, 'w') as f:
                json.dump(protocols, f, indent=4)
            
            print(f"\n {Color.GREEN}✓ Todos los servicios SSL detenidos{Color.END}")
            moratech.log_action("admin", "Todos los servicios SSL detenidos")
            
        else:
            # Detener puerto específico
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(ssl_ports):
                    port = ssl_ports[idx]
                    
                    # Leer configuración actual
                    with open('/etc/stunnel/stunnel.conf', 'r') as f:
                        lines = f.readlines()
                    
                    # Filtrar secciones que usan ese puerto
                    new_lines = []
                    skip = False
                    
                    for line in lines:
                        if line.strip().startswith('['):
                            skip = False
                        
                        if f'accept = {port}' in line:
                            skip = True
                            continue
                        
                        if not skip:
                            new_lines.append(line)
                    
                    # Guardar nueva configuración
                    with open('/etc/stunnel/stunnel.conf', 'w') as f:
                        f.writelines(new_lines)
                    
                    # Reiniciar stunnel
                    subprocess.run(['service', 'stunnel4', 'restart'], stderr=subprocess.DEVNULL)
                    
                    # Cerrar puerto en firewall
                    subprocess.run(['iptables', '-D', 'INPUT', '-p', 'tcp', '--dport', port, '-j', 'ACCEPT'], stderr=subprocess.DEVNULL)
                    
                    print(f"\n {Color.GREEN}✓ Puerto {port} SSL detenido{Color.END}")
                    moratech.log_action("admin", f"Puerto {port} SSL detenido")
                else:
                    print(f" {Color.RED}✗ Opción inválida{Color.END}")
            except ValueError:
                print(f" {Color.RED}✗ Opción inválida{Color.END}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

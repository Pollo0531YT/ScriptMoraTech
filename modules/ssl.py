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
    """Instalar SSL con Let's Encrypt (igual a la que funciona)"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INSTALANDO SSL CON LET'S ENCRYPT{Color.END}")
    print_line()
    
    domain = input(f"\n {Color.GREEN}Dominio (ej: vps2.moratech.work): {Color.END}").strip()
    if not domain:
        print(f" {Color.RED}✗ Dominio requerido{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return
    
    port = input(f" {Color.GREEN}Puerto para SSL (default 443): {Color.END}").strip()
    if not port:
        port = "443"
    
    print(f"\n {Color.YELLOW}Instalando SSL con certificado Let's Encrypt...{Color.END}")
    
    try:
        # Detener servicios anteriores
        subprocess.run(['pkill', '-f', 'stunnel4'], stderr=subprocess.DEVNULL)
        subprocess.run(['service', 'stunnel4', 'stop'], stderr=subprocess.DEVNULL)
        
        # Instalar stunnel y certbot
        print(f" {Color.YELLOW}Instalando paquetes...{Color.END}")
        subprocess.run(['apt-get', 'update'], stdout=subprocess.DEVNULL)
        subprocess.run(['apt-get', 'install', '-y', 'stunnel4', 'certbot'], stdout=subprocess.DEVNULL)
        
        # Detener servicios que usen puerto 80
        subprocess.run(['systemctl', 'stop', 'nginx'], stderr=subprocess.DEVNULL)
        subprocess.run(['systemctl', 'stop', 'apache2'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-f', 'pythonwe'], stderr=subprocess.DEVNULL)
        
        import time
        time.sleep(2)
        
        # Obtener certificado
        print(f" {Color.YELLOW}Obteniendo certificado SSL para {domain}...{Color.END}")
        
        result = subprocess.run([
            'certbot', 'certonly', '--standalone', 
            '-d', domain, 
            '--non-interactive', 
            '--agree-tos', 
            '--register-unsafely-without-email'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f" {Color.RED}✗ Error obteniendo certificado{Color.END}")
            print(result.stderr)
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        print(f" {Color.GREEN}✓ Certificado obtenido{Color.END}")
        
        # Combinar certificado y clave
        print(f" {Color.YELLOW}Configurando certificado...{Color.END}")
        cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
        key_path = f"/etc/letsencrypt/live/{domain}/privkey.pem"
        
        subprocess.run([
            'bash', '-c',
            f'cat {cert_path} {key_path} > /etc/stunnel/stunnel.pem'
        ])
        
        subprocess.run(['chmod', '600', '/etc/stunnel/stunnel.pem'])
        
        # Obtener puerto SSH
        ssh_port = '22'
        
        # Configuración stunnel EXACTA como la máquina que funciona
        stunnel_conf = f"""cert = /etc/stunnel/stunnel.pem
client = no
socket = a:SO_REUSEADDR=1
socket = l:TCP_NODELAY=1
socket = r:TCP_NODELAY=1

[ssh-tls]
connect = 127.0.0.1:{ssh_port}
accept = {port}
cert = /etc/stunnel/stunnel.pem
TIMEOUTclose = 0
"""
        
        with open('/etc/stunnel/stunnel.conf', 'w') as f:
            f.write(stunnel_conf)
        
        # Configurar /etc/default/stunnel4
        with open('/etc/default/stunnel4', 'r') as f:
            content = f.read()
        
        if 'FILES="/etc/stunnel/*.conf"' not in content:
            with open('/etc/default/stunnel4', 'a') as f:
                f.write('\nFILES="/etc/stunnel/*.conf"\n')
        
        # Iniciar
        print(f" {Color.YELLOW}Iniciando Stunnel...{Color.END}")
        subprocess.run(['systemctl', 'daemon-reload'])
        subprocess.run(['systemctl', 'restart', 'stunnel4'])
        subprocess.run(['systemctl', 'enable', 'stunnel4'], stderr=subprocess.DEVNULL)
        
        time.sleep(2)
        
        # Verificar
        result = subprocess.run(['systemctl', 'status', 'stunnel4'], capture_output=True, text=True)
        if 'active (running)' in result.stdout:
            print(f" {Color.GREEN}✓ Stunnel iniciado{Color.END}")
        
        # Verificar puerto
        result = subprocess.run(['ss', '-tuln'], capture_output=True, text=True)
        if f':{port}' in result.stdout:
            print(f" {Color.GREEN}✓ Puerto {port} escuchando{Color.END}")
        
        # Abrir puerto
        subprocess.run(['ufw', 'allow', port], stderr=subprocess.DEVNULL)
        subprocess.run(['iptables', '-I', 'INPUT', '-p', 'tcp', '--dport', port, '-j', 'ACCEPT'])
        
        # Forwarding
        print(f" {Color.YELLOW}Configurando forwarding...{Color.END}")
        moratech.configure_forwarding()
        print(f" {Color.GREEN}✓ Forwarding configurado{Color.END}")
        
        # Guardar en config
        with open(PROTOCOLS_FILE, 'r') as f:
            protocols = json.load(f)
        
        protocols['ssl']['enabled'] = True
        protocols['ssl']['port'] = int(port)
        protocols['ssl']['domain'] = domain
        protocols['ssl']['cert_type'] = 'letsencrypt'
        
        with open(PROTOCOLS_FILE, 'w') as f:
            json.dump(protocols, f, indent=4)
        
        print(f"\n {Color.GREEN}✓ SSL Let's Encrypt instalado exitosamente{Color.END}")
        print(f" {Color.CYAN}Dominio: {domain}{Color.END}")
        print(f" {Color.CYAN}Puerto: {port}{Color.END}")
        print(f" {Color.YELLOW}Certificado válido por 90 días{Color.END}")
        moratech.log_action("admin", f"SSL Let's Encrypt: {domain}:{port}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

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

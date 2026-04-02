#!/usr/bin/env python3
"""
Módulo BADVPN - Gestión de BADVPN
"""
import subprocess
import json
import os
from pathlib import Path

from modules.common import Color, PROTOCOLS_FILE, clear_screen, print_banner, print_line
import moratech
from modules import autostart

def menu_badvpn():
    """Menú de BadVPN"""
    while True:
        clear_screen()
        print_banner()
        print_line()
        print(f" {Color.CYAN}BADVPN - UDP GATEWAY{Color.END}")
        print_line()
        
        # Mostrar instancias activas
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            ports_active = []
            
            for line in result.stdout.split('\n'):
                if 'badvpn-udpgw' in line and 'grep' not in line:
                    import re
                    match = re.search(r'127\.0\.0\.1:(\d+)', line)
                    if match:
                        ports_active.append(match.group(1))
            
            if ports_active:
                print(f" {Color.GREEN}Puertos activos: {', '.join(ports_active)}{Color.END}")
            else:
                print(f" {Color.YELLOW}No hay instancias activas{Color.END}")
            
            print_line()
        except:
            pass
        
        print(f" {Color.GREEN}[1]{Color.END} ➮ Instalar/Agregar BadVPN")
        print(f" {Color.GREEN}[2]{Color.END} ➮ Detener BadVPN")
        print_line()
        print(f" {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}Volver{Color.END}")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
        
        if choice == '1':
            install_badvpn()
        elif choice == '2':
            stop_badvpn()
        elif choice == '0':
            break


def install_badvpn():
    """Instalar BadVPN-UDP Gateway"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INSTALANDO BADVPN{Color.END}")
    print_line()
    
    port = input(f"\n {Color.GREEN}Puerto para BadVPN (default 7300): {Color.END}").strip()
    if not port:
        port = "7300"
    
    print(f"\n {Color.YELLOW}Instalando BadVPN en puerto {port}...{Color.END}")
    
    try:
        # Verificar si ya está instalado
        badvpn_installed = subprocess.run(['which', 'badvpn-udpgw'], capture_output=True).returncode == 0
        
        if not badvpn_installed:
            print(f" {Color.YELLOW}Instalando dependencias...{Color.END}")
            subprocess.run(['apt-get', 'update'], stdout=subprocess.DEVNULL)
            subprocess.run(['apt-get', 'install', '-y', 'cmake', 'screen', 'wget', 'gcc', 'build-essential', 'g++', 'make'], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Descargar BadVPN
            print(f" {Color.YELLOW}Descargando BadVPN...{Color.END}")
            subprocess.run(['wget', '-O', '/tmp/badvpn.tar.bz2',
                          'https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/badvpn/badvpn-1.999.128.tar.bz2'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Extraer
            subprocess.run(['tar', 'xf', '/tmp/badvpn.tar.bz2', '-C', '/tmp/'], stderr=subprocess.DEVNULL)
            
            # Compilar
            print(f" {Color.YELLOW}Compilando BadVPN (puede tardar)...{Color.END}")
            subprocess.run(['cmake', '/tmp/badvpn-1.999.128', 
                          '-DBUILD_NOTHING_BY_DEFAULT=1', '-DBUILD_UDPGW=1'],
                         cwd='/tmp/badvpn-1.999.128',
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            subprocess.run(['make', 'install'], 
                         cwd='/tmp/badvpn-1.999.128',
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Limpiar
            subprocess.run(['rm', '-rf', '/tmp/badvpn-1.999.128', '/tmp/badvpn.tar.bz2'], stderr=subprocess.DEVNULL)
            
            print(f" {Color.GREEN}✓ BadVPN compilado e instalado{Color.END}")
        else:
            print(f" {Color.GREEN}✓ BadVPN ya está instalado{Color.END}")
        
        # Verificar si el puerto está en uso
        result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
        if result.stdout.strip():
            print(f" {Color.YELLOW}⚠ Puerto {port} ya está en uso por BadVPN{Color.END}")
            confirm = input(f" {Color.YELLOW}¿Usar este puerto de todas formas? (s/n): {Color.END}").strip().lower()
            if confirm != 's':
                input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                return
        
        # Iniciar BadVPN
        print(f" {Color.YELLOW}Iniciando BadVPN en puerto {port}...{Color.END}")
        
        # Detener instancia anterior del mismo puerto si existe
        subprocess.run(['pkill', '-f', f'badvpn-udpgw.*{port}'], stderr=subprocess.DEVNULL)
        
        # Iniciar en screen
        screen_name = f'badvpn_{port}'
        subprocess.run(['screen', '-dmS', screen_name,
                       'badvpn-udpgw', '--listen-addr', f'127.0.0.1:{port}'],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        import time
        time.sleep(2)
        
        # Verificar que inició
        result = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        if screen_name in result.stdout:
            print(f" {Color.GREEN}✓ BadVPN iniciado en screen ({screen_name}){Color.END}")
        
        # Verificar puerto
        result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
        if f'127.0.0.1:{port}' in result.stdout:
            print(f" {Color.GREEN}✓ Puerto {port} escuchando correctamente{Color.END}")
        
        # Guardar en autostart
        autostart_line = f"screen -dmS {screen_name} badvpn-udpgw --listen-addr 127.0.0.1:{port}"
        
        if not os.path.exists('/etc/autostart'):
            with open('/etc/autostart', 'w') as f:
                f.write('#!/bin/bash\n')
            subprocess.run(['chmod', '+x', '/etc/autostart'])
        
        with open('/etc/autostart', 'r') as f:
            autostart_content = f.read()
        
        if autostart_line not in autostart_content:
            with open('/etc/autostart', 'a') as f:
                f.write(f"\n{autostart_line}\n")
        
        # Guardar en config
        with open(PROTOCOLS_FILE, 'r') as f:
            protocols = json.load(f)

        if 'badvpn' not in protocols:
            protocols['badvpn'] = {'enabled': False, 'ports': []}

        # Asegurar que 'ports' existe
        if 'ports' not in protocols['badvpn']:
            protocols['badvpn']['ports'] = []

        if int(port) not in protocols['badvpn']['ports']:
            protocols['badvpn']['ports'].append(int(port))

        protocols['badvpn']['enabled'] = True

        with open(PROTOCOLS_FILE, 'w') as f:
            json.dump(protocols, f, indent=4)

        print(f"\n {Color.GREEN}✓ BadVPN instalado en puerto {port}{Color.END}")
        print(f" {Color.CYAN}Para llamadas y juegos UDP{Color.END}")
        moratech.log_action("admin", f"BadVPN instalado en puerto {port}")
        autostart.register('badvpn', port=int(port))
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def stop_badvpn():
    """Detener BadVPN"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}DETENER BADVPN{Color.END}")
    print_line()
    
    try:
        # Buscar instancias de BadVPN
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        badvpn_instances = []
        
        for line in result.stdout.split('\n'):
            if 'badvpn-udpgw' in line and 'grep' not in line:
                import re
                match = re.search(r'127\.0\.0\.1:(\d+)', line)
                if match:
                    port = match.group(1)
                    pid = line.split()[1]
                    badvpn_instances.append({'port': port, 'pid': pid})
        
        if not badvpn_instances:
            print(f"\n {Color.YELLOW}No hay instancias de BadVPN activas{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return
        
        print(f"\n {Color.YELLOW}Instancias de BadVPN activas:{Color.END}")
        for i, instance in enumerate(badvpn_instances, 1):
            print(f" {Color.GREEN}[{i}]{Color.END} Puerto {instance['port']} (PID: {instance['pid']})")
        
        print(f"\n {Color.GREEN}[0]{Color.END} Detener TODAS las instancias")
        print(f" {Color.RED}[X]{Color.END} Cancelar")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Selecciona opción: ").strip()
        
        if choice.upper() == 'X':
            return
        
        if choice == '0':
            # Detener todas
            confirm = input(f"\n {Color.YELLOW}¿Detener TODAS las instancias de BadVPN? (s/n): {Color.END}").strip().lower()
            if confirm != 's':
                return
            
            subprocess.run(['pkill', '-f', 'badvpn-udpgw'], stderr=subprocess.DEVNULL)
            
            # Limpiar screens
            result = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'badvpn_' in line:
                    screen_name = line.split('.')[1].split('\t')[0]
                    subprocess.run(['screen', '-S', screen_name, '-X', 'quit'], stderr=subprocess.DEVNULL)
            
            # Limpiar config
            with open(PROTOCOLS_FILE, 'r') as f:
                protocols = json.load(f)
            
            protocols['badvpn']['enabled'] = False
            protocols['badvpn']['ports'] = []
            
            with open(PROTOCOLS_FILE, 'w') as f:
                json.dump(protocols, f, indent=4)
            
            print(f"\n {Color.GREEN}✓ Todas las instancias de BadVPN detenidas{Color.END}")
            moratech.log_action("admin", "Todas las instancias de BadVPN detenidas")
            autostart.unregister('badvpn')
            
        else:
            # Detener instancia específica
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(badvpn_instances):
                    port = badvpn_instances[idx]['port']
                    pid = badvpn_instances[idx]['pid']
                    
                    # Matar proceso
                    subprocess.run(['kill', '-9', pid], stderr=subprocess.DEVNULL)
                    
                    # Detener screen
                    subprocess.run(['screen', '-S', f'badvpn_{port}', '-X', 'quit'], stderr=subprocess.DEVNULL)
                    
                    # Actualizar config
                    with open(PROTOCOLS_FILE, 'r') as f:
                        protocols = json.load(f)
                    
                    if 'badvpn' in protocols and int(port) in protocols['badvpn']['ports']:
                        protocols['badvpn']['ports'].remove(int(port))
                        
                        if not protocols['badvpn']['ports']:
                            protocols['badvpn']['enabled'] = False
                        
                        with open(PROTOCOLS_FILE, 'w') as f:
                            json.dump(protocols, f, indent=4)
                    
                    print(f"\n {Color.GREEN}✓ BadVPN en puerto {port} detenido{Color.END}")
                    moratech.log_action("admin", f"BadVPN puerto {port} detenido")
                    autostart.unregister('badvpn', port=port)
                else:
                    print(f" {Color.RED}✗ Opción inválida{Color.END}")
            except ValueError:
                print(f" {Color.RED}✗ Opción inválida{Color.END}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

#!/usr/bin/env python3
"""
Módulo V2RAY - Gestión del v2ray
"""
import subprocess
import json
from pathlib import Path

from moratech import Color, PROTOCOLS_FILE, log_action, clear_screen, print_banner, print_line


def menu_v2ray():
    """Menú de V2Ray/3X-UI"""
    while True:
        clear_screen()
        print_banner()
        print_line()
        print(f" {Color.CYAN}V2RAY / 3X-UI PANEL{Color.END}")
        print_line()
        
        # Verificar si está instalado
        v2ray_installed = subprocess.run(['which', 'x-ui'], capture_output=True).returncode == 0
        
        if v2ray_installed:
            # Verificar estado del servicio
            result = subprocess.run(['systemctl', 'is-active', 'x-ui'], capture_output=True, text=True)
            if 'active' in result.stdout:
                status = f"{Color.GREEN}ACTIVO ✓{Color.END}"
            else:
                status = f"{Color.YELLOW}INACTIVO{Color.END}"
            
            # Verificar puerto
            result_port = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
            if ':54321' in result_port.stdout:
                port_status = f"{Color.GREEN}54321 ✓{Color.END}"
            else:
                port_status = f"{Color.YELLOW}54321{Color.END}"
            
            print(f" {Color.CYAN}∘{Color.END} Estado: {status}")
            print(f" {Color.CYAN}∘{Color.END} Puerto: {port_status}")
            
            # Mostrar IP de acceso
            try:
                ip = subprocess.check_output(['curl', '-s', 'ifconfig.me'], timeout=3).decode().strip()
                print(f" {Color.CYAN}∘{Color.END} Acceso: {Color.GREEN}http://{ip}:54321{Color.END}")
            except:
                pass
            
            print_line()
            print(f" {Color.GREEN}[1]{Color.END} ➮ Ingresar al menú x-ui")
            print(f" {Color.GREEN}[2]{Color.END} ➮ Reiniciar servicio")
            print(f" {Color.GREEN}[3]{Color.END} ➮ Detener servicio")
            print(f" {Color.GREEN}[4]{Color.END} ➮ Desinstalar 3X-UI")
            
        else:
            print(f" {Color.YELLOW}3X-UI no está instalado{Color.END}")
            print_line()
            print(f" {Color.GREEN}[1]{Color.END} ➮ Instalar 3X-UI")
        
        print_line()
        print(f" {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}Volver{Color.END}")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
        
        if not v2ray_installed:
            # Si NO está instalado
            if choice == '1':
                install_v2ray()
            elif choice == '0':
                break
        else:
            # Si SÍ está instalado
            if choice == '1':
                # Ingresar al menú x-ui
                clear_screen()
                print_banner()
                print_line()
                print(f" {Color.CYAN}Abriendo menú 3X-UI...{Color.END}")
                print_line()
                subprocess.run(['x-ui'])
                input(f"\n {Color.CYAN}Presiona Enter para volver...{Color.END}")
                
            elif choice == '2':
                # Reiniciar
                print(f"\n {Color.YELLOW}Reiniciando 3X-UI...{Color.END}")
                subprocess.run(['x-ui', 'restart'])
                print(f" {Color.GREEN}✓ 3X-UI reiniciado{Color.END}")
                log_action("admin", "3X-UI reiniciado")
                input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                
            elif choice == '3':
                # Detener
                print(f"\n {Color.YELLOW}Deteniendo 3X-UI...{Color.END}")
                subprocess.run(['x-ui', 'stop'])
                print(f" {Color.GREEN}✓ 3X-UI detenido{Color.END}")
                log_action("admin", "3X-UI detenido")
                input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                
            elif choice == '4':
                # Desinstalar
                clear_screen()
                print_banner()
                print_line()
                print(f" {Color.RED}DESINSTALAR 3X-UI{Color.END}")
                print_line()
                
                confirm = input(f"\n {Color.RED}⚠️  ¿Desinstalar completamente 3X-UI? (s/n): {Color.END}").strip().lower()
                if confirm == 's':
                    print(f"\n {Color.YELLOW}Desinstalando 3X-UI...{Color.END}")
                    subprocess.run(['bash', '-c', 'x-ui uninstall'])
                    
                    # Limpiar config
                    try:
                        with open(PROTOCOLS_FILE, 'r') as f:
                            protocols = json.load(f)
                        
                        if 'v2ray' in protocols:
                            protocols['v2ray']['enabled'] = False
                        
                        with open(PROTOCOLS_FILE, 'w') as f:
                            json.dump(protocols, f, indent=4)
                    except:
                        pass
                    
                    print(f"\n {Color.GREEN}✓ 3X-UI desinstalado{Color.END}")
                    log_action("admin", "3X-UI desinstalado")
                else:
                    print(f"\n {Color.YELLOW}Desinstalación cancelada{Color.END}")
                
                input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                
            elif choice == '0':
                break


def install_v2ray():
    """Instalar 3X-UI (V2Ray Panel)"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INSTALANDO 3X-UI (V2RAY PANEL){Color.END}")
    print_line()
    
    print(f"\n {Color.YELLOW}3X-UI es un panel web para gestionar V2Ray/Xray{Color.END}")
    print(f" {Color.YELLOW}Se instalará en el puerto 54321 (por defecto){Color.END}\n")
    
    confirm = input(f" {Color.GREEN}¿Continuar con la instalación? (s/n): {Color.END}").strip().lower()
    if confirm != 's':
        return
    
    try:
        print(f"\n {Color.YELLOW}Descargando e instalando 3X-UI...{Color.END}")
        print(f" {Color.CYAN}Esto puede tardar varios minutos...{Color.END}\n")
        print_line()
        
        # Ejecutar instalación
        result = subprocess.run([
            'bash', '-c',
            'curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh | bash'
        ])
        
        print_line()
        
        if result.returncode == 0:
            print(f"\n {Color.GREEN}✓ 3X-UI instalado correctamente{Color.END}")
            
            # Guardar en config
            try:
                with open(PROTOCOLS_FILE, 'r') as f:
                    protocols = json.load(f)
                
                protocols['v2ray'] = {
                    'enabled': True,
                    'port': 54321,
                    'type': '3x-ui'
                }
                
                with open(PROTOCOLS_FILE, 'w') as f:
                    json.dump(protocols, f, indent=4)
            except:
                pass
            
            print(f"\n {Color.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Color.END}")
            print(f" {Color.YELLOW}Para acceder al panel 3X-UI, ejecuta:{Color.END}")
            print(f" {Color.GREEN}x-ui{Color.END}")
            print(f"\n {Color.YELLOW}O accede vía web:{Color.END}")
            
            # Obtener IP
            try:
                ip = subprocess.check_output(['curl', '-s', 'ifconfig.me']).decode().strip()
                print(f" {Color.GREEN}http://{ip}:54321{Color.END}")
            except:
                print(f" {Color.GREEN}http://TU_IP:54321{Color.END}")
            
            print(f" {Color.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Color.END}")
            
            log_action("admin", "3X-UI instalado")
        else:
            print(f"\n {Color.RED}✗ Error durante la instalación{Color.END}")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

def stop_v2ray():
    """Detener/Desinstalar 3X-UI"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}GESTIONAR 3X-UI{Color.END}")
    print_line()
    
    print(f"\n {Color.YELLOW}Opciones disponibles:{Color.END}")
    print(f" {Color.GREEN}[1]{Color.END} Detener servicio 3X-UI")
    print(f" {Color.GREEN}[2]{Color.END} Reiniciar servicio 3X-UI")
    print(f" {Color.GREEN}[3]{Color.END} Desinstalar 3X-UI")
    print(f" {Color.RED}[0]{Color.END} Volver")
    print_line()
    
    choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
    
    try:
        if choice == '1':
            # Detener
            subprocess.run(['x-ui', 'stop'])
            print(f"\n {Color.GREEN}✓ 3X-UI detenido{Color.END}")
            log_action("admin", "3X-UI detenido")
            
        elif choice == '2':
            # Reiniciar
            subprocess.run(['x-ui', 'restart'])
            print(f"\n {Color.GREEN}✓ 3X-UI reiniciado{Color.END}")
            log_action("admin", "3X-UI reiniciado")
            
        elif choice == '3':
            # Desinstalar
            confirm = input(f"\n {Color.RED}⚠️  ¿Desinstalar completamente 3X-UI? (s/n): {Color.END}").strip().lower()
            if confirm == 's':
                subprocess.run(['bash', '-c', 'x-ui uninstall'])
                
                # Limpiar config
                try:
                    with open(PROTOCOLS_FILE, 'r') as f:
                        protocols = json.load(f)
                    
                    if 'v2ray' in protocols:
                        protocols['v2ray']['enabled'] = False
                    
                    with open(PROTOCOLS_FILE, 'w') as f:
                        json.dump(protocols, f, indent=4)
                except:
                    pass
                
                print(f"\n {Color.GREEN}✓ 3X-UI desinstalado{Color.END}")
                log_action("admin", "3X-UI desinstalado")
        
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
    
    if choice in ['1', '2', '3']:
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")


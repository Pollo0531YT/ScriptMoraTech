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
    """Instalar SSL con Let's Encrypt (mejorada, con streaming y reuso de certificados)."""
    import time
    import shutil
    import socket
    import textwrap
    from subprocess import Popen, PIPE, STDOUT
    from pathlib import Path

    CONFIG_DIR = Path.home() / '.moratech'
    certs_base = Path('/etc/letsencrypt/live')
    stunnel_pem = Path('/etc/stunnel/stunnel.pem')

    def run_cmd_stream(cmd, show_cmd=True, timeout=None):
        """Ejecuta cmd (lista) mostrando salida en tiempo real. Retorna (code, out)."""
        if show_cmd:
            print(f"\n {Color.YELLOW}=> Ejecutando: {' '.join(cmd)}{Color.END}\n")
        try:
            p = Popen(cmd, stdout=PIPE, stderr=STDOUT, text=True)
            out_lines = []
            start = time.time()
            while True:
                line = p.stdout.readline()
                if line:
                    out_lines.append(line.rstrip())
                    print(f" {Color.CYAN}{line.rstrip()}{Color.END}")
                else:
                    if p.poll() is not None:
                        break
                if timeout and (time.time() - start) > timeout:
                    p.kill()
                    raise TimeoutError("Comando excedió timeout")
            return p.returncode, "\n".join(out_lines)
        except Exception as e:
            print(f" {Color.RED}✗ Error ejecutando comando: {e}{Color.END}")
            return 255, str(e)

    def append_stunnel_section(domain, port, ssh_port='22'):
        """Añade sección en /etc/stunnel/stunnel.conf si no existe un accept para ese puerto."""
        conf_path = Path('/etc/stunnel/stunnel.conf')
        conf_path.parent.mkdir(parents=True, exist_ok=True)
        conf_txt = conf_path.read_text() if conf_path.exists() else ""
        # Buscar si ya existe la sección con ese puerto
        if f'accept = {port}' in conf_txt:
            print(f" {Color.YELLOW}Nota: ya existe una entrada accept = {port} en stunnel.conf, no se duplicará.{Color.END}")
            return False

        section = textwrap.dedent(f"""
        [{domain.replace('.', '_')}_{port}]
        cert = /etc/stunnel/stunnel.pem
        accept = {port}
        connect = 127.0.0.1:{ssh_port}
        TIMEOUTclose = 0
        """).strip() + "\n\n"

        # Append manteniendo formato
        with open(conf_path, 'a') as f:
            f.write("\n" + section)
        print(f" {Color.GREEN}✓ Sección añadida a /etc/stunnel/stunnel.conf para puerto {port}{Color.END}")
        return True

    try:
        clear_screen()
        print_banner()
        print_line()
        print(f" {Color.CYAN}INSTALANDO SSL CON LET'S ENCRYPT (MEJORADO){Color.END}")
        print_line()

        domain = input(f"\n {Color.GREEN}Dominio (ej: vps2.moratech.work): {Color.END}").strip()
        if not domain:
            print(f" {Color.RED}✗ Dominio requerido{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return

        port = input(f" {Color.GREEN}Puerto para SSL (default 443): {Color.END}").strip() or "443"
        ssh_port = '22'

        # Opción staging (pruebas)
        use_staging = input(f" {Color.YELLOW}¿Usar staging de Let's Encrypt para pruebas? (s/N): {Color.END}").strip().lower() == 's'

        # Si ya existen certs para el dominio, preguntar si reusar
        cert_dir = certs_base / domain
        cert_exists = cert_dir.exists() and (cert_dir / 'fullchain.pem').exists() and (cert_dir / 'privkey.pem').exists()

        if cert_exists:
            print(f"\n {Color.GREEN}✓ Certificados existentes detectados en {cert_dir}{Color.END}")
            reuse = input(f" {Color.YELLOW}¿Reusar certificado existente y solo añadir puerto {port} al stunnel? (S/n): {Color.END}").strip().lower()
            if reuse == '' or reuse == 's':
                # concatenar fullchain + privkey a /etc/stunnel/stunnel.pem
                run_cmd_stream(['bash', '-c', f'cat "{cert_dir}/fullchain.pem" "{cert_dir}/privkey.pem" > /etc/stunnel/stunnel.pem'], show_cmd=False)
                run_cmd_stream(['chmod', '600', '/etc/stunnel/stunnel.pem'], show_cmd=False)
                appended = append_stunnel_section(domain, port, ssh_port)
                run_cmd_stream(['systemctl', 'daemon-reload'], show_cmd=False)
                run_cmd_stream(['systemctl', 'restart', 'stunnel4'], show_cmd=False)
                # actualizar PROTOCOLS_FILE
                try:
                    with open(PROTOCOLS_FILE, 'r') as f:
                        protocols = json.load(f)
                except Exception:
                    protocols = {}
                protocols.setdefault('ssl', {})
                protocols['ssl']['enabled'] = True
                protocols['ssl']['port'] = int(port)
                protocols['ssl']['domain'] = domain
                protocols['ssl']['cert_type'] = 'letsencrypt-reuse'
                with open(PROTOCOLS_FILE, 'w') as f:
                    json.dump(protocols, f, indent=4)
                moratech.log_action("admin", f"SSL reutilizado: {domain}:{port}")
                print(f"\n {Color.GREEN}✓ Se añadió/activó SSL para {domain}:{port} usando certificado existente{Color.END}")
                input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                return
            else:
                print(f" {Color.YELLOW}Se intentará obtener certificado nuevo (si aplica).{Color.END}")

        # Detener servicios que puedan bloquear puerto 80/443 (para standalone)
        print(f"\n {Color.YELLOW}Preparando entorno: deteniendo temporariamente nginx/apache si están activos...{Color.END}")
        run_cmd_stream(['systemctl', 'stop', 'nginx'], show_cmd=False)
        run_cmd_stream(['systemctl', 'stop', 'apache2'], show_cmd=False)
        # Intentar matar procesos python que ocupen puertos (a veces checks)
        run_cmd_stream(['pkill', '-f', 'pythonwe'], show_cmd=False)

        # Instalar paquetes si no existen
        print(f"\n {Color.YELLOW}Instalando paquetes requeridos (stunnel4, certbot si falta)...{Color.END}")
        run_cmd_stream(['apt-get', 'update'], show_cmd=False)
        code, _ = run_cmd_stream(['apt-get', 'install', '-y', 'stunnel4', 'certbot'], show_cmd=False, timeout=600)
        if code != 0:
            print(f" {Color.RED}✗ apt-get falló. Revisa la salida arriba.{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return

        # Ejecutar certbot --standalone
        print(f"\n {Color.YELLOW}Obteniendo certificado SSL para {domain} (modo standalone)...{Color.END}")
        certbot_cmd = ['certbot', 'certonly', '--standalone', '-d', domain, '--non-interactive', '--agree-tos', '--register-unsafely-without-email']
        if use_staging:
            certbot_cmd.insert(-1, '--staging')  # agrega antes de último
        code, out = run_cmd_stream(certbot_cmd, timeout=420)  # 7 min timeout
        if code != 0:
            print(f"\n {Color.RED}✗ certbot devolvió código {code}. Revisa salida arriba.{Color.END}")
            # mostrar log resumido
            run_cmd_stream(['tail', '-n', '80', '/var/log/letsencrypt/letsencrypt.log'], show_cmd=False)
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return

        # Combinar fullchain + privkey en /etc/stunnel/stunnel.pem
        print(f"\n {Color.YELLOW}Configurando /etc/stunnel/stunnel.pem...{Color.END}")
        run_cmd_stream(['bash', '-c', f'cat "{cert_dir}/fullchain.pem" "{cert_dir}/privkey.pem" > /etc/stunnel/stunnel.pem'], show_cmd=False)
        run_cmd_stream(['chmod', '600', '/etc/stunnel/stunnel.pem'], show_cmd=False)

        # Añadir sección en stunnel.conf (si aún no existe)
        append_stunnel_section(domain, port, ssh_port)

        # Asegurar que /etc/default/stunnel4 contenga FILES var (compatibilidad)
        default_path = Path('/etc/default/stunnel4')
        if default_path.exists():
            content = default_path.read_text()
            if 'FILES="/etc/stunnel/*.conf"' not in content:
                with open(default_path, 'a') as f:
                    f.write('\nFILES="/etc/stunnel/*.conf"\n')

        # Reiniciar y comprobar stunnel
        print(f"\n {Color.YELLOW}Reiniciando stunnel4...{Color.END}")
        run_cmd_stream(['systemctl', 'daemon-reload'], show_cmd=False)
        run_cmd_stream(['systemctl', 'restart', 'stunnel4'], show_cmd=False)
        time.sleep(2)
        rc, st = run_cmd_stream(['systemctl', 'status', 'stunnel4'], show_cmd=False)
        if 'active (running)' in st:
            print(f"\n {Color.GREEN}✓ Stunnel activo{Color.END}")
        else:
            print(f"\n {Color.RED}✗ stunnel parece no estar activo. Revisa logs arriba.{Color.END}")

        # Abrir puerto en firewall y reglas iptables
        print(f"\n {Color.YELLOW}Abriendo puerto {port} en firewall y iptables...{Color.END}")
        run_cmd_stream(['ufw', 'allow', port], show_cmd=False)
        run_cmd_stream(['iptables', '-I', 'INPUT', '-p', 'tcp', '--dport', str(port), '-j', 'ACCEPT'], show_cmd=False)

        # Guardar en PROTOCOLS_FILE
        try:
            with open(PROTOCOLS_FILE, 'r') as f:
                protocols = json.load(f)
        except Exception:
            protocols = {}
        protocols.setdefault('ssl', {})
        protocols['ssl']['enabled'] = True
        protocols['ssl']['port'] = int(port)
        protocols['ssl']['domain'] = domain
        protocols['ssl']['cert_type'] = 'letsencrypt' if not use_staging else 'letsencrypt-staging'
        with open(PROTOCOLS_FILE, 'w') as f:
            json.dump(protocols, f, indent=4)

        moratech.log_action("admin", f"SSL Let's Encrypt: {domain}:{port}")
        print(f"\n {Color.GREEN}✓ SSL Let's Encrypt instalado y stunnel configurado para {domain}:{port}{Color.END}")
        print(f" {Color.YELLOW}Certificados válidos en: /etc/letsencrypt/live/{domain}{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

    except Exception as e:
        print(f"\n {Color.RED}✗ Error crítico en install_ssl: {e}{Color.END}")
        import traceback
        traceback.print_exc()
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return


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

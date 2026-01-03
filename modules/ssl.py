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
    """Instalar o reutilizar certificado Let's Encrypt y añadir un puerto a stunnel (interfaz simplificada)."""
    import time
    from pathlib import Path
    import shlex

    def stream_cmd(cmd, header=None):
        """Ejecuta un comando y muestra su salida en tiempo real (retorna código)."""
        if header:
            print(f"\n {Color.YELLOW}{header}{Color.END}")
        print(f"  ➜ Ejecutando: {' '.join(cmd)}\n")
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            for line in p.stdout:
                print("   " + line.rstrip())
        except Exception:
            pass
        p.wait()
        return p.returncode

    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INSTALANDO SSL CON LET'S ENCRYPT (MEJORADO){Color.END}")
    print_line()

    # 1) Detectar certificado existente:
    domain = None
    cert_dir = None
    try:
        # Leer PROTOCOLS_FILE si existe
        if Path(PROTOCOLS_FILE).exists():
            with open(PROTOCOLS_FILE, 'r') as f:
                protocols = json.load(f)
            ssl_info = protocols.get('ssl', {})
            d = ssl_info.get('domain')
            if d and Path(f"/etc/letsencrypt/live/{d}").exists():
                domain = d
                cert_dir = Path(f"/etc/letsencrypt/live/{d}")
    except Exception:
        domain = None

    # Si no hay domain según PROTOCOLS_FILE, buscar en /etc/letsencrypt/live cualquier certificado
    if not domain:
        try:
            live_path = Path("/etc/letsencrypt/live")
            if live_path.exists():
                candidates = [p for p in live_path.iterdir() if p.is_dir()]
                if candidates:
                    # elegir el primero disponible (esto significa que ya tenés al menos un cert)
                    cert_dir = candidates[0]
                    domain = cert_dir.name
        except Exception:
            domain = None

    # Si ya hay certificado, NO pedir dominio: pedir solo puerto y reutilizar
    reuse_cert = False
    if domain:
        reuse_cert = True
        print(f"\n {Color.GREEN}✓ Certificado detectado: {domain}{Color.END}")
        print(f" {Color.CYAN}Se reutilizará este certificado y solo se solicitará el puerto a agregar.{Color.END}\n")

    # Si no hay certificado, pedir dominio (flujo completo)
    if not reuse_cert:
        domain = input(f"\n {Color.GREEN}Dominio (ej: vps2.moratech.work): {Color.END}").strip()
        if not domain:
            print(f"\n {Color.RED}✗ Dominio requerido, operación cancelada.{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return

    # Pedir puerto (si estamos agregando, no pedimos dominio)
    port = input(f" {Color.GREEN}Puerto para SSL (default 443): {Color.END}").strip()
    if not port:
        port = "443"

    # Si no existía cert, pedir staging op (para pruebas)
    staging = False
    if not reuse_cert:
        s = input(f" {Color.GREEN}¿Usar staging de Let's Encrypt para pruebas? (s/N): {Color.END}").strip().lower()
        staging = (s == 's')

    # Si no hay cert y debemos crearlo: instalar dependencias y ejecutar certbot (streamed)
    if not reuse_cert:
        print(f"\n {Color.YELLOW}Preparando entorno y verificando paquetes requeridos...{Color.END}")
        # apt-get update/install (silencioso pero con streaming)
        stream_cmd(['apt-get', 'update'], header="Actualizando índices de paquetes...")
        stream_cmd(['apt-get', 'install', '-y', 'stunnel4', 'certbot'], header="Instalando stunnel4 & certbot (si falta)...")

        # asegurarnos puertos libres: detiene servicios web temporales si están corriendo
        print(f"\n {Color.YELLOW}Parando nginx/apache temporalmente si existen...{Color.END}")
        subprocess.run(['systemctl', 'stop', 'nginx'], stderr=subprocess.DEVNULL)
        subprocess.run(['systemctl', 'stop', 'apache2'], stderr=subprocess.DEVNULL)

        # Ejecutar certbot en modo standalone y mostrar salida en tiempo real
        cmd = ['certbot', 'certonly', '--standalone', '-d', domain, '--non-interactive', '--agree-tos', '--register-unsafely-without-email']
        if staging:
            cmd.insert(-2, '--staging')  # añade --staging antes de --non-interactive por legibilidad
        rc = stream_cmd(cmd, header=f"Obteniendo certificado SSL para {domain} (standalone)...")
        if rc != 0:
            print(f"\n {Color.RED}✗ certbot devolvió código {rc}. Revisa /var/log/letsencrypt/letsencrypt.log{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return

        cert_dir = Path(f"/etc/letsencrypt/live/{domain}")
        if not cert_dir.exists():
            print(f"\n {Color.RED}✗ Certificado no encontrado después de certbot. Abortando.{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return

        print(f"\n {Color.GREEN}✓ Certificado obtenido y guardado en: {cert_dir}{Color.END}")

    # --------------- ahora reutilizar/usar certificado para añadir puerto en stunnel ---------------
    try:
        stunnel_conf_path = Path("/etc/stunnel/stunnel.conf")
        pem_dest = Path("/etc/stunnel/stunnel.pem")

        # concatenar fullchain + privkey en stunnel.pem (si no existe o si pertenece a este domain)
        if cert_dir:
            fullchain = cert_dir / "fullchain.pem"
            privkey = cert_dir / "privkey.pem"
            if fullchain.exists() and privkey.exists():
                subprocess.run(['bash', '-c', f'cat "{fullchain}" "{privkey}" > "{pem_dest}"'])
                subprocess.run(['chmod', '600', str(pem_dest)])
                print(f"\n {Color.GREEN}✓ Configurando {pem_dest} con certificado {domain}{Color.END}")
            else:
                print(f"\n {Color.YELLOW}! Atención: faltan fullchain/privkey en {cert_dir}. Se intentará añadir la sección pero verifica el .pem manualmente.{Color.END}")

        # Crear entrada stunnel para el puerto solicitado
        # generar un nombre de sección único basado en domain y puerto
        section_name = f"{domain.replace('.', '_')}_{port}"
        new_section = (
            f"\n[{section_name}]\n"
            f"accept = {port}\n"
            f"connect = 127.0.0.1:22\n"
            f"cert = /etc/stunnel/stunnel.pem\n"
            f"TIMEOUTclose = 0\n"
        )

        # Añadir sección si no existe accept = port ya presente
        conf_text = ""
        if stunnel_conf_path.exists():
            conf_text = stunnel_conf_path.read_text()
        if f"accept = {port}" in conf_text:
            print(f"\n {Color.YELLOW}ℹ El puerto {port} ya está configurado en stunnel.conf (skip).{Color.END}")
        else:
            with open(stunnel_conf_path, 'a') as f:
                f.write(new_section)
            print(f"\n {Color.GREEN}✓ Sección añadida a {stunnel_conf_path} para puerto {port}{Color.END}")

        # Reiniciar stunnel (mostramos estado resumido)
        print(f"\n {Color.YELLOW}Reiniciando stunnel4...{Color.END}")
        subprocess.run(['systemctl', 'daemon-reload'], stderr=subprocess.DEVNULL)
        subprocess.run(['systemctl', 'restart', 'stunnel4'], stderr=subprocess.DEVNULL)

        # Comprobar si está activo
        st = subprocess.run(['systemctl', 'is-active', 'stunnel4'], capture_output=True, text=True)
        if st.returncode == 0:
            print(f" {Color.GREEN}✓ Stunnel activo{Color.END}")
        else:
            print(f" {Color.RED}✗ Stunnel parece no estar activo (revisa logs){Color.END}")

        # Abrir firewall / iptables
        subprocess.run(['ufw', 'allow', port], stderr=subprocess.DEVNULL)
        subprocess.run(['iptables', '-C', 'INPUT', '-p', 'tcp', '--dport', port, '-j', 'ACCEPT'], stderr=subprocess.DEVNULL)
        # si la regla no existía, la añadimos (evitamos duplicados)
        subprocess.run(['iptables', '-I', 'INPUT', '-p', 'tcp', '--dport', port, '-j', 'ACCEPT'], stderr=subprocess.DEVNULL)

        # Configurar forwarding (tu función existente)
        try:
            moratech.configure_forwarding()
            print(f"\n {Color.GREEN}✓ Forwarding configurado{Color.END}")
        except Exception:
            print(f"\n {Color.YELLOW}! Forwarding: no se pudo ejecutar moratech.configure_forwarding() automáticamente.{Color.END}")

        # Guardar en PROTOCOLS_FILE (actualizar info ssl)
        try:
            protocols = {}
            if Path(PROTOCOLS_FILE).exists():
                with open(PROTOCOLS_FILE, 'r') as f:
                    protocols = json.load(f)
            if 'ssl' not in protocols:
                protocols['ssl'] = {}
            protocols['ssl']['enabled'] = True
            protocols['ssl']['port'] = int(port)
            protocols['ssl']['domain'] = domain
            protocols['ssl']['cert_type'] = 'letsencrypt'
            with open(PROTOCOLS_FILE, 'w') as f:
                json.dump(protocols, f, indent=4)
        except Exception:
            pass

        print(f"\n {Color.GREEN}✓ SSL instalado/activado: {domain}:{port}{Color.END}")
        print(f" {Color.CYAN}Certificados válidos en: /etc/letsencrypt/live/{domain}{Color.END}")

    except Exception as e:
        print(f"\n {Color.RED}✗ Error configurando stunnel: {e}{Color.END}")
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

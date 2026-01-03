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
    """Menu de ssl - banner bonito y opciones según estado detectado."""
    import re
    from pathlib import Path

    STUNNEL_CONF = Path("/etc/stunnel/stunnel.conf")

    while True:
        clear_screen()

        # Banner ASCII (mejorado, compacto)
        print("+-------------------------------------------------+")
        print("|                                                 |")
        print("|   ____ ____  _          __  _____ _     ____    |")
        print("|  / ___/ ___|| |        / / |_   _| |   / ___|   |")
        print("|  \___ \___ \| |       / /    | | | |   \___ \   |")
        print("|   ___) |__) | |___   / /     | | | |___ ___) |  |")
        print("|  |____/____/|_____| /_/      |_| |_____|____/   |")
        print("|                                                 |")
        print("|                                                 |")
        print("+-------------------------------------------------+")
        print_line()

        # Título e info
        print(" Certificado SSL/TLS (MoraTech)")
        print(" Certificado: Let's Encrypt")
        print_line()

        # Detectar estado
        try:
            # Preferir leer el stunnel.conf si existe (detecta accept = <port>)
            ssl_ports = []
            if STUNNEL_CONF.exists():
                txt = STUNNEL_CONF.read_text(errors='ignore')
                import re
                ssl_ports = re.findall(r'accept\s*=\s*(\d+)', txt)
                ssl_ports = sorted(list(set(ssl_ports)), key=lambda x: int(x))
            else:
                # fallback: buscar procesos en ss
                res = subprocess.run(['ss', '-tulpn'], capture_output=True, text=True)
                for line in res.stdout.splitlines():
                    if 'stunnel' in line:
                        m = re.search(r':(\d+)\s', line)
                        if m:
                            ssl_ports.append(m.group(1))
                ssl_ports = sorted(list(set(ssl_ports)), key=lambda x: int(x))

            if ssl_ports:
                ports_str = ", ".join(ssl_ports)
                ssl_status = f"{Color.GREEN}ACTIVO - Puerto(s) {ports_str}{Color.END}"
            else:
                ssl_status = f"{Color.YELLOW}INACTIVO{Color.END}"

            print(f" {Color.CYAN}∘{Color.END} CONFIGURACION SSL: {ssl_status}")
            print_line()
        except Exception:
            print(f" {Color.YELLOW}∘{Color.END} CONFIGURACION SSL: {Color.YELLOW}ERROR DETECTANDO ESTADO{Color.END}")
            print_line()

        # Opciones (más claras)
        print(f"{Color.GREEN}1.{Color.END} ADICIONAR PUERTO SSL")
        print(f"{Color.GREEN}2.{Color.END} DETENER SSL (limpieza completa)")
        print(f"{Color.GREEN}3.{Color.END} ELIMINAR PUERTO SSL (específico)")
        print(f"{Color.GREEN}0.{Color.END} Volver")
        print_line()

        choice = input(f"\n{Color.YELLOW}Selecciona: {Color.END}").strip()
        if choice == '1':
            # Usamos tu install_ssl() existente; si quieres que detecte certs automáticamente,
            # habría que ajustar install_ssl para recibir solo 'port' cuando ya hay certificado.
            install_ssl()
        elif choice == '2':
            stop_ssl()    # limpieza completa
        elif choice == '3':
            # llamamos a stop_ssl() con modo puerto específico mediante un helper
            _stop_specific_port_interactive()
        elif choice == '0':
            break
        else:
            print(f"\n{Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")

# Helper para eliminar un puerto específico interactivo (re-usable)
def _stop_specific_port_interactive():
    """Interfaz sencilla para eliminar un puerto stunnel específico."""
    import re
    from pathlib import Path
    stunnel_conf = Path("/etc/stunnel/stunnel.conf")

    # Detectar puertos
    ssl_ports = []
    if stunnel_conf.exists():
        txt = stunnel_conf.read_text(errors='ignore')
        ssl_ports = re.findall(r'accept\s*=\s*(\d+)', txt)
        ssl_ports = sorted(list(set(ssl_ports)), key=lambda x: int(x))

    if not ssl_ports:
        print(f"\n {Color.YELLOW}No se detectaron puertos SSL en stunnel.conf{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return

    print(f"\n {Color.YELLOW}Puertos SSL detectados:{Color.END}")
    for i, p in enumerate(ssl_ports, 1):
        print(f" {Color.GREEN}[{i}]{Color.END} Puerto {p}")
    print(f" {Color.RED}[X]{Color.END} Cancelar")
    choice = input(f"\n {Color.CYAN}Seleccione puerto a eliminar: {Color.END}").strip()
    if choice.upper() == 'X':
        return
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(ssl_ports):
            port = ssl_ports[idx]
            # Reusar la lógica de stop_ssl para puerto (sin backup)
            _stop_ssl_port(port)
        else:
            print(f"\n {Color.RED}Opción inválida{Color.END}")
    except ValueError:
        print(f"\n {Color.RED}Opción inválida{Color.END}")
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")


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

# Helper para eliminar un puerto específico interactivo (re-usable)
def _stop_specific_port_interactive():
    """Interfaz sencilla para eliminar un puerto stunnel específico."""
    import re
    from pathlib import Path
    stunnel_conf = Path("/etc/stunnel/stunnel.conf")

    # Detectar puertos
    ssl_ports = []
    if stunnel_conf.exists():
        txt = stunnel_conf.read_text(errors='ignore')
        ssl_ports = re.findall(r'accept\s*=\s*(\d+)', txt)
        ssl_ports = sorted(list(set(ssl_ports)), key=lambda x: int(x))

    if not ssl_ports:
        print(f"\n {Color.YELLOW}No se detectaron puertos SSL en stunnel.conf{Color.END}")
        input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        return

    print(f"\n {Color.YELLOW}Puertos SSL detectados:{Color.END}")
    for i, p in enumerate(ssl_ports, 1):
        print(f" {Color.GREEN}[{i}]{Color.END} Puerto {p}")
    print(f" {Color.RED}[X]{Color.END} Cancelar")
    choice = input(f"\n {Color.CYAN}Seleccione puerto a eliminar: {Color.END}").strip()
    if choice.upper() == 'X':
        return
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(ssl_ports):
            port = ssl_ports[idx]
            # Reusar la lógica de stop_ssl para puerto (sin backup)
            _stop_ssl_port(port)
        else:
            print(f"\n {Color.RED}Opción inválida{Color.END}")
    except ValueError:
        print(f"\n {Color.RED}Opción inválida{Color.END}")
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

# Lógica que elimina un puerto de stunnel.conf y limpia reglas (llamada desde helper y stop_ssl)
def _stop_ssl_port(port: str):
    """Eliminar sección con accept = <port> y limpiar reglas (sin backups)."""
    import re
    from pathlib import Path
    stunnel_conf = Path("/etc/stunnel/stunnel.conf")

    if not stunnel_conf.exists():
        print(f"\n {Color.YELLOW}stunnel.conf no existe{Color.END}")
        return

    try:
        lines = stunnel_conf.read_text(errors='ignore').splitlines()
        new_lines = []
        skip = False
        for ln in lines:
            if ln.strip().startswith('['):
                skip = False
            if f'accept = {port}' in ln:
                skip = True
                continue
            if not skip:
                new_lines.append(ln)

        # Guardar nuevo conf (sin backup por pedido)
        with open(stunnel_conf, 'w') as f:
            f.write("\n".join(new_lines) + ("\n" if new_lines else ""))

        # Reiniciar stunnel
        subprocess.run(['systemctl', 'daemon-reload'], stderr=subprocess.DEVNULL)
        subprocess.run(['systemctl', 'restart', 'stunnel4'], stderr=subprocess.DEVNULL)

        # Firewall limpieza
        subprocess.run(['iptables', '-D', 'INPUT', '-p', 'tcp', '--dport', port, '-j', 'ACCEPT'], stderr=subprocess.DEVNULL)
        subprocess.run(['ip6tables', '-D', 'INPUT', '-p', 'tcp', '--dport', port, '-j', 'ACCEPT'], stderr=subprocess.DEVNULL)
        try:
            subprocess.run(['ufw', 'delete', 'allow', port], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        print(f"\n {Color.GREEN}✓ Puerto {port} eliminado y reglas firewall removidas{Color.END}")
        moratech.log_action("admin", f"Puerto SSL eliminado: {port}")
    except Exception as e:
        print(f"\n {Color.RED}✗ Error al eliminar puerto {port}: {e}{Color.END}")
        import traceback
        traceback.print_exc()

def stop_ssl():
    """Detener SSL/Stunnel - LIMPIEZA COMPLETA (sin backups)."""
    import re
    import shutil
    from pathlib import Path

    stunnel_conf = Path("/etc/stunnel/stunnel.conf")
    stunnel_pem = Path("/etc/stunnel/stunnel.pem")
    protocols_path = Path(PROTOCOLS_FILE)

    clear_screen()
    print_line()
    print(f" {Color.CYAN}DETENER SSL/STUNNEL (LIMPIEZA COMPLETA){Color.END}")
    print_line()

    try:
        # Detectar puertos (desde conf o procesos)
        ssl_ports = []
        if stunnel_conf.exists():
            txt = stunnel_conf.read_text(errors='ignore')
            ssl_ports = re.findall(r'accept\s*=\s*(\d+)', txt)
            ssl_ports = sorted(list(set(ssl_ports)), key=lambda x: int(x))
        else:
            res = subprocess.run(['ss', '-tulpn'], capture_output=True, text=True)
            for line in res.stdout.splitlines():
                if 'stunnel' in line:
                    m = re.search(r':(\d+)\s', line)
                    if m:
                        ssl_ports.append(m.group(1))
            ssl_ports = sorted(list(set(ssl_ports)), key=lambda x: int(x))

        if not ssl_ports:
            # preguntar si forzar limpieza completa
            confirm_force = input(f"\n {Color.YELLOW}No se detectaron puertos stunnel. ¿Forzar limpieza completa? (s/N): {Color.END}").strip().lower()
            if confirm_force != 's':
                input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                return

        # 1) Parar procesos y servicio
        subprocess.run(['pkill', '-f', 'stunnel4'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-f', 'stunnel'], stderr=subprocess.DEVNULL)
        subprocess.run(['systemctl', 'stop', 'stunnel4'], stderr=subprocess.DEVNULL)
        subprocess.run(['systemctl', 'disable', 'stunnel4'], stderr=subprocess.DEVNULL)

        # 2) Eliminar stunnel.conf y stunnel.pem (sin backups)
        try:
            if stunnel_conf.exists():
                stunnel_conf.unlink()
                print(f"  - {Color.GREEN}stunnel.conf eliminado{Color.END}")
        except Exception as e:
            print(f"  - {Color.RED}No se pudo eliminar stunnel.conf: {e}{Color.END}")

        try:
            if stunnel_pem.exists():
                stunnel_pem.unlink()
                print(f"  - {Color.GREEN}stunnel.pem eliminado{Color.END}")
        except Exception as e:
            print(f"  - {Color.RED}No se pudo eliminar stunnel.pem: {e}{Color.END}")

        # 3) Limpiar reglas firewall para todos los puertos detectados (y algunos comunes)
        common_ports = ssl_ports + ['443', '8443', '444']  # agregar puertos comunes por si acaso
        for port in sorted(set(common_ports), key=lambda x: int(x) if str(x).isdigit() else x):
            try:
                subprocess.run(['iptables', '-D', 'INPUT', '-p', 'tcp', '--dport', str(port), '-j', 'ACCEPT'], stderr=subprocess.DEVNULL)
            except Exception:
                pass
            try:
                subprocess.run(['ip6tables', '-D', 'INPUT', '-p', 'tcp', '--dport', str(port), '-j', 'ACCEPT'], stderr=subprocess.DEVNULL)
            except Exception:
                pass
            try:
                subprocess.run(['ufw', 'delete', 'allow', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        # 4) Intentar eliminar certificados Let's Encrypt si existe dominio en PROTOCOLS_FILE
        try:
            if protocols_path.exists():
                with open(protocols_path, 'r') as f:
                    protocols = json.load(f)
                ssl_info = protocols.get('ssl', {})
                domain = ssl_info.get('domain')
                if domain:
                    # intentar certbot delete
                    if shutil.which('certbot'):
                        try:
                            subprocess.run(['certbot', 'delete', '--cert-name', domain, '--non-interactive', '--quiet'], check=False)
                        except Exception:
                            pass
                    # eliminar directories manualmente si quedaran
                    for p in (f"/etc/letsencrypt/live/{domain}", f"/etc/letsencrypt/archive/{domain}", f"/etc/letsencrypt/renewal/{domain}.conf"):
                        try:
                            if Path(p).exists():
                                if Path(p).is_file():
                                    Path(p).unlink()
                                else:
                                    shutil.rmtree(Path(p))
                        except Exception:
                            pass
                # desactivar ssl en protocols.json
                try:
                    protocols['ssl'] = {'enabled': False}
                    with open(protocols_path, 'w') as f:
                        json.dump(protocols, f, indent=4)
                except Exception:
                    pass
        except Exception:
            pass

        # 5) reload daemon y asegurar stunnel fuera
        subprocess.run(['systemctl', 'daemon-reload'], stderr=subprocess.DEVNULL)
        subprocess.run(['systemctl', 'stop', 'stunnel4'], stderr=subprocess.DEVNULL)
        subprocess.run(['systemctl', 'disable', 'stunnel4'], stderr=subprocess.DEVNULL)

        # 6) Mensaje final
        print(f"\n {Color.GREEN}✓ Limpieza completa de SSL / stunnel ejecutada (sin backups).{Color.END}")
        moratech.log_action("admin", "stop_ssl: limpieza completa ejecutada (sin backups)")

    except Exception as e:
        print(f"\n {Color.RED}✗ Error durante limpieza: {e}{Color.END}")
        import traceback
        traceback.print_exc()

    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

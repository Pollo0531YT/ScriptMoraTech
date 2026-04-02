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


def _rebuild_pem_from_letsencrypt(domain):
    """Reconstruir stunnel.pem desde certs Let's Encrypt existentes sin correr certbot."""
    from pathlib import Path
    cert_path = Path(f"/etc/letsencrypt/live/{domain}/fullchain.pem")
    key_path  = Path(f"/etc/letsencrypt/live/{domain}/privkey.pem")
    if cert_path.exists() and key_path.exists():
        subprocess.run(
            ['bash', '-c', f'cat {cert_path} {key_path} > /etc/stunnel/stunnel.pem'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        subprocess.run(['chmod', '600', '/etc/stunnel/stunnel.pem'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    return False

def _find_letsencrypt_domain():
    """Buscar el primer dominio con certs válidos en /etc/letsencrypt/live/."""
    from pathlib import Path
    live = Path('/etc/letsencrypt/live')
    if live.exists():
        for d in live.iterdir():
            if d.is_dir() and (d / 'fullchain.pem').exists() and (d / 'privkey.pem').exists():
                return d.name
    return None

def install_ssl():
    """
    Instalar/agregar puerto SSL via stunnel4.
    - Reutiliza stunnel.pem si existe.
    - Si no existe pero hay certs Let's Encrypt, los reutiliza sin correr certbot.
    - Solo pide dominio y corre certbot si no hay ningún certificado previo.
    """
    import time
    from pathlib import Path

    STUNNEL_CONF = Path("/etc/stunnel/stunnel.conf")
    STUNNEL_PEM  = Path("/etc/stunnel/stunnel.pem")
    STUNNEL_DEFAULT = Path("/etc/default/stunnel4")
    PROTOCOLS    = Path(PROTOCOLS_FILE)

    clear_screen()
    print_line()
    print(f" {Color.CYAN}CONFIGURAR PUERTO SSL{Color.END}")
    print_line()

    # ── 1. Resolver certificado ─────────────────────────────────────────────
    domain = None
    cert_exists = STUNNEL_PEM.exists()

    if cert_exists:
        print(f" {Color.GREEN}✓ Certificado stunnel.pem detectado — se reutilizará{Color.END}")
    else:
        # Intentar reconstruir desde Let's Encrypt sin certbot
        le_domain = _find_letsencrypt_domain()
        if le_domain:
            print(f" {Color.YELLOW}Certificado Let's Encrypt encontrado ({le_domain}) — reconstruyendo stunnel.pem...{Color.END}", end='', flush=True)
            if _rebuild_pem_from_letsencrypt(le_domain):
                cert_exists = True
                domain = le_domain
                print(f" {Color.GREEN}✓{Color.END}")
            else:
                print(f" {Color.RED}✗{Color.END}")

        # Buscar dominio en protocols.json si no encontramos LE
        if not cert_exists:
            try:
                if PROTOCOLS.exists():
                    with open(PROTOCOLS, 'r') as f:
                        prot = json.load(f)
                    saved_domain = prot.get('ssl', {}).get('domain')
                    if saved_domain:
                        le_domain = saved_domain
                        print(f" {Color.YELLOW}Intentando reconstruir con dominio guardado ({saved_domain})...{Color.END}", end='', flush=True)
                        if _rebuild_pem_from_letsencrypt(saved_domain):
                            cert_exists = True
                            domain = saved_domain
                            print(f" {Color.GREEN}✓{Color.END}")
                        else:
                            print(f" {Color.RED}✗{Color.END}")
            except Exception:
                pass

        if not cert_exists:
            print(f"\n {Color.YELLOW}No se encontró certificado previo. Se obtendrá uno nuevo.{Color.END}")
            domain = input(f" {Color.GREEN}Dominio (ej: vps.moratech.work): {Color.END}").strip()
            if not domain:
                print(f"\n {Color.RED}✗ Dominio requerido.{Color.END}")
                input("\n Presiona Enter...")
                return

    port = input(f" {Color.GREEN}Puerto para SSL (default 443): {Color.END}").strip() or "443"

    print(f"\n {Color.YELLOW}Configurando...{Color.END}")
    try:
        # ── 2. Instalar paquetes si faltan ──────────────────────────────────
        subprocess.run(['apt-get', 'install', '-y', 'stunnel4'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # ── 3. Obtener cert con certbot si todavía no hay uno ───────────────
        if not cert_exists:
            subprocess.run(['apt-get', 'install', '-y', 'certbot'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['systemctl', 'stop', 'nginx'],  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['systemctl', 'stop', 'apache2'],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.3)

            r = subprocess.run(
                ['certbot', 'certonly', '--standalone', '-d', domain,
                 '--non-interactive', '--agree-tos', '--register-unsafely-without-email'],
                capture_output=True, text=True
            )
            if r.returncode != 0:
                err = (r.stderr or r.stdout or "error desconocido").strip().splitlines()[-1]
                print(f" {Color.RED}✗ Error obteniendo certificado: {err}{Color.END}")
                input("\n Presiona Enter...")
                return

            if not _rebuild_pem_from_letsencrypt(domain):
                print(f" {Color.RED}✗ Certificado no encontrado después de certbot.{Color.END}")
                input("\n Presiona Enter...")
                return

        # ── 4. Escribir sección en stunnel.conf (sin duplicar) ──────────────
        st_conf_text = STUNNEL_CONF.read_text(errors='ignore') if STUNNEL_CONF.exists() else ""

        # Cabecera global si el conf está vacío o no tiene 'cert =' global
        global_header = (
            "cert = /etc/stunnel/stunnel.pem\n"
            "client = no\n"
            "socket = a:SO_REUSEADDR=1\n"
            "socket = l:TCP_NODELAY=1\n"
            "socket = r:TCP_NODELAY=1\n"
        )
        if not st_conf_text.strip():
            st_conf_text = global_header

        if f"accept = {port}" not in st_conf_text:
            label   = f"mora_{port}"
            section = (f"\n[{label}]\n"
                       f"connect = 127.0.0.1:22\n"
                       f"accept = {port}\n"
                       f"cert = /etc/stunnel/stunnel.pem\n"
                       f"TIMEOUTclose = 0\n")
            new_conf = st_conf_text.rstrip() + "\n" + section
            with open(STUNNEL_CONF, 'w') as f:
                f.write(new_conf)

        # ── 5. Activar stunnel4 correctamente ───────────────────────────────
        # En Ubuntu/Debian, /etc/default/stunnel4 tiene ENABLED=0 por defecto
        # Sin cambiarlo a 1, el servicio no arranca aunque esté en systemd
        if STUNNEL_DEFAULT.exists():
            default_txt = STUNNEL_DEFAULT.read_text(errors='ignore')
            if 'ENABLED=0' in default_txt:
                new_default = default_txt.replace('ENABLED=0', 'ENABLED=1')
                with open(STUNNEL_DEFAULT, 'w') as f:
                    f.write(new_default)
        else:
            with open(STUNNEL_DEFAULT, 'w') as f:
                f.write('ENABLED=1\n')

        subprocess.run(['systemctl', 'daemon-reload'],         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['systemctl', 'enable', 'stunnel4'],    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['systemctl', 'restart', 'stunnel4'],   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)

        # Verificar que arrancó
        status = subprocess.run(['systemctl', 'is-active', 'stunnel4'], capture_output=True, text=True)
        if status.stdout.strip() == 'active':
            print(f" {Color.GREEN}✓ stunnel4 activo{Color.END}")
        else:
            # Intentar arrancar manualmente como fallback
            subprocess.run(['stunnel4', '/etc/stunnel/stunnel.conf'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.5)
            status2 = subprocess.run(['pgrep', '-f', 'stunnel'], capture_output=True, text=True)
            if status2.stdout.strip():
                print(f" {Color.GREEN}✓ stunnel4 activo (inicio manual){Color.END}")
            else:
                print(f" {Color.RED}✗ stunnel4 no arrancó — revisa: journalctl -u stunnel4 -n 20{Color.END}")

        # ── 6. Abrir puerto en firewall ─────────────────────────────────────
        subprocess.run(['ufw', 'allow', port],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['iptables', '-I', 'INPUT', '-p', 'tcp', '--dport', str(port), '-j', 'ACCEPT'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        try:
            moratech.configure_forwarding()
        except Exception:
            pass

        # ── 7. Guardar en protocols.json ────────────────────────────────────
        try:
            prot = {}
            if PROTOCOLS.exists():
                with open(PROTOCOLS, 'r') as f:
                    prot = json.load(f)
            prot.setdefault('ssl', {})
            prot['ssl']['enabled'] = True
            prot['ssl']['port'] = int(port)
            if domain:
                prot['ssl']['domain'] = domain
                prot['ssl']['cert_type'] = 'letsencrypt'
            with open(PROTOCOLS, 'w') as f:
                json.dump(prot, f, indent=4)
        except Exception:
            pass

        print(f"\n {Color.GREEN}✓ SSL puerto {port} configurado{Color.END}")
        input("\n Presiona Enter...")

    except Exception as e:
        print(f" {Color.RED}✗ Error: {str(e)}{Color.END}")
        import traceback
        traceback.print_exc()
        input("\n Presiona Enter...")
        return

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

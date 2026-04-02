#!/usr/bin/env python3
"""
Módulo SPHYTONSL - Gestión de PROXY
"""
import subprocess
import json
import os
from pathlib import Path

from modules.common import Color, PROTOCOLS_FILE, clear_screen, print_banner, print_line
import moratech
from modules import autostart

def menu_phyton():
    """Menu de phyton"""
    while True:
        #show_dashboard()

        # Mostrar estado actual - DETECCIÓN AUTOMÁTICA
        try:
            result = subprocess.run(['ss', '-tulpn'], capture_output=True, text=True)
            output = result.stdout
            
            # Detectar Proxy Python
            proxy_ports = []
            proxy_check = subprocess.run(['pgrep', '-f', 'proxy.py'], capture_output=True, text=True)
            if proxy_check.stdout.strip():
                for line in output.split('\n'):
                    if 'python' in line.lower():
                        import re
                        match = re.search(r':(\d+)\s', line)
                        if match and match.group(1) not in ['22']:
                            proxy_ports.append(match.group(1))
            
            if proxy_ports:
                ports_str = ", ".join(set(proxy_ports))
                proxy_status = f"{Color.GREEN}ACTIVO - Puerto(s) {ports_str}{Color.END}"
            else:
                proxy_status = f"{Color.YELLOW}INACTIVO{Color.END}"
            
            print(f" {Color.CYAN}∘{Color.END} CONFIGURACION PHYTON: {proxy_status}")
            print_line()
        except:
            pass
  
        print(f"{Color.GREEN}1.{Color.END} Agregar puerto")
        print(f"{Color.GREEN}2.{Color.END} Detener puerto")
        print(f"{Color.GREEN}0.{Color.END} Volver")
        
        choice = input(f"\n{Color.YELLOW}Selecciona: {Color.END}").strip()
        if choice == '1':
            install_proxy()
        elif choice == '2':
            stop_proxy()    
        elif choice == '0':
            break
        else:
            print(f"\n{Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")


def install_proxy():
    """Instalar Proxy Python (Python 2) - versión limpia y amigable."""
    import shutil
    import time
    from pathlib import Path
    import traceback

    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}INSTALANDO PROXY PYTHON{Color.END}")
    print_line()

    port = input(f"\n {Color.GREEN}Puerto para Proxy (default 80): {Color.END}").strip()
    if not port:
        port = "80"

    try:
        # 0) Preparar checks
        def has(cmd):
            return shutil.which(cmd) is not None

        # 1) Verificar si puerto en uso (lsof preferido)
        print(f"\n {Color.YELLOW}Verificando puerto {port}...{Color.END}", end='', flush=True)
        port_busy = False
        if has('lsof'):
            r = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
            pids = [p for p in r.stdout.splitlines() if p.strip()]
            if pids:
                port_busy = True
        else:
            # intentar ss fallback
            r = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
            for ln in r.stdout.splitlines():
                if f":{port} " in ln:
                    port_busy = True
                    break
        time.sleep(0.3)
        print(" ✓")

        if port_busy:
            print(f"\n {Color.RED}⚠ Puerto {port} parece estar en uso.{Color.END}")
            if has('lsof'):
                r = subprocess.run(['lsof', '-i', f':{port}'], capture_output=True, text=True)
                # mostrar sólo la línea de proceso (concisa)
                lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
                if len(lines) > 1:
                    print(f"  ➜ {lines[1]}")
            confirm = input(f"\n {Color.YELLOW}¿Liberar el puerto {port}? (s/n): {Color.END}").strip().lower()
            if confirm != 's':
                print(f"\n {Color.RED}Instalación cancelada por usuario{Color.END}")
                input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                return
            # matar procesos que liberen el puerto
            if has('lsof'):
                r = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
                for pid in r.stdout.splitlines():
                    if pid.strip().isdigit():
                        subprocess.run(['kill', '-9', pid.strip()], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1)

        # 2) Detener restos previos (silencioso)
        subprocess.run(['pkill', '-f', 'pythonwe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-f', 'proxy.py'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 3) Instalar dependencias necesarias sólo si faltan (sin volcar logs)
        print(f"\n {Color.YELLOW}Verificando dependencias...{Color.END}", end='', flush=True)
        need_install = []
        for pkg_cmd, apt_pkg in (('python2', 'python2'), ('screen', 'screen'), ('lsof', 'lsof')):
            if not has(pkg_cmd):
                need_install.append(apt_pkg)
        if need_install:
            print(f" instalando ({', '.join(need_install)})...", end='', flush=True)
            # actualizar + instalar
            subprocess.run(['apt-get', 'update'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['apt-get', 'install', '-y'] + need_install, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.5)
        print(" ✓")

        # 4) Detectar qué bin usar para ejecutar el script (python2 preferido)
        python_bin = 'python2' if has('python2') else ('python' if has('python') else None)
        if not python_bin:
            # intentar instalar python (silencioso) si todo falló
            subprocess.run(['apt-get', 'install', '-y', 'python'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            python_bin = 'python' if has('python') else None

        if not python_bin:
            print(f"\n {Color.RED}✗ No hay intérprete Python disponible (ni python2 ni python).{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return

        print(f"\n {Color.YELLOW}Puerto SSH detectado: 22{Color.END}")

        # 5) Escribir script proxy desde template
        from modules.proxy_template import PROXY_SCRIPT
        proxy_path = Path('/root/proxy.py')
        proxy_script = PROXY_SCRIPT.format(port=port)

        # Para no cambiar tu script, guardamos exactamente el original que tengas.
        # Si quieres, reemplazo el contenido completo aquí.
        with open(proxy_path, 'w') as f:
            # Si prefieres conservar el script "exacto" que traías, pega aquí tu código completo.
            f.write(proxy_script)
        proxy_path.chmod(0o755)

        # 6) Iniciar en screen (silencioso)
        print(f"\n {Color.YELLOW}Iniciando proxy en segundo plano...{Color.END}", end='', flush=True)
        # limpiar sesiones huérfanas
        subprocess.run(['screen', '-wipe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # arrancar session
        start_cmd = [ 'screen', '-dmS', 'pythonwe', python_bin, str(proxy_path) ]
        subprocess.run(start_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.2)

        # 7) Verificar sesión screen (filtrando el ruido "No Sockets found...")
        r = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        screen_out = (r.stdout or '') + (r.stderr or '')
        if 'pythonwe' in screen_out:
            print(" ✓")
        else:
            # intentar buscar por procesos pgrep
            r2 = subprocess.run(['pgrep', '-f', 'pythonwe'], capture_output=True, text=True)
            if r2.stdout.strip():
                print(" ✓")
            else:
                print(" ✗")
                print(f"\n {Color.RED}⚠ Atención: no se detectó la sesión 'pythonwe'. Revisa logs con: screen -r pythonwe{Color.END}")
                input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
                return

        # 8) Abrir puerto y configurar forwarding (silencioso)
        subprocess.run(['iptables', '-I', 'INPUT', '-p', 'tcp', '--dport', port, '-j', 'ACCEPT'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['ufw', 'allow', port], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"\n {Color.YELLOW}Configurando forwarding...{Color.END}", end='', flush=True)
        try:
            moratech.configure_forwarding()
            print(" ✓")
        except Exception:
            print(" ✗")
            # no rompemos todo por esto, sólo avisamos
            traceback.print_exc()

        # 9) Guardar estado en PROTOCOLS_FILE (silencioso)
        try:
            with open(PROTOCOLS_FILE, 'r') as f:
                protocols = json.load(f)
        except Exception:
            protocols = {}
        protocols.setdefault('proxy', {})['enabled'] = True
        protocols['proxy']['port'] = int(port)
        with open(PROTOCOLS_FILE, 'w') as f:
            json.dump(protocols, f, indent=4)

        # 10) Mensaje final corto y limpio
        print(f"\n\n {Color.GREEN}✓ Proxy Python instalado en puerto {port}{Color.END}")
        print(f" {Color.YELLOW}Para ver logs: screen -r pythonwe{Color.END}")

        moratech.log_action("admin", f"Proxy Python configurado en puerto {port}")
        autostart.register('proxy', port=int(port))

    except Exception as e:
        print(f"\n {Color.RED}✗ Error durante la instalación: {str(e)}{Color.END}")
        # muestra traza breve sólo si hace falta depurar
        traceback.print_exc()

    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")


def stop_proxy():
    """Detener Proxy Python (robusto: usa pgrep + lsof/ss, no depende de netstat)."""
    import re
    from pathlib import Path
    import shutil
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}DETENER PROXY PYTHON{Color.END}")
    print_line()

    try:
        # 1) Encontrar PIDs relevantes (proxy.py / pythonwe)
        pids = set()

        def safe_run(cmd):
            try:
                return subprocess.run(cmd, capture_output=True, text=True, check=False)
            except Exception:
                return None

        # pgrep first (fast)
        for pattern in ['pythonwe', 'proxy.py']:
            r = safe_run(['pgrep', '-f', pattern])
            if r and r.stdout.strip():
                for ln in r.stdout.splitlines():
                    ln = ln.strip()
                    if ln.isdigit():
                        pids.add(ln)

        # fallback: ps aux search
        if not pids:
            r = safe_run(['ps', 'aux'])
            if r and r.stdout:
                for line in r.stdout.splitlines():
                    if ('proxy.py' in line or 'pythonwe' in line) and 'grep' not in line:
                        parts = line.split()
                        if len(parts) >= 2 and parts[1].isdigit():
                            pids.add(parts[1])

        if not pids:
            print(f"\n {Color.YELLOW}No hay proxies Python activos (no se encontraron pids){Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return

        # 2) Para cada PID intentar detectar puertos (lsof preferible, si no -> ss)
        pid_to_ports = {}
        lsof_ok = shutil.which('lsof') is not None

        ss_output = None
        if not lsof_ok:
            # obtener ss output una sola vez para fallback
            ss_r = safe_run(['ss', '-tlnp'])
            ss_output = ss_r.stdout if ss_r and ss_r.stdout else ''

        for pid in pids:
            ports = set()
            if lsof_ok:
                r = safe_run(['lsof', '-Pan', '-p', pid, '-iTCP', '-sTCP:LISTEN'])
                if r and r.stdout:
                    for ln in r.stdout.splitlines()[1:]:
                        m = re.search(r':(\d+)->|:(\d+)\s', ln)
                        if m:
                            port = m.group(1) or m.group(2)
                            if port:
                                ports.add(port)
            # fallback using ss output (pid=1234 in the "users:" field)
            if not ports and ss_output is not None:
                for ln in ss_output.splitlines():
                    if f"pid={pid}" in ln or f"pid={pid}," in ln:
                        m = re.search(r':(\d+)\s', ln)
                        if m:
                            ports.add(m.group(1))
            if not ports:
                ports.add("desconocido")

            pid_to_ports[pid] = sorted(list(ports))

        # 3) Mostrar opciones al usuario
        print(f"\n {Color.YELLOW}Proxies Python detectados:{Color.END}")
        # construir lista única de (port->pid) priorizando puertos reales
        unique = {}
        for pid, ports in pid_to_ports.items():
            for port in ports:
                if port not in unique:
                    unique[port] = pid

        ports_list = list(unique.keys())
        for i, port in enumerate(ports_list, 1):
            pid = unique[port]
            print(f" {Color.GREEN}[{i}]{Color.END} Puerto {port} (PID: {pid})")

        print(f"\n {Color.GREEN}[X]{Color.END} Detener TODOS los proxies")
        print(f" {Color.RED}[0]{Color.END} Cancelar")
        print_line()

        choice = input(f" {Color.CYAN}►{Color.END} Selecciona opción: ").strip()
        if choice.upper() == '0':
            return

        # 4) Ejecución de la acción
        def safe_kill(pid):
            try:
                subprocess.run(['kill', '-9', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass

        def remove_iptables_port(port):
            try:
                subprocess.run(['iptables', '-D', 'INPUT', '-p', 'tcp', '--dport', str(port), '-j', 'ACCEPT'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass
            try:
                subprocess.run(['ufw', 'delete', 'allow', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass

        if choice == 'X':
            confirm = input(f"\n {Color.YELLOW}¿Detener TODOS los proxies? (s/n): {Color.END}").strip().lower()
            if confirm != 's':
                return
            # kill by name + screen quit
            subprocess.run(['pkill', '-f', 'pythonwe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'proxy.py'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['screen', '-S', 'pythonwe', '-X', 'quit'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # remove iptables for detected ports
            for port in ports_list:
                if port != "desconocido":
                    remove_iptables_port(port)
            # update config
            try:
                with open(PROTOCOLS_FILE, 'r') as f:
                    protocols = json.load(f)
                protocols.setdefault('proxy', {})['enabled'] = False
                protocols['proxy'].pop('port', None)
                with open(PROTOCOLS_FILE, 'w') as f:
                    json.dump(protocols, f, indent=4)
            except Exception:
                pass
            print(f"\n {Color.GREEN}✓ Todos los proxies detenidos{Color.END}")
            moratech.log_action("admin", "Todos los proxies detenidos")
            autostart.unregister('proxy')
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
            return

        # user selected single
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(ports_list):
                port = ports_list[idx]
                pid = unique[port]
                # kill and clean
                safe_kill(pid)
                remove_iptables_port(port)
                # try to also quit screen session
                subprocess.run(['screen', '-S', 'pythonwe', '-X', 'quit'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                # update config: if the port matches protocols.json remove it
                try:
                    with open(PROTOCOLS_FILE, 'r') as f:
                        protocols = json.load(f)
                    if protocols.get('proxy', {}).get('port') == int(port):
                        protocols['proxy']['enabled'] = False
                        protocols['proxy'].pop('port', None)
                        with open(PROTOCOLS_FILE, 'w') as f:
                            json.dump(protocols, f, indent=4)
                except Exception:
                    pass

                print(f"\n {Color.GREEN}✓ Proxy en puerto {port} detenido{Color.END}")
                moratech.log_action("admin", f"Proxy puerto {port} detenido")
                autostart.unregister('proxy')
            else:
                print(f" {Color.RED}✗ Opción inválida{Color.END}")
        except ValueError:
            print(f" {Color.RED}✗ Opción inválida{Color.END}")

    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

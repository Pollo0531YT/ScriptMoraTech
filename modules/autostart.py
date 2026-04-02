#!/usr/bin/env python3
"""
Módulo AUTOSTART - Persistencia de servicios al reinicio del VPS
Registra qué servicios están activos y los relanza vía systemd al boot.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

CONFIG_DIR = Path.home() / '.moratech'
AUTOSTART_FILE = CONFIG_DIR / 'autostart.json'
INSTALL_DIR = Path('/usr/local/lib/moratech')
SYSTEMD_SERVICE = Path('/etc/systemd/system/moratech-autostart.service')

SERVICE_LABELS = {
    'proxy':       'Proxy Python',
    'badvpn':      'BadVPN',
    'checkuser':   'CheckUser Online',
    'telegram_bot':'Bot Telegram',
    'api_server':  'API Individual',
    'api_general': 'API Master',
}

# ── Persistencia ────────────────────────────────────────────────────────────

def _load():
    if AUTOSTART_FILE.exists():
        try:
            with open(AUTOSTART_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = AUTOSTART_FILE.with_suffix('.tmp')
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=4)
    os.replace(tmp, AUTOSTART_FILE)

# ── API pública ──────────────────────────────────────────────────────────────

def register(service, **kwargs):
    """Registrar (o actualizar) un servicio para autostart."""
    data = _load()
    if service == 'badvpn':
        existing = data.get('badvpn', {'enabled': True, 'ports': []})
        existing['enabled'] = True
        ports = existing.get('ports', [])
        new_port = int(kwargs.get('port', 0))
        if new_port and new_port not in ports:
            ports.append(new_port)
        existing['ports'] = ports
        data['badvpn'] = existing
    else:
        entry = {'enabled': True}
        entry.update({k: v for k, v in kwargs.items()})
        data[service] = entry
    _save(data)

def unregister(service, port=None):
    """Quitar un servicio del autostart."""
    data = _load()
    if service == 'badvpn' and port is not None:
        if 'badvpn' in data:
            ports = data['badvpn'].get('ports', [])
            port_int = int(port)
            if port_int in ports:
                ports.remove(port_int)
            if not ports:
                del data['badvpn']
            else:
                data['badvpn']['ports'] = ports
    else:
        data.pop(service, None)
    _save(data)

# ── Inicio de cada servicio ──────────────────────────────────────────────────

def _has(cmd):
    return shutil.which(cmd) is not None

def _start_service(name, config):
    """Inicia un servicio individual. Fallas silenciosas para no bloquear el boot."""
    try:
        if name == 'proxy':
            port = config.get('port', 80)
            if not Path('/root/proxy.py').exists():
                return
            # Buscar python2/python con rutas absolutas (systemd no hereda PATH completo)
            python_bin = None
            for candidate in ['/usr/bin/python2', '/usr/bin/python', '/usr/local/bin/python2', '/usr/local/bin/python']:
                if Path(candidate).exists():
                    python_bin = candidate
                    break
            if not python_bin:
                python_bin = _has('python2') or _has('python')
            if python_bin:
                subprocess.run(
                    ['/usr/bin/screen', '-dmS', 'pythonwe', python_bin, '/root/proxy.py'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                subprocess.run(
                    ['/sbin/iptables', '-I', 'INPUT', '-p', 'tcp', '--dport', str(port), '-j', 'ACCEPT'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )

        elif name == 'badvpn':
            if not _has('badvpn-udpgw'):
                return
            for port in config.get('ports', []):
                screen_name = f'badvpn_{port}'
                subprocess.run(
                    ['screen', '-dmS', screen_name,
                     'badvpn-udpgw', '--listen-addr', f'127.0.0.1:{port}'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                time.sleep(0.5)

        elif name == 'checkuser':
            port = config.get('port', 8888)
            script = INSTALL_DIR / 'modules' / 'checkuser_flask.py'
            if script.exists():
                subprocess.run(
                    ['screen', '-dmS', 'moratech_checkuser',
                     'python3', str(script), str(port)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )

        elif name == 'telegram_bot':
            script = INSTALL_DIR / 'modules' / 'telegram_bot.py'
            bot_config = CONFIG_DIR / 'bot_config.json'
            if script.exists() and bot_config.exists():
                subprocess.run(
                    ['screen', '-dmS', 'moratech_telegram_bot', 'python3', str(script)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )

        elif name == 'api_server':
            port = config.get('port', 9000)
            script = INSTALL_DIR / 'modules' / 'api_server.py'
            if script.exists():
                subprocess.run(
                    ['screen', '-dmS', 'api_server_individual',
                     'python3', str(script), str(port)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )

        elif name == 'api_general':
            port = config.get('port', 9100)
            if (INSTALL_DIR / 'modules' / 'api_general.py').exists():
                subprocess.run(
                    ['screen', '-dmS', 'servidor_global',
                     'python3', '-m', 'modules.api_general', str(port)],
                    cwd=str(INSTALL_DIR),
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )

    except Exception:
        pass  # Nunca romper el boot por un servicio individual

def run_all():
    """Inicia todos los servicios registrados. Llamado por systemd al boot."""
    time.sleep(5)  # Esperar red y demás servicios del sistema
    subprocess.run(['screen', '-wipe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    data = _load()
    for service, config in data.items():
        if config.get('enabled', True):
            _start_service(service, config)
            time.sleep(1)  # Pequeña pausa entre servicios

# ── Gestión del servicio systemd ─────────────────────────────────────────────

def is_systemd_installed():
    return SYSTEMD_SERVICE.exists()

def install_systemd_service():
    """Crear y habilitar el servicio systemd moratech-autostart."""
    content = f"""[Unit]
Description=MoraTech Autostart - Servicios VPN
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 {INSTALL_DIR}/modules/autostart.py --startup
WorkingDirectory={INSTALL_DIR}
User=root
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="HOME=/root"

[Install]
WantedBy=multi-user.target
"""
    with open(SYSTEMD_SERVICE, 'w') as f:
        f.write(content)

    subprocess.run(['systemctl', 'daemon-reload'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['systemctl', 'enable', 'moratech-autostart'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def uninstall_systemd_service():
    """Deshabilitar y eliminar el servicio systemd."""
    subprocess.run(['systemctl', 'disable', 'moratech-autostart'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if SYSTEMD_SERVICE.exists():
        SYSTEMD_SERVICE.unlink()
    subprocess.run(['systemctl', 'daemon-reload'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ── Menú interactivo ─────────────────────────────────────────────────────────

def menu_autostart():
    from modules.common import Color, clear_screen, print_line, print_banner

    while True:
        clear_screen()
        print_banner()
        print_line()
        print(f" {Color.CYAN}>> AUTOSTART AL REINICIO <<{Color.END}")
        print_line()

        systemd_ok = is_systemd_installed()
        estado = f"{Color.GREEN}ACTIVO{Color.END}" if systemd_ok else f"{Color.RED}NO INSTALADO{Color.END}"
        print(f" {Color.CYAN}∘{Color.END} Servicio systemd: {estado}")
        print_line()

        data = _load()
        print(f" {Color.YELLOW}Servicios registrados:{Color.END}\n")

        if not data:
            print(f"   (ninguno — activa servicios desde sus respectivos menús)")
        else:
            for svc, cfg in data.items():
                label = SERVICE_LABELS.get(svc, svc)
                on = cfg.get('enabled', True)
                tag = f"{Color.GREEN}ON{Color.END}" if on else f"{Color.RED}OFF{Color.END}"
                extra = ""
                if svc == 'proxy':
                    extra = f"  puerto {cfg.get('port', '?')}"
                elif svc == 'badvpn':
                    extra = f"  puertos {cfg.get('ports', [])}"
                elif svc in ('checkuser', 'api_server', 'api_general'):
                    extra = f"  puerto {cfg.get('port', '?')}"
                print(f"  {Color.CYAN}∘{Color.END} {label}: [{tag}]{extra}")

        print_line()
        if systemd_ok:
            print(f" {Color.GREEN}[1]{Color.END} ➮ Desinstalar autostart systemd")
        else:
            print(f" {Color.GREEN}[1]{Color.END} ➮ Instalar autostart systemd (activa al reiniciar)")
        print(f" {Color.GREEN}[2]{Color.END} ➮ Iniciar ahora todos los registrados")
        print(f" {Color.RED}[0]{Color.END} ⇦ Volver")
        print_line()

        choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()

        if choice == '1':
            if systemd_ok:
                uninstall_systemd_service()
                print(f"\n {Color.GREEN}✓ Autostart desinstalado{Color.END}")
            else:
                install_systemd_service()
                print(f"\n {Color.GREEN}✓ Autostart instalado - se activará en cada reinicio{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

        elif choice == '2':
            print(f"\n {Color.YELLOW}Iniciando servicios registrados...{Color.END}")
            run_all()
            print(f" {Color.GREEN}✓ Listo{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")

        elif choice == '0':
            break


if __name__ == '__main__':
    if '--startup' in sys.argv:
        run_all()

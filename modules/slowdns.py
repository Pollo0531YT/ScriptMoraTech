#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instalador/gestor slowdns (adaptado a MoraTech + opción key fija)
- Escribe server.key con MASTER_PRIV (por defecto).
- Descarga server.pub desde Nevermore (fallback).
- Descarga sldns-server / sldns-client (fallback).
- Crea systemd units server-sldns & client-sldns.
- Aplica reglas iptables mínimas.
"""
import os
import sys
import subprocess
import shutil
import json
import time
from pathlib import Path

# IMPORTS DEL PROYECTO (colores, helpers)
from modules.common import Color, print_line, print_banner, clear_screen

SLOW_DIR = "/etc/slowdns"
SERVER_BIN = f"{SLOW_DIR}/sldns-server"
CLIENT_BIN = f"{SLOW_DIR}/sldns-client"
KEY_FILE = f"{SLOW_DIR}/server.key"
PUB_FILE = f"{SLOW_DIR}/server.pub"
CONFIG_FILE = f"{SLOW_DIR}/mora_conf.json"
LOG_FILE = f"{SLOW_DIR}/slowdns.log"

# Tu master_priv fija (la que quieres mantener)
MASTER_PRIV = "b17a4ce4c0e8cc54e33ee70b5e5a11c1a3ba853fd3743897ee091f9fcb53f0e2"

# URLs primarias y fallback (raw + jsdelivr)
BASE_RAW = "https://raw.githubusercontent.com/NevermoreSSH/hopp/main/slowdns"
SERVER_URLS = [
    f"{BASE_RAW}/sldns-server",
    "https://cdn.jsdelivr.net/gh/NevermoreSSH/hopp@main/slowdns/sldns-server"
]
CLIENT_URLS = [
    f"{BASE_RAW}/sldns-client",
    "https://cdn.jsdelivr.net/gh/NevermoreSSH/hopp@main/slowdns/sldns-client"
]
PUB_URLS = [
    f"{BASE_RAW}/server.pub",
    "https://cdn.jsdelivr.net/gh/NevermoreSSH/hopp@main/slowdns/server.pub"
]


def run(cmd, capture=False, check=False):
    """Helper: ejecuta comando, devuelve CompletedProcess o excepción."""
    if capture:
        return subprocess.run(cmd, capture_output=True, text=True, check=check)
    else:
        return subprocess.run(cmd, check=check)


def ensure_root():
    if os.geteuid() != 0:
        print("Ejecuta este script con sudo/root.")
        sys.exit(1)


def ensure_dirs():
    os.makedirs(SLOW_DIR, exist_ok=True)
    os.chmod(SLOW_DIR, 0o700)
    Path(LOG_FILE).touch(exist_ok=True)
    os.chmod(LOG_FILE, 0o600)


def apt_install(pkgs):
    print("  ✓ Asegurando dependencias básicas...")
    run(["apt-get", "update"], capture=True)
    run(["apt-get", "install", "-y"] + pkgs)


def download_any(urls, dest):
    tmp = f"{dest}.tmp"
    if os.path.exists(tmp):
        os.unlink(tmp)
    for url in urls:
        print(f"    -> intentando: {url}")
        # prefer curl
        if shutil.which("curl"):
            r = run(["curl", "-fsSL", "-o", tmp, url], capture=True)
            ok = (getattr(r, "returncode", 1) == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 0)
        else:
            r = run(["wget", "-q", "-O", tmp, url], capture=True)
            ok = (getattr(r, "returncode", 1) == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 0)
        if ok:
            shutil.move(tmp, dest)
            os.chmod(dest, 0o755)
            return True
        # limpiar tmp y seguir al siguiente url
        if os.path.exists(tmp):
            os.unlink(tmp)
    return False


def write_key(fixed_priv):
    # escribe PRIV como fichero (no es la "clave PEM", es la key usada por sldns)
    with open(KEY_FILE, "w") as f:
        f.write(fixed_priv.strip() + "\n")
    os.chmod(KEY_FILE, 0o600)


def save_config(ns, lport):
    data = {"ns": ns, "port": str(lport)}
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)
    os.chmod(CONFIG_FILE, 0o600)


def create_systemd_units(nameserver, local_port):
    server_unit = f"""[Unit]
Description=Server SlowDNS By MoraTech
After=network.target

[Service]
Type=simple
User=root
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ExecStart={SERVER_BIN} -udp :5300 -privkey-file {KEY_FILE} {nameserver} 127.0.0.1:{local_port}
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""
    client_unit = f"""[Unit]
Description=Client SlowDNS By MoraTech
After=network.target

[Service]
Type=simple
User=root
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ExecStart={CLIENT_BIN} -udp 8.8.8.8:53 --pubkey-file {PUB_FILE} {nameserver} 127.0.0.1:3369
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""
    with open("/etc/systemd/system/server-sldns.service", "w") as f:
        f.write(server_unit)
    with open("/etc/systemd/system/client-sldns.service", "w") as f:
        f.write(client_unit)
    os.chmod("/etc/systemd/system/server-sldns.service", 0o644)
    os.chmod("/etc/systemd/system/client-sldns.service", 0o644)
    run(["systemctl", "daemon-reload"])


def apply_iptables():
    # Añadir reglas concretas si no existen (no flush total)
    print("  ✓ Aplicando reglas iptables necesarias...")
    # permitir loopback
    run(["iptables", "-C", "INPUT", "-i", "lo", "-j", "ACCEPT"], capture=True)
    run(["iptables", "-A", "INPUT", "-i", "lo", "-j", "ACCEPT"])
    run(["iptables", "-C", "OUTPUT", "-o", "lo", "-j", "ACCEPT"], capture=True)
    run(["iptables", "-A", "OUTPUT", "-o", "lo", "-j", "ACCEPT"])
    # aceptar 5300/udp
    run(["iptables", "-C", "INPUT", "-p", "udp", "--dport", "5300", "-j", "ACCEPT"], capture=True)
    run(["iptables", "-A", "INPUT", "-p", "udp", "--dport", "5300", "-j", "ACCEPT"])
    # redirigir 53 -> 5300
    ipt_save = run(["iptables-save"], capture=True)
    ipt_txt = ipt_save.stdout if hasattr(ipt_save, "stdout") else ""
    if "--to-ports 5300" not in ipt_txt:
        run(["iptables", "-t", "nat", "-A", "PREROUTING", "-p", "udp", "--dport", "53", "-j", "REDIRECT", "--to-ports", "5300"])


def enable_and_start_services():
    run(["systemctl", "enable", "--now", "server-sldns"], capture=True)
    run(["systemctl", "enable", "--now", "client-sldns"], capture=True)
    time.sleep(1)
    # check status (short)
    s1 = run(["systemctl", "is-active", "server-sldns"], capture=True)
    s2 = run(["systemctl", "is-active", "client-sldns"], capture=True)
    return (getattr(s1, "stdout", "").strip() == "active", getattr(s2, "stdout", "").strip() == "active")


def install_flow():
    ensure_root()
    ensure_dirs()
    print("\n INSTALANDO SLOWDNS (MoraTech) - breve...")
    # dependencies
    apt_install(["curl", "wget", "screen", "iptables", "dnsutils", "python3", "git"])
    print("  ✓ Dependencias OK.")

    # opción key fija o random (por defecto fija)
    use_fixed = True
    ans = input(" Usar KEY FIJA (recomendada) [S/n]: ").strip().lower()
    if ans == "n":
        use_fixed = False

    if use_fixed:
        print("  -> Usando KEY FIJA (MASTER_PRIV).")
        write_key(MASTER_PRIV)
    else:
        # generar key aleatoria de 64 hex chars
        import secrets
        newkey = secrets.token_hex(32)
        print("  -> Generando key random.")
        write_key(newkey)

    # descargar server.pub
    print("  -> Descargando server.pub ...")
    ok_pub = download_any(PUB_URLS, PUB_FILE)
    if not ok_pub:
        print(" ✗ No se pudo bajar server.pub. Abortar.")
        return

    # descargar binarios server & client
    print("  -> Descargando sldns-server ...")
    ok = download_any(SERVER_URLS, SERVER_BIN)
    if not ok:
        print(" ✗ Falló descarga sldns-server. Abortar.")
        return
    print("  -> Descargando sldns-client ...")
    ok = download_any(CLIENT_URLS, CLIENT_BIN)
    if not ok:
        print(" ✗ Falló descarga sldns-client. Abortar.")
        return

    # permisos
    os.chmod(SERVER_BIN, 0o755)
    os.chmod(CLIENT_BIN, 0o755)
    os.chmod(PUB_FILE, 0o644)
    os.chmod(KEY_FILE, 0o600)

    # pedir NS y puertos
    ns = input(" NS domain (ej: tu.ns.example.com): ").strip()
    if not ns:
        print(" ✗ NS vacio. Abortar.")
        return
    lport = input(" Puerto SSH local en servidor (ej 22): ").strip() or "22"

    save_config(ns, lport)
    apply_iptables()
    create_systemd_units(ns, lport)
    active_server, active_client = enable_and_start_services()
    if active_server and active_client:
        print("\n ✓ slowdns instalado y servicios activos.")
        print(f"   Logs: journalctl -u server-sldns -n 200 --no-pager")
    else:
        print("\n ¡Atención! Uno o ambos servicios NO iniciaron correctamente.")
        print(" Revisa: journalctl -u server-sldns -n 200 --no-pager")
    print("\n Fin.\n")


def stop_flow():
    ensure_root()
    run(["systemctl", "stop", "server-sldns"], capture=True)
    run(["systemctl", "stop", "client-sldns"], capture=True)
    run(["systemctl", "disable", "server-sldns"], capture=True)
    run(["systemctl", "disable", "client-sldns"], capture=True)
    run(["pkill", "-f", "sldns-server"], capture=True)
    run(["pkill", "-f", "sldns-client"], capture=True)
    print(" Servicios slowdns detenidos.")


def uninstall_flow():
    stop_flow()
    # eliminar archivos
    for p in (SERVER_BIN, CLIENT_BIN, KEY_FILE, PUB_FILE, CONFIG_FILE, LOG_FILE):
        try:
            if os.path.exists(p):
                os.unlink(p)
        except Exception:
            pass
    for u in ("/etc/systemd/system/server-sldns.service", "/etc/systemd/system/client-sldns.service"):
        try:
            if os.path.exists(u):
                os.unlink(u)
        except Exception:
            pass
    run(["systemctl", "daemon-reload"], capture=True)
    print(" Uninstall completo (archivos eliminados).")


# -------------------------
# MENU (limpio, con colores)
# -------------------------
def menu_slowdns():
    """Menú SLOWDNS (limpio, con colores)."""
    while True:
        try:
            clear_screen()
            # header sencillo
            print(f"{Color.CYAN}+------------------ SLOWDNS (MoraTech) ------------------+{Color.END}")
            # estado service / pgrep
            try:
                s = run(["systemctl", "is-active", "server-sldns"], capture=True)
                s_active = getattr(s, "stdout", "").strip() == "active"
            except Exception:
                p = run(["pgrep", "-f", "sldns-server"], capture=True)
                s_active = bool(getattr(p, "stdout", "").strip())
            status_txt = f"{Color.GREEN}ACTIVO{Color.END}" if s_active else f"{Color.RED}INACTIVO{Color.END}"
            print(f" {Color.YELLOW}Estado:{Color.END} {status_txt}")
            print_line()

            # opciones
            print(f" {Color.GREEN}1.{Color.END} Instalar / Iniciar")
            print(f" {Color.GREEN}2.{Color.END} Detener")
            print(f" {Color.GREEN}3.{Color.END} Info")
            print(f" {Color.GREEN}4.{Color.END} Ver logs")
            print(f" {Color.GREEN}5.{Color.END} Desinstalar (elimina binarios & units)")
            print(f" {Color.GREEN}0.{Color.END} Volver")
            print_line()

            choice = input(f"\n{Color.CYAN}► Selecciona: {Color.END}").strip()

            if choice == "1":
                install_flow()
            elif choice == "2":
                stop_flow()
                input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")
            elif choice == "3":
                conf = {"ns": "No configurado", "port": "?"}
                if os.path.exists(CONFIG_FILE):
                    try:
                        with open(CONFIG_FILE, "r") as f:
                            conf = json.load(f)
                    except:
                        pass
                print_line()
                print(f" {Color.CYAN}NS:{Color.END} {Color.GREEN}{conf.get('ns')}{Color.END}")
                print(f" {Color.CYAN}Puerto SSH local:{Color.END} {Color.GREEN}{conf.get('port')}{Color.END}")
                print(f" {Color.CYAN}Key (preview):{Color.END} {Color.YELLOW}{MASTER_PRIV[:20]}...{Color.END}")
                input(f"\n{Color.CYAN}Presiona Enter para volver...{Color.END}")
            elif choice == "4":
                # logs: prefer journalctl
                if os.path.exists("/etc/systemd/system/server-sldns.service"):
                    print(f"\n {Color.YELLOW}Abriendo journalctl -u server-sldns (Ctrl+C para salir){Color.END}\n")
                    try:
                        run(["bash", "-c", "journalctl -u server-sldns -n 200 --no-pager -f"])
                    except KeyboardInterrupt:
                        pass
                elif os.path.exists(LOG_FILE):
                    print(f"\n {Color.YELLOW}Abriendo tail -f {LOG_FILE} (Ctrl+C para salir){Color.END}\n")
                    try:
                        run(["bash", "-c", f"tail -n 200 -f {LOG_FILE}"])
                    except KeyboardInterrupt:
                        pass
                else:
                    print(f"\n {Color.RED}No hay logs disponibles.{Color.END}")
                    input(f"\n{Color.CYAN}Presiona Enter...{Color.END}")
            elif choice == "5":
                confirm = input(f"{Color.YELLOW}¿Eliminar todo (binarios, keys, units)? (s/N): {Color.END}").strip().lower()
                if confirm == "s":
                    uninstall_flow()
                    input(f"\n{Color.CYAN}Hecho. Presiona Enter...{Color.END}")
                else:
                    print(f"{Color.YELLOW}Cancelado.{Color.END}")
                    time.sleep(0.6)
            elif choice == "0":
                break
            else:
                print(f"\n{Color.RED}Opción inválida{Color.END}")
                time.sleep(0.5)

        except KeyboardInterrupt:
            break


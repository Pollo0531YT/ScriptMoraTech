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
    """Instala paquetes sin imprimir; devuelve True/False."""
    env = os.environ.copy()
    env["DEBIAN_FRONTEND"] = "noninteractive"
    try:
        subprocess.run(["apt-get", "update", "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, env=env)
        subprocess.run(["apt-get", "install", "-y"] + pkgs, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, env=env)
        return True
    except subprocess.CalledProcessError:
        return False



def download_any(urls, dest):
    tmp = f"{dest}.tmp"
    if os.path.exists(tmp):
        os.unlink(tmp)
    for url in urls:
        # intento silencioso
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
        if os.path.exists(tmp):
            os.unlink(tmp)
    return False


def write_key(fixed_priv):
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
    # permitir loopback
    run(["iptables", "-C", "INPUT", "-i", "lo", "-j", "ACCEPT"], capture=True)
    run(["iptables", "-A", "INPUT", "-i", "lo", "-j", "ACCEPT"])
    run(["iptables", "-C", "OUTPUT", "-o", "lo", "-j", "ACCEPT"], capture=True)
    run(["iptables", "-A", "OUTPUT", "-o", "lo", "-j", "ACCEPT"])
    # aceptar 5300/udp
    run(["iptables", "-C", "INPUT", "-p", "udp", "--dport", "5300", "-j", "ACCEPT"], capture=True)
    run(["iptables", "-A", "INPUT", "-p", "udp", "--dport", "5300", "-j", "ACCEPT"])
    # redirigir 53 -> 5300 si no existe
    ipt_save = run(["iptables-save"], capture=True)
    ipt_txt = ipt_save.stdout if hasattr(ipt_save, "stdout") else ""
    if "--to-ports 5300" not in ipt_txt:
        run(["iptables", "-t", "nat", "-A", "PREROUTING", "-p", "udp", "--dport", "53", "-j", "REDIRECT", "--to-ports", "5300"])


def enable_and_start_services():
    run(["systemctl", "enable", "--now", "server-sldns"], capture=True)
    run(["systemctl", "enable", "--now", "client-sldns"], capture=True)
    time.sleep(1)
    s1 = run(["systemctl", "is-active", "server-sldns"], capture=True)
    s2 = run(["systemctl", "is-active", "client-sldns"], capture=True)
    return (getattr(s1, "stdout", "").strip() == "active", getattr(s2, "stdout", "").strip() == "active")


# -----------------------------
# INSTALL_FLOW (reordenado y bonito)
# -----------------------------
def install_flow():
    ensure_root()
    ensure_dirs()
    clear_screen()
    print(f"{Color.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Color.END}")
    print(f"{Color.CYAN} INSTALANDO SLOWDNS (MoraTech) - PROCESO SIMPLE{Color.END}")
    print(f"{Color.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Color.END}\n")

    # 0) Pedir NS y puerto primero
    ns = input(f" {Color.GREEN}Dominio NS (ej: tu.ns.example.com): {Color.END}").strip()
    if not ns:
        print(f"\n {Color.RED}✗ NS vacio. Abortando.{Color.END}")
        input("\n Presiona Enter...")
        return
    lport = input(f" {Color.GREEN}Puerto SSH local en servidor (ej 22): {Color.END}").strip() or "22"

    # Save early so menu info lo ve inmediatamente
    save_config(ns, lport)

    # Paso 1: dependencias
    print(f"\n {Color.YELLOW}1) Instalando dependencias...{Color.END}")
    if apt_install(["curl", "wget", "screen", "iptables", "dnsutils", "python3", "git"]):
        print(f"  {Color.GREEN}✓ Dependencias instaladas{Color.END}")
    else:
        print(f"  {Color.RED}✗ Error instalando dependencias{Color.END}")
        input("\n Presiona Enter...")
        return

    # Paso 2: key (fija o random)
    print(f"\n {Color.YELLOW}2) Configurando key...{Color.END}")
    use_fixed = True
    ans = input(f" Usar KEY FIJA (recomendada) [S/n]: ").strip().lower()
    if ans == "n":
        use_fixed = False
    if use_fixed:
        write_key(MASTER_PRIV)
        print(f"  {Color.GREEN}✓ Key fija escrita{Color.END}")
    else:
        import secrets
        newkey = secrets.token_hex(32)
        write_key(newkey)
        print(f"  {Color.GREEN}✓ Key random generada y escrita{Color.END}")

    # Paso 3: descargar server.pub
    print(f"\n {Color.YELLOW}3) Descargando server.pub...{Color.END}")
    ok_pub = download_any(PUB_URLS, PUB_FILE)
    if not ok_pub:
        print(f"  {Color.RED}✗ No se pudo descargar server.pub. Abortando.{Color.END}")
        input("\n Presiona Enter...")
        return
    print(f"  {Color.GREEN}✓ server.pub descargado{Color.END}")

    # Paso 4: descargar binarios
    print(f"\n {Color.YELLOW}4) Descargando sldns-server y sldns-client...{Color.END}")
    ok = download_any(SERVER_URLS, SERVER_BIN)
    if not ok:
        print(f"  {Color.RED}✗ Falló descarga sldns-server. Abortando.{Color.END}")
        input("\n Presiona Enter...")
        return
    ok = download_any(CLIENT_URLS, CLIENT_BIN)
    if not ok:
        print(f"  {Color.RED}✗ Falló descarga sldns-client. Abortando.{Color.END}")
        input("\n Presiona Enter...")
        return
    os.chmod(SERVER_BIN, 0o755)
    os.chmod(CLIENT_BIN, 0o755)
    os.chmod(PUB_FILE, 0o644)
    os.chmod(KEY_FILE, 0o600)
    print(f"  {Color.GREEN}✓ Binarios listos{Color.END}")

    # Paso 5: iptables
    print(f"\n {Color.YELLOW}5) Aplicando reglas de red (iptables)...{Color.END}")
    try:
        apply_iptables()
        print(f"  {Color.GREEN}✓ Reglas aplicadas{Color.END}")
    except Exception as e:
        print(f"  {Color.RED}✗ Error aplicando iptables: {e}{Color.END}")
        # seguimos aunque iptables falle; usuario lo revisa
    # Paso 6: crear unidades systemd
    print(f"\n {Color.YELLOW}6) Creando servicios systemd...{Color.END}")
    try:
        create_systemd_units(ns, lport)
        print(f"  {Color.GREEN}✓ Units creadas{Color.END}")
    except Exception as e:
        print(f"  {Color.RED}✗ Error creando units: {e}{Color.END}")
        input("\n Presiona Enter...")
        return

    # Paso 7: activar servicios
    print(f"\n {Color.YELLOW}7) Activando servicios...{Color.END}")
    active_server, active_client = enable_and_start_services()
    if active_server and active_client:
        print(f"  {Color.GREEN}✓ Servicios activos{Color.END}")
        print(f"\n {Color.GREEN}✓ slowdns instalado y servicios activos.{Color.END}")
        print(f"   Logs: {Color.CYAN}journalctl -u server-sldns -n 200 --no-pager{Color.END}")
    else:
        print(f"  {Color.RED}✗ Atención: uno o ambos servicios NO arrancaron.{Color.END}")
        print(f"   Revisa: {Color.CYAN}journalctl -u server-sldns -n 200 --no-pager{Color.END}")

    print("\n Fin del proceso.")
    input("\n Presiona Enter...")

# -------------------------
# STOP / UNINSTALL FLOWS
# -------------------------
def stop_flow():
    ensure_root()
    run(["systemctl", "stop", "server-sldns"], capture=True)
    run(["systemctl", "stop", "client-sldns"], capture=True)
    run(["systemctl", "disable", "server-sldns"], capture=True)
    run(["systemctl", "disable", "client-sldns"], capture=True)
    run(["pkill", "-f", "sldns-server"], capture=True)
    run(["pkill", "-f", "sldns-client"], capture=True)
    print(f"\n {Color.GREEN}✓ Servicios slowdns detenidos.{Color.END}")

def _unit_belongs_to_moratech(unit_path):
    """Devuelve True si la unit parece ser la creada por nosotros."""
    try:
        with open(unit_path, "r") as f:
            contents = f.read()
        if "MoraTech" in contents or SERVER_BIN in contents or "sldns-server" in contents:
            return True
    except Exception:
        pass
    return False

def uninstall_flow():
    ensure_root()
    # Detener servicios primero
    run(["systemctl", "stop", "server-sldns"], capture=True)
    run(["systemctl", "stop", "client-sldns"], capture=True)
    run(["systemctl", "disable", "server-sldns"], capture=True)
    run(["systemctl", "disable", "client-sldns"], capture=True)

    # matar procesos si quedan
    run(["pkill", "-f", "sldns-server"], capture=True)
    run(["pkill", "-f", "sldns-client"], capture=True)

    # lista de ficheros que queremos eliminar (solo nuestros paths)
    targets = [SERVER_BIN, CLIENT_BIN, KEY_FILE, PUB_FILE, CONFIG_FILE, LOG_FILE]
    removed = []
    skipped = []
    for p in targets:
        try:
            if p and os.path.exists(p):
                # si el fichero está en uso, lo saltamos
                in_use = False
                try:
                    # pgrep por nombre de binario
                    base = os.path.basename(p)
                    proc = subprocess.run(["pgrep", "-f", base], capture_output=True, text=True)
                    if proc.stdout.strip():
                        in_use = True
                except Exception:
                    pass
                if in_use:
                    skipped.append((p, "en uso"))
                    continue
                os.unlink(p)
                removed.append(p)
        except Exception as e:
            skipped.append((p, str(e)))

    # unidades systemd: solo eliminarlas si parecen nuestras
    units = ["/etc/systemd/system/server-sldns.service", "/etc/systemd/system/client-sldns.service"]
    for u in units:
        try:
            if os.path.exists(u):
                if _unit_belongs_to_moratech(u):
                    os.unlink(u)
                    removed.append(u)
                else:
                    skipped.append((u, "unit no parece ser de MoraTech — SKIP"))
        except Exception as e:
            skipped.append((u, str(e)))

    run(["systemctl", "daemon-reload"], capture=True)

    # reporte al usuario
    if removed:
        print(f"\n {Color.GREEN}✓ Eliminados:{Color.END}")
        for r in removed:
            print(f"   - {r}")
    if skipped:
        print(f"\n {Color.YELLOW}Archivos/units omitidos:{Color.END}")
        for s, reason in skipped:
            print(f"   - {s} ({reason})")

    print(f"\n {Color.GREEN}Uninstall (parcial/seguro) completado.{Color.END}")

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
            print(f" {Color.GREEN}6.{Color.END} Reiniciar servidor")
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
                # mostrar KEY COMPLETA (según pediste)
                print(f" {Color.CYAN}Key completa:{Color.END} {Color.YELLOW}{MASTER_PRIV}{Color.END}")
                input(f"\n{Color.CYAN}Presiona Enter para volver...{Color.END}")
                
            elif choice == "4":
                # Mostrar sólo logs NUEVOS desde el momento en que se abre el visor
                if os.path.exists("/etc/systemd/system/server-sldns.service"):
                    print(f"\n {Color.YELLOW}Abriendo journalctl -u server-sldns (solo ENTRADAS NUEVAS, Ctrl+C para salir){Color.END}\n")
                    try:
                        # -n 0 evita mostrar líneas previas, --since now asegura empezar "desde ahora"
                        run(["bash", "-c", "journalctl -u server-sldns -n 0 --no-pager -f --since \"now\""])
                    except KeyboardInterrupt:
                        pass
                elif os.path.exists(LOG_FILE):
                    print(f"\n {Color.YELLOW}Abriendo tail -f {LOG_FILE} (solo ENTRADAS NUEVAS, Ctrl+C para salir){Color.END}\n")
                    try:
                        # -n 0 --> no mostrar líneas previas, sólo nuevas
                        run(["bash", "-c", f"tail -n 0 -f {LOG_FILE}"])
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
            elif choice == "6":
                confirm = input(f"{Color.RED}¿Reiniciar ESTE SERVIDOR AHORA? (s/N): {Color.END}").strip().lower()
                if confirm == "s":
                    print(f"\n {Color.YELLOW}Reiniciando...{Color.END}")
                    run(["reboot"])
                    # si reboot falla por permiso, lo notifica y vuelve
                    time.sleep(3)
                else:
                    print(f"{Color.YELLOW}Reinicio cancelado.{Color.END}")
                    time.sleep(0.6)
            elif choice == "0":
                break
            else:
                print(f"\n{Color.RED}Opción inválida{Color.END}")
                time.sleep(0.5)

        except KeyboardInterrupt:
            break



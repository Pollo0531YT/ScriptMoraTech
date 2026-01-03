#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess
import time
import json
import shutil
from pathlib import Path
from modules.common import Color, print_line, print_banner, clear_screen

SLOW_DIR = "/etc/slowdns"
SERVER_BIN = f"{SLOW_DIR}/sldns-server"
KEY_FILE = f"{SLOW_DIR}/server.key"
CONFIG_FILE = f"{SLOW_DIR}/mora_conf.json"
LOG_FILE = f"{SLOW_DIR}/slowdns.log"

# Llave Privada Maestra (siempre puedes cambiarla)
MASTER_PRIV = "b17a4ce4c0e8cc54e33ee70b5e5a11c1a3ba853fd3743897ee091f9fcb53f0e2"

# URL por defecto para descargar el bin (raw)
SERVER_URL = "https://raw.githubusercontent.com/NevermoreSSH/hopp/main/slowdns/sldns-server"


def run_cmd(cmd, check=False, capture=False, text=True):
    """Ejecuta comando y lo muestra resumido — devuelve CompletedProcess."""
    if isinstance(cmd, list):
        disp = " ".join(cmd)
    else:
        disp = cmd
    try:
        if capture:
            return subprocess.run(cmd, check=check, capture_output=True, text=text)
        else:
            return subprocess.run(cmd, check=check)
    except subprocess.CalledProcessError as e:
        return e  # caller inspects


def save_config(ns, port):
    os.makedirs(SLOW_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'ns': ns, 'port': port}, f)


def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'ns': 'No configurado', 'port': '22'}


def ensure_dir():
    os.makedirs(SLOW_DIR, exist_ok=True)
    # asegurar permisos
    os.chmod(SLOW_DIR, 0o700)


def download_server_bin(url=SERVER_URL):
    ensure_dir()
    # usar curl o wget de forma silenciosa
    tmp = f"{SERVER_BIN}.tmp"
    # eliminar tmp previo
    if os.path.exists(tmp):
        os.unlink(tmp)
    print(f"  ➜ Descargando binario desde {url} ...")
    # prefer curl, sino wget
    if shutil.which("curl"):
        r = run_cmd(["curl", "-fsSL", "-o", tmp, url], capture=True)
    else:
        r = run_cmd(["wget", "-q", "-O", tmp, url], capture=True)
    # comprobar
    if isinstance(r, subprocess.CalledProcessError) or not os.path.exists(tmp) or os.path.getsize(tmp) == 0:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise RuntimeError("Fallo al descargar el binario. Revisa URL o conexión.")
    # mover y chmod
    shutil.move(tmp, SERVER_BIN)
    os.chmod(SERVER_BIN, 0o755)
    print("  ✓ Binario descargado y marcado como ejecutable.")


def safe_edit_sshd_config():
    cfg = "/etc/ssh/sshd_config"
    if not os.path.exists(cfg):
        print("  ⚠ sshd_config no encontrado, omitiendo cambios.")
        return
    bak = f"{cfg}.moratech.bak"
    if not os.path.exists(bak):
        shutil.copy(cfg, bak)
    # eliminar líneas que puedan duplicarse
    run_cmd(["sed", "-i", "/^ListenAddress\\b/d", cfg])
    run_cmd(["sed", "-i", "/^PermitRootLogin\\b/d", cfg])
    # añadir PermitRootLogin yes si no existe
    with open(cfg, "a") as f:
        f.write("\nPermitRootLogin yes\n")
    run_cmd(["service", "ssh", "restart"])


def iptables_add_once(rule_list):
    """rule_list = list de listas (cada una es un comando iptables completo)"""
    for cmd in rule_list:
        # comprobar si la regla ya existe (simplista)
        check = run_cmd(["iptables", "-C"] + cmd[1:], capture=True)
        if isinstance(check, subprocess.CalledProcessError):
            # no existe -> añadir
            run_cmd(["iptables"] + cmd[1:])
        else:
            # ya existe
            pass


def install_slowdns():
    clear_screen()
    print_banner()
    ensure_dir()

    print(f"\n {Color.YELLOW}Limpiando procesos y puertos (si existen)...{Color.END}")
    run_cmd(["pkill", "-f", "sldns-server"])
    run_cmd(["fuser", "-k", "53/udp"], capture=True)
    run_cmd(["fuser", "-k", "5300/udp"], capture=True)

    # Guardar llave privada (con permisos 600)
    with open(KEY_FILE, "w") as f:
        f.write(MASTER_PRIV)
    os.chmod(KEY_FILE, 0o600)
    print("  ✓ Llave privada escrita correctamente.")

    # descargar bin si no existe
    try:
        if not os.path.exists(SERVER_BIN) or os.path.getsize(SERVER_BIN) == 0:
            download_server_bin()
        else:
            print("  ✓ Binario sldns-server ya existe, verificando ejecutable...")
            if not os.access(SERVER_BIN, os.X_OK):
                os.chmod(SERVER_BIN, 0o755)
    except Exception as e:
        print(f"\n {Color.RED}✗ Error: {e}{Color.END}")
        print("  -> Revisa la URL o la conectividad. No se continúa.")
        input("\nPresiona Enter...")
        return

    # Limpiar reglas iptables NAT solo relacionadas con DNS/5300 para no tocar todo
    print(f"\n {Color.CYAN}Configurando reglas iptables (solo las necesarias)...{Color.END}")
    # Asegurarse de que loopback está permitido
    run_cmd(["iptables", "-C", "INPUT", "-i", "lo", "-j", "ACCEPT"], capture=True)
    run_cmd(["iptables", "-A", "INPUT", "-i", "lo", "-j", "ACCEPT"])
    run_cmd(["iptables", "-C", "OUTPUT", "-o", "lo", "-j", "ACCEPT"], capture=True)
    run_cmd(["iptables", "-A", "OUTPUT", "-o", "lo", "-j", "ACCEPT"])

    # reglas que queremos (si no existen)
    # aceptar 5300/udp
    run_cmd(["iptables", "-C", "INPUT", "-p", "udp", "--dport", "5300", "-j", "ACCEPT"], capture=True)
    run_cmd(["iptables", "-A", "INPUT", "-p", "udp", "--dport", "5300", "-j", "ACCEPT"])
    # Prerouting: REDIRECT 53 -> 5300 (solo si no está)
    # Comprobar existencia aproximada buscando la regla en iptables-save
    ipt_save = run_cmd(["iptables-save"], capture=True)
    if isinstance(ipt_save, subprocess.CalledProcessError):
        ipt_txt = ""
    else:
        ipt_txt = ipt_save.stdout
    if "--to-ports 5300" not in ipt_txt:
        run_cmd(["iptables", "-t", "nat", "-A", "PREROUTING", "-p", "udp", "--dport", "53", "-j", "REDIRECT", "--to-ports", "5300"])

    # Reiniciar/ajustar SSH (backup antes)
    print(f"\n {Color.YELLOW}Sincronizando SSH (se hará backup de sshd_config)...{Color.END}")
    ssh_cfg = "/etc/ssh/sshd_config"
    if os.path.exists(ssh_cfg):
        shutil.copy(ssh_cfg, f"{ssh_cfg}.moratech.preinst")
    safe_edit_sshd_config()

    # Pedir NS y puerto local
    ns_domain = input(f"\n {Color.GREEN}Ingresa tu NS Domain: {Color.END}").strip()
    if not ns_domain:
        print(f" {Color.RED}✗ NS no puede estar vacío{Color.END}")
        input("\nPresiona Enter...")
        return
    l_port = input(f" {Color.GREEN}Puerto SSH local (ej 22): {Color.END}").strip() or "22"

    # crear log file
    open(LOG_FILE, "a").close()
    os.chmod(LOG_FILE, 0o600)

    # comando con salida a log, en screen
    cmd = f"{SERVER_BIN} -udp :5300 -privkey-file {KEY_FILE} {ns_domain} 127.0.0.1:{l_port} >> {LOG_FILE} 2>&1"
    # iniciar screen en background
    print(f"\n {Color.YELLOW}Iniciando slowdns en background (screen -> slowdns)...{Color.END}")
    # usar bash -c para redirección
    run_cmd(["screen", "-S", "slowdns", "-dm", "bash", "-c", cmd])
    time.sleep(2)

    # comprobar si proceso está arriba
    check = run_cmd(["pgrep", "-f", "sldns-server"], capture=True)
    if check and check.stdout.strip():
        print(f"\n {Color.GREEN}✓ slowdns iniciado en screen y registrando en {LOG_FILE}{Color.END}")
        save_config(ns_domain, l_port)
        print("  -> Para ver logs: tail -n 200 /etc/slowdns/slowdns.log")
    else:
        print(f"\n {Color.RED}✗ No se detectó el proceso sldns-server tras el intento de inicio.{Color.END}")
        print("  -> Revisa el log: less /etc/slowdns/slowdns.log")
        print("  -> Prueba ejecutar el binario manualmente y ver el error:")
        print(f"     {SERVER_BIN} -udp :5300 -privkey-file {KEY_FILE} {ns_domain} 127.0.0.1:{l_port}")
    time.sleep(1)
    input("\nPresiona Enter...")


def menu_slowdns():
    while True:
        clear_screen()
        print_banner()
        check = run_cmd(["pgrep", "-f", "sldns-server"], capture=True)
        status = f"{Color.GREEN}ACTIVO{Color.END}" if check and check.stdout.strip() else f"{Color.RED}INACTIVO{Color.END}"
        print(f" PANEL SLOWDNS MORATECH | ESTADO: {status}")
        print_line()
        print(" [1] Instalar / Iniciar (Modo Espejo)")
        print(" [2] Detener")
        print(" [3] Ver Info")
        print(" [4] Ver Logs (tail -f)")
        print(" [0] Volver")
        op = input("\n ► Opcion : ").strip()
        if op == '1':
            install_slowdns()
        elif op == '2':
            run_cmd(["pkill", "-f", "sldns-server"])
            run_cmd(["screen", "-S", "slowdns", "-X", "quit"])
            print("\n Detenido.")
            input("\nPresiona Enter...")
        elif op == '3':
            conf = get_config()
            print(f"\n NS: {conf.get('ns')}")
            print(f" Key: {MASTER_PRIV[:30]}...")  # no mostrar todo si no quieres
            print(f" Puerto Local: {conf.get('port')}")
            input("\nPresiona Enter...")
        elif op == '4':
            # abrir tail en pantalla (intento de usar 'less' si no head)
            try:
                run_cmd(["bash", "-c", f"tail -n 200 -f {LOG_FILE}"], check=False)
            except KeyboardInterrupt:
                pass
        elif op == '0':
            break

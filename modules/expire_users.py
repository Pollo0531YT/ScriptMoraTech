#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime
from pathlib import Path
import fcntl
import tempfile
import os
import sys
import traceback

# --- USAR RUTAS ABSOLUTAS SIEMPRE ---
# Ajusta '/root/.moratech' a la ruta REAL donde está tu carpeta .moratech
CONFIG_DIR = Path('/root/.moratech') 
USERS_FILE = CONFIG_DIR / 'users.json'
EXPIRE_LOG_FILE = CONFIG_DIR / 'expire.log'
LOCK_FILE = CONFIG_DIR / 'expire.lock'

def log_expire(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(EXPIRE_LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        print(f"[{timestamp}] {message}")

class FileLock:
    def __init__(self, path: Path):
        self.path = path
        self.fd = None
    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fd = open(self.path, 'w')
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return self
        except BlockingIOError:
            raise RuntimeError("Proceso ya en ejecucion")
    def __exit__(self, exc_type, exc, tb):
        try:
            if self.fd:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
                self.fd.close()
        except Exception: pass

def _atomic_write_json(path: Path, data):
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, indent=4)
        os.replace(tmp, str(path))
    except Exception:
        if os.path.exists(tmp): os.unlink(tmp)
        raise

def expire_users():
    """Solo bloquea y desconecta (NO borra de Linux)"""
    try:
        with FileLock(LOCK_FILE):
            log_expire("=== INICIO VERIFICACION ===")

            if not USERS_FILE.exists():
                log_expire(f"Error: No se encontro {USERS_FILE}")
                return 0

            with open(USERS_FILE, 'r') as f:
                users = json.load(f)

            now = datetime.now()
            expired_count = 0
            changed = False

            for username, data in list(users.items()):
                if username == "admin": continue
                
                expires = data.get('expires')
                if not expires: continue

                try:
                    expire_date = datetime.fromisoformat(expires)
                except: continue

                # Si ya paso la hora de expiracion
                if now >= expire_date and data.get('enabled', True):
                    # 1. BLOQUEAR CONTRASEÑA
                    subprocess.run(['usermod', '-L', username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    # 2. DESCONECTAR (KILL AGRESIVO)
                    subprocess.run(['pkill', '-9', '-u', username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    # 3. MARCAR EN JSON
                    users[username]['enabled'] = False
                    expired_count += 1
                    changed = True
                    log_expire(f"X EXPIRADO: {username}")

            if changed:
                _atomic_write_json(USERS_FILE, users)
                log_expire(f"Se procesaron {expired_count} usuarios.")
            else:
                log_expire("Nada que expirar.")

    except Exception as e:
        log_expire(f"ERROR: {str(e)}")

if __name__ == '__main__':
    expire_users()
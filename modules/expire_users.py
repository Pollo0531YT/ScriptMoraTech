#!/usr/bin/env python3
"""
Sistema de expiración automática de usuarios
Se ejecuta diariamente a las 18:00 para bloquear usuarios expirados.
Bloquea la cuenta con `usermod -L`, mata conexiones con `pkill -u` y marca enabled=False en users.json.
Añade locking por fichero para evitar solapamientos.
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path
import fcntl
import tempfile
import os
import sys
import traceback

# Usar la misma carpeta que init_system (Path.home()/.moratech)
CONFIG_DIR = Path.home() / '.moratech'
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
        # fallback to stdout if logging file not writable
        print(f"[{timestamp}] {message}")

class FileLock:
    """Lock simple usando fcntl sobre un fichero."""
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
            raise RuntimeError("Otro proceso de expiración ya está corriendo")

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.fd:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
                self.fd.close()
        except Exception:
            pass

def _atomic_write_json(path: Path, data):
    """Escribe JSON de forma atómica (temp -> move)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, indent=4)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise

def expire_users():
    """Bloquear y desconectar usuarios expirados"""
    try:
        with FileLock(LOCK_FILE):
            log_expire("=== Iniciando verificación de expiración ===")

            if not USERS_FILE.exists():
                log_expire("No existe users.json, nothing to do.")
                return 0

            with open(USERS_FILE, 'r') as f:
                users = json.load(f)

            now = datetime.now()
            expired_count = 0
            changed = False

            for username, data in list(users.items()):
                expires = data.get('expires')
                if not expires:
                    continue  # Usuario sin expiración

                try:
                    expire_date = datetime.fromisoformat(expires)
                except Exception:
                    log_expire(f"Formato inválido de expires para {username}: {expires}")
                    continue

                if now >= expire_date:
                    user_type = data.get('type', 'ssh')
                    display_name = data.get('display_name', username) if user_type == 'token' else username

                    # 1) Intentar bloquear la cuenta (usermod -L)
                    try:
                        r = subprocess.run(['usermod', '-L', username],
                                           capture_output=True, text=True)
                        if r.returncode == 0:
                            log_expire(f"✓ Cuenta bloqueada: {display_name} ({username})")
                        else:
                            # Si falla, lo registramos (puede fallar si el usuario no existe en /etc/passwd)
                            log_expire(f"✗ Error al bloquear {display_name}: {r.stderr.strip()}")
                    except Exception as e:
                        log_expire(f"✗ Excepción al ejecutar usermod para {username}: {e}")

                    # 2) Matar conexiones
                    try:
                        kr = subprocess.run(['pkill', '-u', username],
                                            capture_output=True, text=True)
                        # pkill devuelve 1 si no encontró procesos; no siempre es error
                        if kr.returncode == 0:
                            log_expire(f"✓ Conexiones cerradas: {display_name}")
                        else:
                            log_expire(f"ℹ pkill para {username} terminó con código {kr.returncode}")
                    except Exception as e:
                        log_expire(f"✗ Error matando procesos de {username}: {e}")

                    # 3) Marcar como deshabilitado en JSON
                    if users.get(username, {}).get('enabled', True):
                        users[username]['enabled'] = False
                        changed = True
                    expired_count += 1

            # Guardar cambios si hubo alguno
            if changed:
                _atomic_write_json(USERS_FILE, users)
                log_expire("Usuarios actualizados en users.json")

            log_expire(f"=== Verificación completada: {expired_count} usuarios expirados ===")
            return expired_count

    except RuntimeError as re:
        log_expire(f"✗ Saltado: {re}")
        return 0
    except Exception as e:
        log_expire(f"✗ Error crítico en expire_users: {e}")
        log_expire(traceback.format_exc())
        return 0

if __name__ == '__main__':
    exit(expire_users() or 0)

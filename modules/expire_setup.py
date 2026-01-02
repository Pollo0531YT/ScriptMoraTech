#!/usr/bin/env python3
"""
Configuración del sistema de expiración automática
Se encarga de crear el wrapper /usr/local/bin/moratech-expire y registrar cron.
"""
import os
import stat
import subprocess
from pathlib import Path
import textwrap
import sys
import shutil

MODULE_DIR = Path(__file__).resolve().parent
# Asumimos que expire_users.py está en el mismo folder (modules)
EXPIRE_SCRIPT_MODULE = MODULE_DIR / 'expire_users.py'
WRAPPER_PATH = Path('/usr/local/bin/moratech-expire')
CRON_FILE = Path('/etc/cron.d/moratech-expire')
LOCK_PATH = Path('/var/lock/moratech-expire.lock')
LOG_PATH = Path('/var/log/moratech-expire.log')

def _is_root():
    try:
        return os.geteuid() == 0
    except AttributeError:
        # Windows fallback (no need aquí, pero por completitud)
        return False

def _write_wrapper(script_target: Path):
    """Escribe el wrapper bash que usa flock y ejecuta expire_users.py con rutas absolutas."""
    python_bin = shutil.which('python3') or '/usr/bin/python3'
    wrapper_content = textwrap.dedent(f"""\
        #!/usr/bin/env bash
        # morat ech-expire - wrapper seguro que ejecuta expire_users.py con locking y logging
        set -euo pipefail

        PYTHON={python_bin}
        SCRIPT="{script_target}"
        LOCK="{LOCK_PATH}"
        LOG="{LOG_PATH}"

        mkdir -p "$(dirname "$LOCK")" "$(dirname "$LOG")"

        # usar flock para evitar solapamientos
        /usr/bin/flock -n "$LOCK" -c '
          echo "==== Ejecutando moratech-expire: $(date \"+%Y-%m-%d %H:%M:%S\") ====" >> "$LOG"
          if [ -x "$PYTHON" ] && [ -f "$SCRIPT" ]; then
            cd "{script_target.parent}"
            "$PYTHON" "$SCRIPT" >> "$LOG" 2>&1 || echo "expire_users.py falló (exit $? )" >> "$LOG"
          else
            echo "Error: python o script no encontrado (PYTHON=$PYTHON, SCRIPT=$SCRIPT)" >> "$LOG"
          fi
          echo "==== Fin: $(date \"+%Y-%m-%d %H:%M:%S\") ====" >> "$LOG"
        '
    """)
    WRAPPER_PATH.write_text(wrapper_content)
    # establecer permisos y propietario root
    WRAPPER_PATH.chmod(0o755)

def _install_cron_as_root():
    """Escribe /etc/cron.d entry para root a las 18:00"""
    cron_text = textwrap.dedent(f"""\
        # MORATECH - Expiración automática de usuarios a las 18:00
        # Ejecutado como root
        0 18 * * * root {WRAPPER_PATH}
    """)
    CRON_FILE.write_text(cron_text)
    CRON_FILE.chmod(0o644)

def _install_cron_user(user_wrapper_path: Path, user_log_path: Path):
    """Agrega entry en crontab del usuario actual (si no es root)."""
    # entrada de cron con redirección de logs
    entry = f"0 18 * * * {user_wrapper_path} >> {user_log_path} 2>&1\n"
    try:
        proc = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        existing = proc.stdout if proc.returncode == 0 else ''
        if 'moratech-expire' in existing:
            return True  # ya está
        new_cron = existing + "\n# MORATECH - Expiración automática de usuarios a las 18:00\n" + entry
        p = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
        p.communicate(new_cron)
        return p.returncode == 0
    except Exception:
        return False

def setup_expire_system():
    """
    Configura expiración:
    - Crea wrapper en /usr/local/bin (si se puede)
    - Crea /etc/cron.d/moratech-expire si es root
    - Si NO es root: crea wrapper en ~/.moratech/ y agrega crontab de usuario (best-effort)
    """
    try:
        if not EXPIRE_SCRIPT_MODULE.exists():
            print(f"⚠️  expire_users.py no encontrado en {EXPIRE_SCRIPT_MODULE}. No se configurará cron.")
            return False

        if _is_root():
            # crear wrapper global
            _write_wrapper(EXPIRE_SCRIPT_MODULE)
            _install_cron_as_root()
            print("✓ Script de expiración creado en /usr/local/bin/moratech-expire")
            print("✓ Cron instalado en /etc/cron.d/moratech-expire (ejecución diaria a las 18:00 como root)")
        else:
            # user-level fallback: crear wrapper en ~/.moratech/moratech-expire
            user_home = Path.home()
            user_conf = user_home / '.moratech'
            user_conf.mkdir(parents=True, exist_ok=True)
            user_wrapper = user_conf / 'moratech-expire'
            user_log = user_conf / 'expire.log'
            user_wrapper_content = textwrap.dedent(f"""\
                #!/usr/bin/env bash
                PYTHON="{shutil.which('python3') or '/usr/bin/python3'}"
                SCRIPT="{EXPIRE_SCRIPT_MODULE}"
                LOG="{user_log}"
                /usr/bin/flock -n "{user_conf}/moratech-expire.lock" -c '$PYTHON "$SCRIPT" >> "$LOG" 2>&1'
            """)
            user_wrapper.write_text(user_wrapper_content)
            user_wrapper.chmod(0o750)
            ok = _install_cron_user(user_wrapper, user_log)
            if ok:
                print(f"✓ Wrapper instalado en {user_wrapper}")
                print("✓ Entry agregado a crontab del usuario actual (ejecución diaria a las 18:00).")
                print("⚠️ Nota: Para que expire_users.py pueda eliminar cuentas del sistema se requiere ejecutar como root.")
            else:
                print("⚠️ No se pudo agregar la entrada al crontab del usuario. Verifica `crontab -l`.")
        return True
    except Exception as e:
        print(f"⚠️ Advertencia: No se pudo configurar expiración automática: {e}")
        return False

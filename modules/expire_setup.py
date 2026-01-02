#!/usr/bin/env python3
"""
expire_setup.py

Configura el wrapper `moratech-expire` y el job en /etc/cron.d para ejecutar
/usr/local/lib/moratech/modules/expire_users.py diariamente a las 18:00.
Idempotente: puede ejecutarse varias veces sin romper nada.
"""
from pathlib import Path
import os
import stat
import textwrap
import shutil
import subprocess
import sys

EXPIRE_SCRIPT_PATH = Path("/usr/local/bin/moratech-expire")
CRON_FILE_PATH = Path("/etc/cron.d/moratech-expire")
MODULES_DIR = Path("/usr/local/lib/moratech/modules")
SCRIPT_TARGET = MODULES_DIR / "expire_users.py"

SCRIPT_CONTENT = textwrap.dedent("""\
    #!/usr/bin/env bash
    # moratech-expire - wrapper seguro que ejecuta expire_users.py con locking y logging
    set -euo pipefail

    PYTHON=$(command -v python3 || echo "/usr/bin/python3")
    SCRIPT="/usr/local/lib/moratech/modules/expire_users.py"
    LOCK="/var/lock/moratech-expire.lock"
    LOG="/var/log/moratech-expire.log"

    # asegurar directorios
    mkdir -p "$(dirname "$LOCK")" "$(dirname "$LOG")"
    touch "$LOG" 2>/dev/null || true
    chown root:root "$(dirname "$LOCK")" "$(dirname "$LOG")" 2>/dev/null || true
    chown root:root "$LOG" 2>/dev/null || true
    chmod 600 "$LOG" 2>/dev/null || true

    # Abrir descriptor 9 sobre el archivo lock y usar flock sobre ese FD para ejecutar en este shell
    exec 9>"$LOCK"
    if /usr/bin/flock -n 9; then
      {
        echo "==== Ejecutando moratech-expire: $(date "+%Y-%m-%d %H:%M:%S") ===="
        if [ -x "$PYTHON" ] && [ -f "$SCRIPT" ]; then
          cd "/usr/local/lib/moratech/modules" || { echo "No existe directorio modules"; exit 1; }
          "$PYTHON" "$SCRIPT" >> "$LOG" 2>&1 || echo "expire_users.py falló (exit $? )" >> "$LOG"
        else
          echo "Error: python o script no encontrado (PYTHON=$PYTHON, SCRIPT=$SCRIPT)" >> "$LOG"
        fi
        echo "==== Fin: $(date "+%Y-%m-%d %H:%M:%S") ===="
      } >> "$LOG" 2>&1
      /usr/bin/flock -u 9
    else
      echo "Otro proceso de expire en ejecución, saliendo." >> "$LOG"
    fi
    """)

CRON_CONTENT = textwrap.dedent("""\
    # MORATECH - Expiración automática de usuarios a las 18:00
    # Ejecutado como root
    0 18 * * * root /usr/local/bin/moratech-expire
    """)


def write_file(path: Path, content: str, mode: int = 0o755, as_root: bool = True):
    """Escribe contenido en path asegurando newline UNIX y permisos."""
    # Asegurar directorio
    path.parent.mkdir(parents=True, exist_ok=True)
    # Escribir con newline unix
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    os.chmod(path, mode)


def setup_expire_system():
    """Crea/actualiza el script y el cron. Devuelve True si ok."""
    try:
        # 1) Verificar que el módulo expire_users.py exista (si no existe, avisar pero continuar)
        if not SCRIPT_TARGET.exists():
            print(f"[WARN] {SCRIPT_TARGET} no existe. El script se creará, pero expire_users.py debe existir en esa ruta para que funcione.")
            # No fallamos aquí; el instalador puede copiar expire_users.py después.

        # 2) Escribir el wrapper en /usr/local/bin/moratech-expire
        write_file(EXPIRE_SCRIPT_PATH, SCRIPT_CONTENT, mode=0o755)
        print(f"✓ Script escrito: {EXPIRE_SCRIPT_PATH}")

        # 3) Asegurar owner/perm (root)
        try:
            os.chown(EXPIRE_SCRIPT_PATH, 0, 0)
        except PermissionError:
            pass  # si no somos root, no podemos cambiar owner aquí

        # 4) Escribir cron file en /etc/cron.d (idempotente)
        write_file(CRON_FILE_PATH, CRON_CONTENT, mode=0o644)
        print(f"✓ Cron file escrito: {CRON_FILE_PATH}")

        # 5) Asegurar owner/perm del cron
        try:
            os.chown(CRON_FILE_PATH, 0, 0)
        except PermissionError:
            pass

        # 6) Recargar cron (si systemd presente)
        if shutil.which("systemctl"):
            try:
                subprocess.run(["systemctl", "reload", "cron"], check=False)
            except Exception:
                # fallback: restart
                try:
                    subprocess.run(["systemctl", "restart", "cron"], check=False)
                except Exception:
                    pass

        print("✓ Intentada recarga/restart de cron (si aplica).")

        # 7) Mensaje final
        print("OK — setup_expire_system completado.")
        return True

    except Exception as e:
        print(f"ERROR: No se pudo configurar expiración automática: {e}")
        return False


if __name__ == "__main__":
    # Si llamás directo: ejecuta la configuración
    ok = setup_expire_system()
    if not ok:
        sys.exit(2)

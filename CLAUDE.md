# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este proyecto

**MORATECH** es un panel de administración VPS para Ubuntu en terminal (sin navegador). Gestiona usuarios SSH, tokens de acceso, y protocolos de tunneling (SSL/Stunnel, Proxy Python, V2Ray, SlowDNS, BadVPN). También expone una API REST Flask y un bot de Telegram.

Target: servidores Ubuntu con acceso root.

## Cómo ejecutar

```bash
# Desarrollo directo (desde el repo):
sudo python3 moratech.py

# Después de instalar:
sudo moratech

# Instalación en el sistema:
sudo ./install.sh
# Instala en /usr/local/lib/moratech/ y crea /usr/local/bin/moratech
```

No hay tests automatizados ni linter configurado. Las pruebas son manuales en el VPS.

## Arquitectura

### Flujo principal
`moratech.py` → `main()` → `init_system()` → `main_menu()` → submenús en módulos

El dashboard (`show_dashboard`) detecta automáticamente qué protocolos están activos usando `ss -tulpn` y `pgrep` en tiempo real — no confiar en `protocols.json` para el estado visual.

### Módulos (`modules/`)

| Módulo | Responsabilidad |
|--------|----------------|
| `common.py` | `Color`, `CONFIG_DIR`, `PROTOCOLS_FILE`, `clear_screen`, `print_line`, `print_banner` — importado por todos los demás |
| `users.py` | Gestión completa de usuarios SSH y token: CRUD, expiración, conexiones activas, backup, API individual/master, bot Telegram, checkuser |
| `phyton.py` | Proxy Python (Python 2) via `screen -dmS pythonwe`. Instala/detiene proxy en puerto configurable |
| `ssl_protocol.py` | Stunnel SSL/TLS — lee `/etc/stunnel/stunnel.conf` para detectar estado |
| `v2ray.py` | V2Ray/3X-UI — verifica via `systemctl is-active x-ui` |
| `badvpn.py` | BadVPN UDP Gateway — detectado en `127.0.0.1:<puerto>` |
| `slowdns.py` | SlowDNS — detectado en puerto 5300 |
| `extras.py` | Herramientas adicionales |
| `api_server.py` | Flask REST API con autenticación por `X-Auth-Key` header o sesión web. Corre en segundo plano |
| `api_general.py` | API master |
| `telegram_bot.py` | Bot de Telegram para gestión remota de usuarios |
| `checkuser_flask.py` | Servicio web para verificar conexiones de usuarios |
| `activaciones.py` | Registro de activaciones |
| `proxy_template.py` | Template del script `proxy.py` que se escribe en `/root/proxy.py` |

### Almacenamiento (`~/.moratech/`)
Todos los datos en JSON, escrituras atómicas via `atomic_write()` (escribe a `.tmp` y luego `os.replace`):
- `users.json` — usuarios SSH y token
- `config.json` — configuración general
- `logs.json` — auditoría de acciones
- `token_config.json` — contraseña maestra de tokens
- `connections.json` — conexiones activas
- `protocols.json` — estado de protocolos (usado para persistencia, no para detección en vivo)
- `api.log` — log de peticiones API (formato JSONL)

### Timezone
`CR_TZ = timezone(timedelta(hours=-6))` — Costa Rica (UTC-6, sin DST)

### Importación circular
`users.py` importa `moratech` (para `log_action`, `configure_forwarding`, etc.) y `moratech.py` importa `users`. Esto funciona porque `install.sh` ejecuta desde `/usr/local/lib/moratech/` donde `moratech.py` está en el path. En desarrollo directo también funciona porque Python resuelve el módulo al ejecutar desde el directorio raíz.

### Patrón de módulo de protocolo
Cada módulo de protocolo sigue el patrón:
1. Detectar estado actual con `ss -tulpn` + `pgrep`
2. Mostrar menú con opciones según estado detectado
3. Instalar: verificar puerto, instalar dependencias con `apt-get`, iniciar servicio, abrir con `iptables` + `ufw`, guardar en `protocols.json`
4. Detener: `pkill`, limpiar `iptables`, actualizar `protocols.json`

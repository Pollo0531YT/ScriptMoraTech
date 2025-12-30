# 🚀 MORATECH - Panel de Administración para Ubuntu

![Version](https://img.shields.io/badge/version-1.0-purple)
![Python](https://img.shields.io/badge/python-3.6+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Panel de administración completo para Ubuntu directamente desde la terminal. Sin necesidad de navegador web, todo funciona en consola.

```
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║    ███╗   ███╗ ██████╗ ██████╗  █████╗ ████████╗███████╗║
║    ████╗ ████║██╔═══██╗██╔══██╗██╔══██╗╚══██╔══╝██╔════╝║
║    ██╔████╔██║██║   ██║██████╔╝███████║   ██║   █████╗  ║
║    ██║╚██╔╝██║██║   ██║██╔══██╗██╔══██║   ██║   ██╔══╝  ║
║    ██║ ╚═╝ ██║╚██████╔╝██║  ██║██║  ██║   ██║   ███████╗║
║    ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝║
║                                                          ║
║              Panel de Administración v1.0                ║
╚══════════════════════════════════════════════════════════╝
```

## ✨ Características

- 🔐 **Sistema de autenticación** con roles (admin, superadmin, user)
- 👥 **Gestión de usuarios** - Crear, eliminar y modificar usuarios
- 🎫 **Usuarios Token** - Sistema de tokens con contraseña maestra
- 👤 **Usuarios Regulares** - Con nombre de usuario y contraseña personalizada
- ⏰ **Expiración de cuentas** - Configuración de días de duración
- 🔌 **Control de conexiones** - Límite de conexiones simultáneas por usuario
- 📊 **Información del sistema** - CPU, RAM, Disco, Uptime
- 🛠️ **Gestión de servicios** - Monitoreo de nginx, apache2, mysql, etc.
- 📝 **Sistema de logs** - Registro de todas las acciones
- 👁️ **Conexiones activas** - Monitoreo en tiempo real de usuarios conectados
- 🎨 **Interfaz colorida** - Diseño atractivo en terminal
- 🔒 **Seguro** - Contraseñas hasheadas con SHA256

## 📋 Requisitos

- Ubuntu 18.04 o superior
- Python 3.6 o superior
- Acceso sudo

## 🚀 Instalación

### Opción 1: Instalación desde GitHub (Recomendada)

```bash
# 1. Clonar el repositorio
git clone https://github.com/tuusuario/moratech.git

# 2. Entrar al directorio
cd moratech

# 3. Dar permisos de ejecución al instalador
chmod +x install.sh

# 4. Ejecutar el instalador
sudo ./install.sh
```

### Opción 2: Instalación Manual

```bash
# 1. Descargar el archivo moratech.py
wget https://raw.githubusercontent.com/tuusuario/moratech/main/moratech.py

# 2. Copiar a /usr/local/bin
sudo cp moratech.py /usr/local/bin/moratech

# 3. Dar permisos de ejecución
sudo chmod +x /usr/local/bin/moratech
```

## 🎯 Uso

Una vez instalado, simplemente escribe en tu terminal:

```bash
moratech
```

### Credenciales por Defecto

```
Usuario: admin
Contraseña: admin123
```

**⚠️ IMPORTANTE:** Cambia la contraseña inmediatamente después del primer login.

## 📖 Funcionalidades

### 1. Información del Sistema
Muestra información completa del servidor:
- Hostname
- Uptime
- Uso de memoria RAM
- Espacio en disco
- Y más...

### 2. Gestión de Usuarios

#### Usuario Regular
Cuando creas un usuario regular, el sistema te pedirá:
- **Nombre de usuario**: El nombre con el que iniciará sesión
- **Contraseña**: Contraseña personalizada
- **Días de duración**: Cuántos días será válida la cuenta (0 = sin expiración)
- **Máximas conexiones**: Número de sesiones simultáneas permitidas

#### Usuario Token
Sistema especial para acceso mediante tokens:

1. **Primera vez (Configuración)**:
   - Debes configurar una contraseña maestra para tokens
   - Esta contraseña será compartida por todos los usuarios token

2. **Crear usuario token**:
   - Ingresas el token
   - El sistema genera automáticamente un username (token_XXXXXXXX)
   - Defines los días de duración
   - Máxima 1 conexión simultánea (fijo)

3. **Login con token**:
   - Username: El generado por el sistema (token_XXXXXXXX)
   - Contraseña: La contraseña maestra de tokens

**Ventajas de usuarios token:**
- No necesitas recordar username específico
- Todos comparten la misma contraseña
- Ideal para accesos temporales
- Control estricto (1 conexión)

### 3. Gestión de Servicios
Monitorea el estado de servicios comunes:
- nginx
- apache2
- mysql
- postgresql
- ssh
- docker

### 4. Ver Logs
Sistema completo de auditoría que registra:
- Inicios de sesión
- Acciones de usuarios
- Cambios en el sistema
- Intentos fallidos de login

### 5. Conexiones Activas
Monitoreo en tiempo real:
- Ver usuarios conectados
- Número de conexiones por usuario
- Tipo de usuario (regular/token)
- Límite de conexiones

## 🔐 Sistema de Seguridad

- **Control de expiración**: Las cuentas expiran automáticamente
- **Límite de conexiones**: Previene uso indebido de cuentas
- **Contraseñas hasheadas**: SHA256, no se almacenan en texto plano
- **Máximo 3 intentos**: Protección contra fuerza bruta
- **Sistema de tokens**: Acceso controlado con contraseña maestra
- **Registro completo**: Auditoría de todas las acciones
- **Habilitación/Deshabilitación**: Control de acceso sin eliminar usuarios

## 📁 Estructura de Archivos

```
~/.moratech/
├── config.json         # Configuración del sistema
├── users.json          # Base de datos de usuarios
├── logs.json           # Registro de acciones
├── services.json       # Servicios monitoreados
├── token_config.json   # Configuración de tokens
└── connections.json    # Conexiones activas
```

## 🔒 Seguridad Adicional

- Contraseñas hasheadas con SHA256
- Máximo 3 intentos de login
- Sistema de roles y permisos
- Registro completo de auditoría
- No almacena contraseñas en texto plano

## 🛠️ Desinstalación

```bash
# Eliminar el ejecutable
sudo rm /usr/local/bin/moratech

# Eliminar archivos de configuración (opcional)
rm -rf ~/.moratech
```

## 🔄 Actualización

```bash
cd moratech
git pull
sudo ./install.sh
```

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/NuevaCaracteristica`)
3. Commit tus cambios (`git commit -am 'Agrega nueva característica'`)
4. Push a la rama (`git push origin feature/NuevaCaracteristica`)
5. Abre un Pull Request

## 📝 Roadmap

- [ ] Backup automático
- [ ] Gestión de bases de datos
- [ ] Monitoreo de recursos en tiempo real
- [ ] Alertas por email
- [ ] Integración con Docker
- [ ] API REST
- [ ] Gestión de cronjobs

## 🐛 Reportar Bugs

Si encuentras algún bug, por favor abre un issue en GitHub con:
- Descripción del problema
- Pasos para reproducirlo
- Sistema operativo y versión
- Logs relevantes

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 👨‍💻 Autor

Creado con ❤️ por [Tu Nombre]

## 📧 Contacto

- GitHub: [@tuusuario](https://github.com/tuusuario)
- Email: tu@email.com

---

**⭐ Si te gusta este proyecto, dale una estrella en GitHub!**
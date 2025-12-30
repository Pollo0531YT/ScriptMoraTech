#!/bin/bash

# MORATECH - Instalador para Ubuntu
# Este script instala Moratech en tu sistema Ubuntu

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}"
cat << "EOF"
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║    ███╗   ███╗ ██████╗ ██████╗  █████╗ ████████╗███████╗║
║    ████╗ ████║██╔═══██╗██╔══██╗██╔══██╗╚══██╔══╝██╔════╝║
║    ██╔████╔██║██║   ██║██████╔╝███████║   ██║   █████╗  ║
║    ██║╚██╔╝██║██║   ██║██╔══██╗██╔══██║   ██║   ██╔══╝  ║
║    ██║ ╚═╝ ██║╚██████╔╝██║  ██║██║  ██║   ██║   ███████╗║
║    ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝║
║                                                          ║
║                    INSTALADOR v1.0                       ║
╚══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Verificar si se ejecuta como root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Por favor ejecuta este script con sudo${NC}"
    exit 1
fi

echo -e "${GREEN}Iniciando instalación de Moratech...${NC}\n"

# 1. Verificar Python3
echo -e "${YELLOW}[1/5] Verificando Python3...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 no está instalado. Instalando...${NC}"
    apt-get update
    apt-get install -y python3 python3-pip
else
    echo -e "${GREEN}✓ Python3 ya está instalado${NC}"
fi

# 2. Copiar el script principal
echo -e "${YELLOW}[2/5] Copiando archivos del sistema...${NC}"
INSTALL_DIR="/usr/local/bin"
cp moratech.py "$INSTALL_DIR/moratech"
chmod +x "$INSTALL_DIR/moratech"
echo -e "${GREEN}✓ Archivos copiados a $INSTALL_DIR${NC}"

# 3. Crear directorio de configuración
echo -e "${YELLOW}[3/5] Creando directorios de configuración...${NC}"
# El directorio se creará automáticamente cuando se ejecute por primera vez
echo -e "${GREEN}✓ Configuración lista${NC}"

# 4. Verificar permisos
echo -e "${YELLOW}[4/5] Configurando permisos...${NC}"
chmod 755 "$INSTALL_DIR/moratech"
echo -e "${GREEN}✓ Permisos configurados${NC}"

# 5. Finalizar
echo -e "${YELLOW}[5/5] Finalizando instalación...${NC}"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}         ✓ ¡MORATECH INSTALADO CORRECTAMENTE!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${PURPLE}Para iniciar Moratech, simplemente escribe:${NC}"
echo -e "${YELLOW}    moratech${NC}"
echo ""
echo -e "${PURPLE}Credenciales por defecto:${NC}"
echo -e "${YELLOW}    Usuario: admin${NC}"
echo -e "${YELLOW}    Contraseña: admin123${NC}"
echo ""
echo -e "${RED}⚠ IMPORTANTE: Cambia la contraseña después del primer login${NC}"
echo ""
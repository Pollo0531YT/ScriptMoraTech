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
echo -e "${YELLOW}[1/6] Verificando Python3...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 no está instalado. Instalando...${NC}"
    apt-get update
    apt-get install -y python3 python3-pip
else
    echo -e "${GREEN}✓ Python3 ya está instalado${NC}"
fi

# 2. Crear directorio de instalación
echo -e "${YELLOW}[2/6] Creando directorios...${NC}"
INSTALL_DIR="/usr/local/lib/moratech"
mkdir -p "$INSTALL_DIR"
echo -e "${GREEN}✓ Directorio creado en $INSTALL_DIR${NC}"

# 3. Copiar archivos
echo -e "${YELLOW}[3/6] Copiando archivos del sistema...${NC}"
cp moratech.py "$INSTALL_DIR/"
cp -r modules "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/moratech.py"
echo -e "${GREEN}✓ Archivos copiados${NC}"

# 4. Crear comando moratech
echo -e "${YELLOW}[4/6] Creando comando moratech...${NC}"
cat > /usr/local/bin/moratech << 'EOF'
#!/bin/bash
cd /usr/local/lib/moratech
exec python3 moratech.py "$@"
EOF
chmod +x /usr/local/bin/moratech
echo -e "${GREEN}✓ Comando moratech creado${NC}"

# 5. Verificar permisos
echo -e "${YELLOW}[5/6] Configurando permisos...${NC}"
chmod -R 755 "$INSTALL_DIR"
echo -e "${GREEN}✓ Permisos configurados${NC}"

# 6. Finalizar
echo -e "${YELLOW}[6/6] Finalizando instalación...${NC}"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}         ✓ ¡MORATECH INSTALADO CORRECTAMENTE!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Para ejecutar, escribe: ${GREEN}moratech${NC}"
echo ""
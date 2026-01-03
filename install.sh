#!/bin/bash

# MORATECH - Instalador para Ubuntu (mejorado)
set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Por favor ejecuta este script con sudo${NC}"
    exit 1
fi

echo -e "${GREEN}Iniciando instalación de Moratech...${NC}\n"

# 1. Verificar Python3
echo -e "${YELLOW}[1/7] Verificando Python3...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 no está instalado. Instalando...${NC}"
    apt-get update
    apt-get install -y python3 python3-pip
else
    echo -e "${GREEN}✓ Python3 ya está instalado${NC}"
fi

# 2. Crear directorio de instalación
echo -e "${YELLOW}[2/7] Creando directorios...${NC}"
INSTALL_DIR="/usr/local/lib/moratech"
mkdir -p "$INSTALL_DIR"
echo -e "${GREEN}✓ Directorio creado en $INSTALL_DIR${NC}"

# 3. Copiar archivos
echo -e "${YELLOW}[3/7] Copiando archivos del sistema...${NC}"
# Asumimos que este instalador se ejecuta desde el directorio que contiene moratech.py y modules/
cp moratech.py "$INSTALL_DIR/" || { echo "Falta moratech.py"; exit 1; }
cp -r modules "$INSTALL_DIR/" || { echo "Falta carpeta modules/"; exit 1; }
chmod +x "$INSTALL_DIR/moratech.py"
echo -e "${GREEN}✓ Archivos copiados${NC}"

# 4. Crear comando moratech
echo -e "${YELLOW}[4/7] Creando comando moratech...${NC}"
cat > /usr/local/bin/moratech << 'EOF'
#!/bin/bash
cd /usr/local/lib/moratech
exec python3 moratech.py "$@"
EOF
chmod +x /usr/local/bin/moratech
echo -e "${GREEN}✓ Comando moratech creado${NC}"

# 5. Configurar permisos y propietario
echo -e "${YELLOW}[5/7] Configurando permisos...${NC}"
chown -R root:root "$INSTALL_DIR"
chmod -R 755 "$INSTALL_DIR"
echo -e "${GREEN}✓ Permisos configurados${NC}"

# Finalizar
echo -e "${YELLOW}[7/7] Finalizando instalación...${NC}"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}         ✓ ¡MORATECH INSTALADO CORRECTAMENTE!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Para ejecutar, escribe: ${GREEN}moratech${NC}"
echo ""

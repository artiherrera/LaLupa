#!/bin/bash
# Script de despliegue para LaLupa en Ubuntu
# Ejecutar como root o con sudo

set -e

echo "=========================================="
echo "  Despliegue de LaLupa en Ubuntu"
echo "=========================================="

# Variables
APP_DIR="/var/www/lalupa"
REPO_URL="https://github.com/arturoherrerae/lalupa.git"

# 1. Actualizar sistema
echo "[1/8] Actualizando sistema..."
apt update && apt upgrade -y

# 2. Instalar dependencias
echo "[2/8] Instalando dependencias..."
apt install -y python3 python3-pip python3-venv nginx git

# 3. Crear directorio de la aplicacion
echo "[3/8] Configurando directorio..."
mkdir -p $APP_DIR
cd $APP_DIR

# 4. Clonar repositorio (o actualizar si existe)
echo "[4/8] Obteniendo codigo..."
if [ -d ".git" ]; then
    git pull origin main
else
    git clone $REPO_URL .
fi

# 5. Crear entorno virtual e instalar dependencias
echo "[5/8] Configurando entorno Python..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 6. Crear archivo .env si no existe
if [ ! -f ".env" ]; then
    echo "[INFO] Creando archivo .env desde plantilla..."
    cp scripts/.env.template .env
    echo ""
    echo "IMPORTANTE: Edita /var/www/lalupa/.env con tus credenciales"
    echo ""
fi

# 7. Configurar Gunicorn como servicio
echo "[6/8] Configurando Gunicorn..."
cp scripts/lalupa.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable lalupa

# 8. Configurar Nginx
echo "[7/8] Configurando Nginx..."
cp scripts/nginx-lalupa.conf /etc/nginx/sites-available/lalupa
ln -sf /etc/nginx/sites-available/lalupa /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Verificar configuracion de Nginx
nginx -t

# 9. Establecer permisos
echo "[8/8] Estableciendo permisos..."
chown -R www-data:www-data $APP_DIR
chmod -R 755 $APP_DIR

# 10. Iniciar servicios
echo "Iniciando servicios..."
systemctl restart lalupa
systemctl restart nginx

echo ""
echo "=========================================="
echo "  Despliegue completado!"
echo "=========================================="
echo ""
echo "Pasos siguientes:"
echo "1. Edita /var/www/lalupa/.env con tus credenciales de BD"
echo "2. Edita /etc/nginx/sites-available/lalupa con tu dominio"
echo "3. Reinicia: sudo systemctl restart lalupa nginx"
echo ""
echo "Para HTTPS con Let's Encrypt:"
echo "  sudo apt install certbot python3-certbot-nginx"
echo "  sudo certbot --nginx -d TU_DOMINIO"
echo ""
echo "Ver logs:"
echo "  sudo journalctl -u lalupa -f"
echo ""

#!/usr/bin/env bash
# build.sh

# Actualizar pip
python -m pip install --upgrade pip

# Instalar dependencias del sistema para Pillow
apt-get update
apt-get install -y libjpeg-dev zlib1g-dev

# Instalar requirements
pip install -r requirements.txt
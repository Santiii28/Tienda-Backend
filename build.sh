#!/usr/bin/env bash
# Comando de build de Render: instala dependencias, reúne los estáticos y
# aplica las migraciones sobre la base de datos (Neon).
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input

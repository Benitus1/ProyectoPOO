#!/usr/bin/env bash
cd "$(dirname "$0")"
python -m pip install pyinstaller
pyinstaller --noconfirm --onefile --add-data "templates:templates" --name EcoTechWeb webapp.py
echo "Ejecutable generado en dist/EcoTechWeb"

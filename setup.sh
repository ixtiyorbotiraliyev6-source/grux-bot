#!/bin/bash
# Oracle Cloud Ubuntu serverga bot o'rnatish skripti
# Ishlatish: bash setup.sh

echo "=== Telegram Bot O'rnatish ==="

# Python va pip o'rnatish
sudo apt update -y
sudo apt install -y python3 python3-pip python3-venv git screen

# Virtual environment yaratish
python3 -m venv venv
source venv/bin/activate

# Kutubxonalar o'rnatish
pip install aiogram aiosqlite

# Systemd service o'rnatish
sudo cp telegram-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot

echo ""
echo "=== Bot muvaffaqiyatli o'rnatildi! ==="
echo "Holat: sudo systemctl status telegram-bot"
echo "Loglar: sudo journalctl -u telegram-bot -f"

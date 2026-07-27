# config.py - Настройки приложения
import os

# Telegram Bot Token (из переменных окружения или по умолчанию)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8734711399:AAHv2a0ipIrKlR_kETQfw2h1d1-IlAHQJko")

# Admin
ADMIN_ID = int(os.getenv("ADMIN_ID", "8592139483"))

# SMS
SMS_NUMBER = "7878"
REPLY_NUMBER = "8464"
CONFIRM_TEXT = "Перевод в Таджикистан"
RURU_TEXT = "Оплата не произведена"
SIGNAL_TEXT = "СИГНАЛ: СМС/САЙТ ИДЕТ"

# WebSocket
WS_HOST = "0.0.0.0"
WS_PORT = 8765

# Auto-buy (заблокировано)
AUTO_BUY_ENABLED = False

# Database
DB_URL = "sqlite:///data.db"

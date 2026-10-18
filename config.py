# language: Python 3.11, file: config.py
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
API_ID    = int(os.environ.get("API_ID", "0"))
API_HASH  = os.environ.get("API_HASH", "")
DB_PATH   = "accounts.db"
PROXIES   = []

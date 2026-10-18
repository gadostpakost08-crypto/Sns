# language: Python 3.11, file: accounts.py
import os
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH
from db import add_account

SESSIONS_DIR = "sessions"

def ensure_sessions_dir():
    os.makedirs(SESSIONS_DIR, exist_ok=True)

def import_session_file(file_bytes: bytes, filename: str) -> str:
    """Сохраняет .session файл и конвертирует в StringSession."""
    ensure_sessions_dir()
    name = filename.replace(".session", "")
    path = os.path.join(SESSIONS_DIR, name)

    # Сохраняем файл
    with open(path + ".session", "wb") as f:
        f.write(file_bytes)

    # Конвертируем в строку
    client = TelegramClient(path, API_ID, API_HASH)
    client.connect()

    if not client.is_user_authorized():
        client.disconnect()
        os.remove(path + ".session")
        raise ValueError("Аккаунт не авторизован")

    string = StringSession.save(client.session)
    client.disconnect()

    # Удаляем файл после конвертации
    os.remove(path + ".session")

    add_account(string, name)
    return string

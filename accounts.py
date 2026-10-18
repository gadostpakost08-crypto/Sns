# language: Python 3.11, file: accounts.py
import os
import json
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from db import add_account

SESSIONS_DIR = "sessions"

def import_from_pair(session_bytes: bytes, json_bytes: bytes, filename: str) -> str:
    """Принимает .session + .json, сам достаёт API данные."""
    os.makedirs(SESSIONS_DIR, exist_ok=True)

    # Читаем JSON
    data     = json.loads(json_bytes.decode("utf-8"))
    api_id   = int(data["api_id"])
    api_hash = str(data["api_hash"])
    phone    = str(data.get("phone", filename.replace(".session", "")))

    # Сохраняем .session файл
    name = filename.replace(".session", "")
    path = os.path.join(SESSIONS_DIR, name)
    with open(path + ".session", "wb") as f:
        f.write(session_bytes)

    # Конвертируем в StringSession
    client = TelegramClient(path, api_id, api_hash)
    client.connect()

    if not client.is_user_authorized():
        client.disconnect()
        os.remove(path + ".session")
        raise ValueError("Аккаунт не авторизован")

    string = StringSession.save(client.session)
    client.disconnect()
    os.remove(path + ".session")

    add_account(string, phone)
    return phone

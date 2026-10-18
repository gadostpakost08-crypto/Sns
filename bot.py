# language: Python 3.11, file: bot.py, target: python-telegram-bot 21.x
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from config import BOT_TOKEN
from db import init_db, add_account, get_account_count
from accounts import import_from_pair
from engine import mass_report, full_mass_report, ALL_REASONS

AWAIT_TARGET, AWAIT_REASON     = range(2)
AWAIT_SESSION_STR, AWAIT_PHONE = range(2, 4)
AWAIT_FULL_TARGET              = 4
AWAIT_SESSION_FILE, AWAIT_JSON_FILE = range(5, 7)

REASON_KB = [["spam", "violence"], ["porn", "other"], ["child"]]

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔨 Report Engine\n\n"
        "/addfile — загрузить аккаунт (.session + .json)\n"
        "/report — жалобы\n"
        "/fullreport — все причины сразу\n"
        "/status — пул аккаунтов\n"
        "/cancel — отмена"
    )

async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    count = get_account_count()
    await update.message.reply_text(f"Активных аккаунтов: {count}")

# ==================== ЗАГРУЗКА ПАРЫ ФАЙЛОВ ====================

async def addfile_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text(
        "Шаг 1/2 — отправь .session файл:"
    )
    return AWAIT_SESSION_FILE

async def addfile_session(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document

    if not doc or not doc.file_name.endswith(".session"):
        await update.message.reply_text("❌ Нужен .session файл. Попробуй ещё раз:")
        return AWAIT_SESSION_FILE

    file = await doc.get_file()
    ctx.user_data["session_bytes"]    = bytes(await file.download_as_bytearray())
    ctx.user_data["session_filename"] = doc.file_name

    await update.message.reply_text(
        f"✅ {doc.file_name} получен.\n"
        "Шаг 2/2 — теперь отправь .json файл для этого аккаунта:"
    )
    return AWAIT_JSON_FILE

async def addfile_json(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document

    if not doc or not doc.file_name.endswith(".json"):
        await update.message.reply_text("❌ Нужен .json файл. Попробуй ещё раз:")
        return AWAIT_JSON_FILE

    file = await doc.get_file()
    json_bytes = bytes(await file.download_as_bytearray())

    session_bytes    = ctx.user_data["session_bytes"]
    session_filename = ctx.user_data["session_filename"]

    msg = await update.message.reply_text(f"Обрабатываю {session_filename}…")

    try:
        phone = import_from_pair(session_bytes, json_bytes, session_filename)
        count = get_account_count()
        await msg.edit_text(
            f"✅ {phone} добавлен.\n"
            f"Всего в пуле: {count}\n\n"
            "Следующий аккаунт → /addfile\n"
            "Готово → /status"
        )
    except ValueError as e:
        await msg.edit_text(f"❌ {session_filename}: {e}")
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {e}")

    return ConversationHandler.END

# ==================== РЕПОРТ ====================

async def report_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Цель — @username или t.me/ссылка:")
    return AWAIT_TARGET

async def report_target(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["target"] = update.message.text.strip()
    kb = ReplyKeyboardMarkup(REASON_KB, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Причина:", reply_markup=kb)
    return AWAIT_REASON

async def report_reason(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    reason = update.message.text.strip().lower()
    target = ctx.user_data["target"]
    msg = await update.message.reply_text(
        f"Репорт на {target} [{reason}]…",
        reply_markup=ReplyKeyboardRemove()
    )
    r = await mass_report(target, reason)
    await msg.edit_text(
        f"Готово — {target}\n"
        f"✅ {r['ok']} / ❌ {r['fail']} / всего {r['total']}"
    )
    return ConversationHandler.END

# ==================== FULL REPORT ====================

async def fullreport_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Цель для полного репорта:")
    return AWAIT_FULL_TARGET

async def fullreport_run(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    target = update.message.text.strip()
    count  = get_account_count()
    msg = await update.message.reply_text(
        f"Полный репорт на {target}\n"
        f"{len(ALL_REASONS)} причины × {count} аккаунтов…"
    )
    r = await full_mass_report(target)
    await msg.edit_text(
        f"Готово — {target}\n"
        f"✅ {r['ok']} / ❌ {r['fail']}"
    )
    return ConversationHandler.END

# ==================== ОТМЕНА ====================

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ==================== MAIN ====================

def main():
    init_db()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("status", status_cmd))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("addfile", addfile_start)],
        states={
            AWAIT_SESSION_FILE: [MessageHandler(filters.Document.ALL, addfile_session)],
            AWAIT_JSON_FILE:    [MessageHandler(filters.Document.ALL, addfile_json)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("report", report_start)],
        states={
            AWAIT_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_target)],
            AWAIT_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_reason)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("fullreport", fullreport_start)],
        states={
            AWAIT_FULL_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, fullreport_run)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    ))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

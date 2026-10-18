# language: Python 3.11, file: bot.py, target: python-telegram-bot v20
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from config import BOT_TOKEN
from db import init_db, add_account, get_account_count
from engine import mass_report, full_mass_report, ALL_REASONS

# --- состояния ---
AWAIT_TARGET, AWAIT_REASON   = range(2)
AWAIT_SESSION_STR, AWAIT_PHONE = range(2, 4)
AWAIT_FULL_TARGET            = 4

REASON_KB = [["spam", "violence"], ["porn", "other"], ["child"]]

# ==================== КОМАНДЫ ====================

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔨 Report Engine\n\n"
        "/report — жалобы (выбор причины)\n"
        "/fullreport — все причины сразу\n"
        "/addaccount — добавить аккаунт (session string)\n"
        "/status — пул аккаунтов\n"
        "/cancel — отмена"
    )

async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    count = get_account_count()
    await update.message.reply_text(f"Активных аккаунтов: {count}")

# ==================== РЕПОРТ ====================

async def report_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Цель — @username или t.me/ссылка:"
    )
    return AWAIT_TARGET

async def report_target(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["target"] = update.message.text.strip()
    kb = ReplyKeyboardMarkup(
        REASON_KB, one_time_keyboard=True, resize_keyboard=True
    )
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
    await update.message.reply_text(
        "Цель для полного репорта — @username или t.me/ссылка:"
    )
    return AWAIT_FULL_TARGET

async def fullreport_run(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    target = update.message.text.strip()
    reasons_count = len(ALL_REASONS)
    accounts_count = get_account_count()
    msg = await update.message.reply_text(
        f"Полный репорт на {target}\n"
        f"{reasons_count} причины × {accounts_count} аккаунтов…"
    )
    r = await full_mass_report(target)
    await msg.edit_text(
        f"Полный репорт завершён — {target}\n"
        f"✅ {r['ok']} / ❌ {r['fail']}"
    )
    return ConversationHandler.END

# ==================== ДОБАВИТЬ АККАУНТ ====================

async def addacc_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Отправь Session String аккаунта.\n\n"
        "Как получить — /getsession"
    )
    return AWAIT_SESSION_STR

async def addacc_session(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["session_str"] = update.message.text.strip()
    await update.message.reply_text("Номер телефона этого аккаунта (+7...):")
    return AWAIT_PHONE

async def addacc_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    phone      = update.message.text.strip()
    session_str = ctx.user_data["session_str"]
    try:
        add_account(session_str, phone)
        await update.message.reply_text(f"✅ Аккаунт {phone} добавлен.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
    return ConversationHandler.END

async def getsession_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Для получения Session String:\n\n"
        "1. Открой @StringSessionBot в Telegram\n"
        "2. Введи API_ID и API_HASH\n"
        "3. Авторизуйся — получишь строку\n"
        "4. Скопируй строку → /addaccount"
    )

# ==================== ОТМЕНА ====================

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Отменено.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ==================== MAIN ====================

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",      start))
    app.add_handler(CommandHandler("status",     status_cmd))
    app.add_handler(CommandHandler("getsession", getsession_help))

    report_conv = ConversationHandler(
        entry_points=[CommandHandler("report", report_start)],
        states={
            AWAIT_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_target)],
            AWAIT_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_reason)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(report_conv)

    full_conv = ConversationHandler(
        entry_points=[CommandHandler("fullreport", fullreport_start)],
        states={
            AWAIT_FULL_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, fullreport_run)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(full_conv)

    addacc_conv = ConversationHandler(
        entry_points=[CommandHandler("addaccount", addacc_start)],
        states={
            AWAIT_SESSION_STR: [MessageHandler(filters.TEXT & ~filters.COMMAND, addacc_session)],
            AWAIT_PHONE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, addacc_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(addacc_conv)

    app.run_polling()

if __name__ == "__main__":
    main()

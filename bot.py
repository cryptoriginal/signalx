# bot.py
import os
import logging
import asyncio
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from suggest import get_trade_suggestions

# load token either from env var or config.py fallback
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    try:
        from config import TELEGRAM_BOT_TOKEN as TOKEN  # type: ignore
    except Exception:
        TOKEN = None

if not TOKEN:
    raise RuntimeError("Telegram token not set. Set TELEGRAM_BOT_TOKEN env var or edit config.py")

# Delete any webhook previously set (avoids getUpdates conflicts)
try:
    Bot(token=TOKEN).delete_webhook()
except Exception as e:
    # not critical
    print("delete_webhook:", e)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 AI Scalper Bot ready. Use /suggest to get scalp trade ideas (MEXC futures pairs >= 40M 24h).")

async def suggest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    # Inform user
    await context.bot.send_message(chat_id=chat.id, text="🔎 Scanning top MEXC futures pairs (this may take a few seconds)...")
    loop = asyncio.get_running_loop()
    # run heavy/blocking work in executor
    try:
        suggestions = await loop.run_in_executor(None, get_trade_suggestions, 3, 40_000_000)
    except Exception as e:
        logger.exception("Error running suggestions")
        await context.bot.send_message(chat_id=chat.id, text=f"❌ Error generating suggestions: {e}")
        return

    if not suggestions:
        await context.bot.send_message(chat_id=chat.id, text="⚠️ No trade setups found right now.")
        return

    for msg in suggestions:
        await context.bot.send_message(chat_id=chat.id, text=msg, parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("suggest", suggest_command))
    # run polling (safe because we deleted webhook above)
    logger.info("Bot starting (polling)...")
    app.run_polling()

if __name__ == "__main__":
    main()

import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from suggest import get_ai_trade_suggestions
from config import TELEGRAM_BOT_TOKEN

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /suggest to get AI trade signals.")

async def suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Scanning MEXC Futures for best trades...")

    suggestions = await get_ai_trade_suggestions()
    if not suggestions:
        await update.message.reply_text("No good trade setups found.")
        return

    for s in suggestions:
        msg = (
            f"📊 *{s['pair']}*\n"
            f"🔁 Direction: *{s['direction']}*\n"
            f"🎯 Entry: `{s['entry']}`\n"
            f"🛡 SL: `{s['sl']}`\n"
            f"💰 TP: `{s['tp']}`\n"
            f"⚖ RR: `{s['rr']}`\n"
            f"📈 Leverage: {s['leverage']}\n"
            f"🧠 Reason: _{s['reason']}_"
        )
        await update.message.reply_markdown(msg)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("suggest", suggest))

    app.run_polling()

if __name__ == "__main__":
    main()



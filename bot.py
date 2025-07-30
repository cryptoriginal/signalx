from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from suggest import get_trade_suggestions
from config import TELEGRAM_BOT_TOKEN

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /suggest to get MEXC Futures scalping trade signals.")

async def suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Scanning MEXC Futures pairs...")

    suggestions = get_trade_suggestions()

    if not suggestions:
        await update.message.reply_text("No high-quality setups found at the moment.")
        return

    for trade in suggestions:
        msg = (
            f"📈 *{trade['symbol']}* — *{trade['signal']}*\n"
            f"🎯 Entry: `{trade['entry']}`\n"
            f"🛑 SL: `{trade['sl']}`\n"
            f"🏁 TP: `{trade['tp']}`\n"
            f"⚖️ RR: ~1:2.2\n"
            f"📊 Leverage: `{trade['leverage']}x`\n"
            f"🧠 Reason: {trade['reason']}"
        )
        await update.message.reply_markdown(msg)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("suggest", suggest))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

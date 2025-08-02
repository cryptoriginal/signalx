# bot.py

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import BOT_TOKEN
from suggest import get_trade_suggestions

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Welcome! Send /suggest to get MEXC Futures trade setups.")

async def suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning market for setups...")
    suggestions = get_trade_suggestions()
    for s in suggestions:
        msg = (
            f"📈 *{s['symbol']}* — *{s['direction']}*\n"
            f"🎯 Entry: `{s['entry']}`\n"
            f"❌ SL: `{s['stop_loss']}`\n"
            f"✅ TP: `{s['take_profit']}`\n"
            f"📊 RR: `{s['rr']}`\n"
            f"🧠 Reason: _{s['reason']}_"
        )
        await update.message.reply_markdown(msg)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("suggest", suggest))
    app.run_polling()

if __name__ == '__main__':
    main()




from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

import suggest  # Your AI logic file

TOKEN = "YOUR_BOT_TOKEN"
bot = Bot(token=TOKEN)

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# Define the /suggest command
async def suggest_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    signals = suggest.get_trade_suggestions()
    if not signals:
        await update.message.reply_text("No good trade setups found.")
        return
    for signal in signals:
        msg = (
            f"📊 Symbol: {signal['symbol']}\n"
            f"📈 Direction: {signal['direction']}\n"
            f"💰 Entry: {signal['entry']}\n"
            f"🛡 Stop Loss: {signal['stop_loss']}\n"
            f"🎯 Take Profit: {signal['take_profit']}\n"
            f"📊 Risk-Reward: {signal['rr']}\n"
            f"🧠 Reason: {signal['reason']}"
        )
        await update.message.reply_text(msg)

application.add_handler(CommandHandler("suggest", suggest_handler))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put(update)
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "Bot is live!", 200




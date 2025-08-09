import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- Bot token ---
TOKEN = os.getenv("8060081170:AAGL3GZsRBhyFUuEQf1PYP-8azEnr3v_2sQ")  # Store BOT_TOKEN in Render environment variables

# --- Function to fetch MEXC Futures pairs ≥ 40M volume ---
def get_high_volume_pairs():
    url = "https://contract.mexc.com/api/v1/contract/ticker"
    try:
        resp = requests.get(url, timeout=10).json()
        filtered = []
        for pair in resp.get("data", []):
            if float(pair["turnover24h"]) >= 40_000_000:
                filtered.append(pair["symbol"])
        return filtered
    except Exception as e:
        logging.error(f"Error fetching MEXC data: {e}")
        return []

# --- AI-like Trade Signal Logic ---
def generate_trade_signal(symbol):
    # In real case, replace this logic with TA/AI checks
    import random
    direction = random.choice(["LONG", "SHORT"])
    entry = round(random.uniform(0.9, 1.1), 4)  # Placeholder
    sl = round(entry * (0.98 if direction == "LONG" else 1.02), 4)
    tp = round(entry * (1.04 if direction == "LONG" else 0.96), 4)
    reason = "Volume spike + bullish reversal candle" if direction == "LONG" else "Resistance rejection + bearish engulfing"
    return {
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "reason": reason
    }

# --- /suggest command handler ---
async def suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pairs = get_high_volume_pairs()
    if not pairs:
        await update.message.reply_text("No high-volume pairs found right now.")
        return

    reply = "📊 **Scalping Trade Suggestions**\n\n"
    for symbol in pairs[:3]:  # Limit to top 3
        trade = generate_trade_signal(symbol)
        reply += f"💎 {trade['symbol']}\n" \
                 f"📈 Direction: {trade['direction']}\n" \
                 f"🎯 Entry: {trade['entry']}\n" \
                 f"📉 SL: {trade['sl']}\n" \
                 f"🚀 TP: {trade['tp']}\n" \
                 f"📌 Reason: {trade['reason']}\n\n"

    await update.message.reply_text(reply, parse_mode="Markdown")

# --- Main ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("suggest", suggest))
    app.run_polling()


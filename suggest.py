# suggest.py

import requests
import random
import math

def fetch_high_volume_pairs(min_volume_usdt=40000000):
    url = 'https://api.mexc.com/api/v3/ticker/24hr'
    res = requests.get(url).json()
    pairs = []
    for item in res:
        symbol = item['symbol']
        vol = float(item.get('quoteVolume', 0))
        if vol > min_volume_usdt and symbol.endswith('USDT'):
            pairs.append(symbol)
    return pairs

def mock_ai_trade_decision(symbol):
    # Simulate AI logic - replace with real model later
    direction = random.choice(['Long', 'Short'])
    entry = round(random.uniform(0.95, 1.05) * 100, 3)
    rr = round(random.uniform(2.2, 3.5), 2)
    sl = round(entry * (0.985 if direction == 'Long' else 1.015), 3)
    tp = round(entry + (entry - sl) * rr if direction == 'Long' else entry - (sl - entry) * rr, 3)

    reason = random.choice([
        "Hammer candle at key support",
        "Bearish engulfing + MACD cross",
        "RSI + 3 EMA alignment",
        "Breakout from consolidation zone",
        "Reversal candle at Fib level"
    ])
    return {
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "rr": rr,
        "reason": reason
    }

def get_trade_suggestions(limit=3):
    suggestions = []
    pairs = fetch_high_volume_pairs()
    random.shuffle(pairs)
    for symbol in


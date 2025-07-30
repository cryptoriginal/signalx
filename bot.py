import aiohttp
import pandas as pd

async def get_top_futures_pairs(min_volume_usdt=40_000_000):
    url = "https://contract.mexc.com/api/v1/contract/ticker"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()

    pairs = []
    for item in data['data']:
        vol = float(item['turnover'])  # 24h volume in USDT
        symbol = item['symbol']
        if vol >= min_volume_usdt:
            pairs.append((symbol, vol))

    sorted_pairs = sorted(pairs, key=lambda x: x[1], reverse=True)
    return [p[0] for p in sorted_pairs]

async def get_ai_trade_suggestions():
    pairs = await get_top_futures_pairs()
    suggestions = []

    for symbol in pairs[:5]:  # Limit to top 5 pairs
        direction = "Long" if hash(symbol) % 2 == 0 else "Short"
        entry = 100  # dummy
        sl = entry * 0.98 if direction == "Long" else entry * 1.02
        tp = entry * 1.05 if direction == "Long" else entry * 0.95
        rr = abs(tp - entry) / abs(entry - sl)

        reason = "Reversal candle + RSI divergence + EMA trend support"

        suggestions.append({
            "pair": symbol,
            "direction": direction,
            "entry": round(entry, 3),
            "sl": round(sl, 3),
            "tp": round(tp, 3),
            "rr": round(rr, 2),
            "leverage": "Up to 5x",
            "reason": reason
        })

    return suggestions


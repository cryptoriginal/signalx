import ccxt
import pandas as pd
import requests
import ta
import datetime

def get_futures_symbols_with_volume(min_volume=40000000):
    exchange = ccxt.mexc()
    markets = exchange.load_markets()
    futures_symbols = [symbol for symbol in markets if '/USDT:USDT' in symbol]

    high_volume_symbols = []

    for symbol in futures_symbols:
        try:
            ticker = exchange.fetch_ticker(symbol)
            if ticker['quoteVolume'] * ticker['last'] >= min_volume:
                high_volume_symbols.append(symbol)
        except Exception:
            continue

    return high_volume_symbols

def fetch_ohlcv(symbol):
    exchange = ccxt.mexc()
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception:
        return None

def analyze_chart(symbol):
    df = fetch_ohlcv(symbol)
    if df is None or df.empty:
        return None

    df['ema21'] = ta.trend.ema_indicator(df['close'], window=21)
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    df['macd'] = ta.trend.macd(df['close']).macd_diff()

    last_candle = df.iloc[-1]
    prev_candle = df.iloc[-2]

    signal = None
    reason = ""

    # Bullish Reversal
    if last_candle['close'] > last_candle['open'] and prev_candle['close'] < prev_candle['open']:
        if last_candle['rsi'] < 35 and last_candle['macd'] > 0:
            signal = 'LONG'
            reason = "Bullish reversal + RSI < 35 + MACD cross"

    # Bearish Reversal
    if last_candle['close'] < last_candle['open'] and prev_candle['close'] > prev_candle['open']:
        if last_candle['rsi'] > 65 and last_candle['macd'] < 0:
            signal = 'SHORT'
            reason = "Bearish reversal + RSI > 65 + MACD cross"

    if signal:
        entry = last_candle['close']
        if signal == 'LONG':
            sl = min(last_candle['low'], prev_candle['low'])
            tp = entry + (entry - sl) * 2.2
        else:
            sl = max(last_candle['high'], prev_candle['high'])
            tp = entry - (sl - entry) * 2.2

        return {
            'symbol': symbol,
            'signal': signal,
            'entry': round(entry, 4),
            'sl': round(sl, 4),
            'tp': round(tp, 4),
            'leverage': 5,
            'reason': reason
        }

    return None

def get_trade_suggestions():
    symbols = get_futures_symbols_with_volume()
    suggestions = []

    for symbol in symbols:
        result = analyze_chart(symbol)
        if result:
            suggestions.append(result)

    return suggestions

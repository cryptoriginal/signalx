# suggest.py

import requests
import pandas as pd
import numpy as np

def fetch_high_volume_pairs(min_volume_usdt=40000000):
    url = 'https://api.mexc.com/api/v3/ticker/24hr'
    res = requests.get(url).json()
    pairs = []
    for item in res:
        symbol = item['symbol']
        volume = float(item.get('quoteVolume', 0))
        if volume > min_volume_usdt and symbol.endswith("USDT"):
            pairs.append(symbol)
    return pairs

def fetch_klines(symbol, interval='1h', limit=100):
    url = f'https://api.mexc.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            '_1', '_2', '_3', '_4', '_5', '_6'
        ])
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].astype(float)
        return df
    except Exception as e:
        print(f"[ERROR] {symbol}: {e}")
        return None

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=period).mean()
    avg_loss = pd.Series(loss).rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def detect_signal(df):
    df['EMA_7'] = df['close'].ewm(span=7).mean()
    df['EMA_30'] = df['close'].ewm(span=30).mean()
    df['EMA_50'] = df['close'].ewm(span=50).mean()
    df['RSI'] = calculate_rsi(df['close'])

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    signal = None

    # Long setup
    if (
        prev['EMA_7'] < prev['EMA_30'] and
        latest['EMA_7'] > latest['EMA_30'] and
        latest['RSI'] > 35 and
        latest['close'] > latest['EMA_50']
    ):
        entry = latest['close']
        sl = df['low'][-30:].min()
        tp = entry + (entry - sl) * 2.2
        rr = round((tp - entry) / (entry - sl), 2)
        if rr >= 2.2:
            signal = {
                'symbol': '',
                'direction': 'Long',
                'entry': round(entry, 4),
                'stop_loss': round(sl, 4),
                'take_profit': round(tp, 4),
                'rr': rr,
                'reason': '7 EMA crossed above 30 EMA, RSI > 35, price > 50 EMA'
            }

    # Short setup
    elif (
        prev['EMA_7'] > prev['EMA_30'] and
        latest['EMA_7'] < latest['EMA_30'] and
        latest['RSI'] < 75 and
        latest['close'] < latest['EMA_50']
    ):
        entry = latest['close']
        sl = df['high'][-30:].max()
        tp = entry - (sl - entry) * 2.2
        rr = round((entry - tp) / (sl - entry), 2)
        if rr >= 2.2:
            signal = {
                'symbol': '',
                'direction': 'Short',
                'entry': round(entry, 4),
                'stop_loss': round(sl, 4),
                'take_profit': round(tp, 4),
                'rr': rr,
                'reason': '7 EMA crossed below 30 EMA, RSI < 75, price < 50 EMA'
            }

    return signal

def get_trade_suggestions(limit=3):
    symbols = fetch_high_volume_pairs()
    results = []
    for symbol in symbols:
        df = fetch_klines(symbol)
        if df is None or len(df) < 50:
            continue
        signal = detect_signal(df)
        if signal:
            signal['symbol'] = symbol
            results.append(signal)
        if len(results) >= limit:
            break
    return results



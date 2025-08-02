# suggest.py

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

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
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', '_1', '_2', '_3', '_4', '_5', '_6'
        ])
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        return df
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def detect_signal(df):
    df['EMA_7'] = df['close'].ewm(span=7).mean()
    df['EMA_30'] = df['close'].ewm(span=30).mean()
    df['EMA_50'] = df['close'].ewm(span=50).mean()

    delta = df['close'].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=14).mean()
    avg_loss = pd.Series(loss).rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    signal = None

    # Long signal
    if (
        prev['EMA_7'] < prev['EMA_30']
        and latest['EMA_7'] > latest['EMA_30']
        and latest['RSI'] > 35
        and latest['close'] > latest['EMA_50']
    ):
        entry = latest['close']
        sl = df['low'][-20:].min()
        tp = entry + (entry - sl) * 2.2
        signal = {
            'direction': 'Long',
            'entry': round(entry, 4),
            'stop_loss': round(sl, 4),
            'take_profit': round(tp, 4),
            'rr': round((tp - entry) / (entry - sl), 2),
            'reason': '7 EMA crossed above 30 EMA + RSI > 35 + price > 50 EMA'
        }

    # Short signal
    elif (
        prev['EMA_7'] > prev['EMA_30']
        and latest['EMA_7'] < latest['EMA_30']
        and latest['RSI'] < 75
        and latest['close'] < latest['EMA_50']
    ):
        entry = latest['close']
        sl = df['high'][-20:].max()
        tp = entry - (sl - entry) * 2.2
        signal = {
            'direction': 'Short',
            'entry': round(entry, 4),
            'stop_loss': round(sl, 4),
            'take_profit': round(tp, 4),
            'rr': round((entry - tp) / (sl - entry), 2),
            'reason': '7 EMA crossed below 30 EMA + RSI < 75 + price < 50 EMA'
        }

    return signal

def get_trade_suggestions(limit=3):
    pairs = fetch_high_volume_pairs()
    results = []
    for symbol in pairs:
        df = fetch_klines(symbol)
        if df is None or df.empty or len(df) < 50:
            continue
        signal = detect_signal(df)
        if signal and signal['rr'] >= 2.2:
            signal['symbol'] = symbol
            results.append(signal)
        if len(results) >= limit:
            break
    return results

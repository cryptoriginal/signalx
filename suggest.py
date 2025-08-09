# suggest.py
import requests
import pandas as pd
import numpy as np
import math
import time
from typing import List, Dict

MEXC_TICKER_URL = "https://api.mexc.com/api/v3/ticker/24hr"
MEXC_KLINES_URL = "https://contract.mexc.com/api/v1/contract/kline/{symbol}?interval={interval}&limit={limit}"

DEFAULT_MIN_VOLUME = 40_000_000  # 40M USDT
MIN_KLINES = 50  # require at least this many candles
INTERVAL = "1h"
KLINES_LIMIT = 200
MIN_RR = 2.2

def fetch_high_volume_usdt_pairs(min_volume_usdt: int = DEFAULT_MIN_VOLUME) -> List[Dict]:
    """Return list of dicts from MEXC ticker data for USDT pairs with quoteVolume >= min_volume_usdt."""
    try:
        r = requests.get(MEXC_TICKER_URL, timeout=8)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print("fetch_high_volume_usdt_pairs error:", e)
        return []

    out = []
    for item in data:
        symbol = item.get("symbol")
        if not symbol or not symbol.endswith("USDT"):
            continue
        quote_vol = float(item.get("quoteVolume") or 0)
        if quote_vol >= min_volume_usdt:
            out.append({
                "symbol": symbol,
                "quoteVolume": quote_vol,
                "lastPrice": float(item.get("lastPrice") or 0)
            })
    # sort by volume desc
    out.sort(key=lambda x: x["quoteVolume"], reverse=True)
    return out

def fetch_klines(symbol: str, interval: str = INTERVAL, limit: int = KLINES_LIMIT) -> pd.DataFrame | None:
    """Fetch klines for contract API, return DataFrame ascending by time with float columns."""
    try:
        url = MEXC_KLINES_URL.format(symbol=symbol, interval=interval, limit=limit)
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        res = r.json()
        # contract API returns dict with code/data
        if isinstance(res, dict) and res.get("code") != 200:
            return None
        data = res.get("data") if isinstance(res, dict) else res
        if not data:
            return None
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        # reverse if returned newest first
        if df.index[0] > df.index[-1]:
            df = df.iloc[::-1].reset_index(drop=True)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        return df
    except Exception as e:
        print(f"fetch_klines {symbol} error:", e)
        return None

# simple candlestick pattern checks
def is_bullish_engulfing(df: pd.DataFrame, idx: int) -> bool:
    if idx < 1: return False
    o, c = df.at[idx, 'open'], df.at[idx, 'close']
    o1, c1 = df.at[idx-1, 'open'], df.at[idx-1, 'close']
    return (c > o) and (c1 < o1) and (c > o1) and (o < c1)

def is_hammer(df: pd.DataFrame, idx: int) -> bool:
    o, c, h, l = df.at[idx, 'open'], df.at[idx, 'close'], df.at[idx, 'high'], df.at[idx, 'low']
    body = abs(c - o)
    total = h - l
    if total <= 0: return False
    # small body near top, long lower shadow
    return (body / total) < 0.35 and ((min(o, c) - l) / total) < 0.35 and ((h - max(o, c)) / total) < 0.4

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['ema7'] = df['close'].ewm(span=7, adjust=False).mean()
    df['ema30'] = df['close'].ewm(span=30, adjust=False).mean()
    # RSI 14
    delta = df['close'].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=14, min_periods=1).mean()
    avg_loss = pd.Series(loss).rolling(window=14, min_periods=1).mean()
    rs = avg_gain / (avg_loss.replace(0, np.nan))
    df['rsi'] = 100 - (100 / (1 + rs))
    # volume rolling mean to detect spikes
    df['vol_ma20'] = df['volume'].rolling(window=20, min_periods=1).mean()
    return df

def find_reversal_candle_level(df: pd.DataFrame, lookback: int = 30, bullish=True):
    """
    Try to find a recent reversal candle (hammer or engulfing). Return price level (low for bullish, high for bearish).
    If none found, fall back to recent swing low/high (min/max over lookback).
    """
    n = len(df)
    for i in range(n-1, max(-1, n - lookback - 1), -1):
        if bullish:
            if is_hammer(df, i) or is_bullish_engulfing(df, i):
                return df.at[i, 'low']
        else:
            # bearish patterns: bearish engulfing (reverse of bullish Engulfing) or inverted hammer/shooting star approximated
            if i >= 1:
                o, c = df.at[i, 'open'], df.at[i, 'close']
                o1, c1 = df.at[i-1, 'open'], df.at[i-1, 'close']
                bearish_engulfing = (c < o) and (c1 > o1) and (c < o1) and (o > c1)
                # shooting star approx
                body = abs(c - o)
                total = df.at[i, 'high'] - df.at[i, 'low']
                shooting_star = total > 0 and (body / total) < 0.35 and ((df.at[i, 'high'] - max(o, c)) / total) > 0.6
                if bearish_engulfing or shooting_star:
                    return df.at[i, 'high']
    # fallback
    if bullish:
        return float(df['low'][-lookback:].min())
    else:
        return float(df['high'][-lookback:].max())

def detect_signal_for_symbol(df: pd.DataFrame, symbol: str) -> Dict | None:
    """
    Return a dict with signal info or None.
    - uses EMA 7/30 cross, RSI filter, volume spike, and reversal candle SL/TP calc.
    """
    df = calculate_indicators(df)
    if len(df) < MIN_KLINES:
        return None

    latest_idx = len(df) - 1
    prev_idx = latest_idx - 1
    latest = df.iloc[latest_idx]
    prev = df.iloc[prev_idx]

    # basic conditions
    ema_cross_up = prev['ema7'] < prev['ema30'] and latest['ema7'] > latest['ema30']
    ema_cross_down = prev['ema7'] > prev['ema30'] and latest['ema7'] < latest['ema30']

    # RSI filters (relaxed)
    rsi_ok_long = (latest['rsi'] is np.nan) or (latest['rsi'] > 20 and latest['rsi'] < 70)
    rsi_ok_short = (latest['rsi'] is np.nan) or (latest['rsi'] > 30 and latest['rsi'] < 80)

    # volume spike relative to 20-ma
    vol_spike = latest['volume'] > 1.5 * latest['vol_ma20']

    # build signals: require EMA cross + (volume spike or candlestick reversal or favorable RSI)
    # LONG
    if ema_cross_up and rsi_ok_long and (vol_spike or is_hammer(df, latest_idx) or is_bullish_engulfing(df, latest_idx)):
        entry = float(latest['close'])
        # sl = low of reversal candle (if found) or recent swing low
        sl_price = find_reversal_candle_level(df, lookback=30, bullish=True)
        if sl_price >= entry:
            # fallback: set SL a % below
            sl_price = entry * 0.995
        rr = MIN_RR
        tp_price = entry + (entry - sl_price) * rr
        # final RR calc
        rr_calc = (tp_price - entry) / max(1e-9, (entry - sl_price))
        reason_parts = []
        if vol_spike: reason_parts.append("volume spike")
        if is_hammer(df, latest_idx): reason_parts.append("hammer reversal")
        if is_bullish_engulfing(df, latest_idx): reason_parts.append("bullish engulfing")
        if prev['ema7'] < prev['ema30'] and latest['ema7'] > latest['ema30']: reason_parts.append("EMA 7 crossed above EMA 30")
        reason = ", ".join(reason_parts) if reason_parts else "EMA crossover"
        return {
            "symbol": symbol,
            "direction": "Long",
            "entry": round(entry, 6),
            "stop_loss": round(float(sl_price), 6),
            "take_profit": round(float(tp_price), 6),
            "rr": round(rr_calc, 2),
            "volume_24h": None,
            "reason": reason
        }

    # SHORT
    if ema_cross_down and rsi_ok_short and (vol_spike or (not is_hammer(df, latest_idx) and (not is_bullish_engulfing(df, latest_idx)) )):
        entry = float(latest['close'])
        sl_price = find_reversal_candle_level(df, lookback=30, bullish=False)
        if sl_price <= entry:
            sl_price = entry * 1.005
        rr = MIN_RR
        tp_price = entry - (sl_price - entry) * rr
        rr_calc = (entry - tp_price) / max(1e-9, (sl_price - entry))
        reason_parts = []
        if vol_spike: reason_parts.append("volume spike")
        # detect bearish engulfing
        if prev['ema7'] > prev['ema30'] and latest['ema7'] < latest['ema30']: reason_parts.append("EMA 7 crossed below EMA 30")
        reason = ", ".join(reason_parts) if reason_parts else "EMA crossover"
        return {
            "symbol": symbol,
            "direction": "Short",
            "entry": round(entry, 6),
            "stop_loss": round(float(sl_price), 6),
            "take_profit": round(float(tp_price), 6),
            "rr": round(rr_calc, 2),
            "volume_24h": None,
            "reason": reason
        }

    return None

def get_trade_suggestions(limit: int = 3, min_volume_usdt: int = DEFAULT_MIN_VOLUME) -> List[str]:
    """
    Scan high-volume pairs and return up to `limit` formatted suggestion strings.
    """
    out_messages = []
    pairs = fetch_high_volume_usdt_pairs(min_volume_usdt)
    if not pairs:
        return []

    # iterate through top pairs, fetch klines and detect signals
    for p in pairs:
        sym = p['symbol']
        try:
            df = fetch_klines(sym, interval=INTERVAL, limit=KLINES_LIMIT)
            if df is None or len(df) < MIN_KLINES:
                continue
            sig = detect_signal_for_symbol(df, sym)
            if sig:
                sig['volume_24h'] = round(p['quoteVolume'], 2)
                # format message (markdown)
                msg = (
                    f"📌 *{sig['symbol']}*  \n"
                    f"Direction: *{sig['direction']}*  \n"
                    f"Entry: `{sig['entry']}`  \n"
                    f"Stop-Loss: `{sig['stop_loss']}`  \n"
                    f"Take-Profit: `{sig['take_profit']}`  \n"
                    f"RR: `{sig['rr']}`  \n"
                    f"24h Volume: `${sig['volume_24h']:,}`  \n"
                    f"Reason: _{sig['reason']}_"
                )
                out_messages.append(msg)
                if len(out_messages) >= limit:
                    break
        except Exception as e:
            print("Error processing", sym, e)
            continue
        # small delay to be polite to API
        time.sleep(0.2)

    return out_messages

"""Signal engine for the MT5 trading assistant."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

PAKISTAN_TZ = ZoneInfo("Asia/Karachi")


def _indicators(candles: pd.DataFrame) -> pd.DataFrame:
    df = candles.copy()
    if "Close" not in df.columns:
        close_name = "close" if "close" in df.columns else "Close"
        df = df.rename(columns={close_name: "Close"})
    if "High" not in df.columns:
        df["High"] = df["Close"]
    if "Low" not in df.columns:
        df["Low"] = df["Close"]

    close = df["Close"].astype(float)
    df["fast_ma"] = close.ewm(span=9, adjust=False).mean()
    df["slow_ma"] = close.ewm(span=21, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = (100 - (100 / (1 + rs))).fillna(50)
    df["atr"] = (df["High"] - df["Low"]).rolling(14).mean()
    return df.dropna().copy()


def _base_analysis(candles: pd.DataFrame):
    df = _indicators(candles)
    if len(df) < 5:
        raise ValueError("Not enough valid candles to generate a signal.")

    last = df.iloc[-1]
    previous = df.iloc[-2]
    bullish = last.fast_ma > last.slow_ma and last.rsi >= 50 and last.Close >= previous.Close
    bearish = last.fast_ma < last.slow_ma and last.rsi <= 50 and last.Close <= previous.Close

    if bullish:
        trend, direction = "Bullish", "up"
    elif bearish:
        trend, direction = "Bearish", "down"
    else:
        trend, direction = "Mixed", "unclear"

    strength = 50
    if direction in {"up", "down"}:
        strength += min(20, abs(float(last.rsi) - 50) * 0.6)
        strength += min(15, abs(float(last.fast_ma - last.slow_ma)) / max(float(last.Close), 1e-9) * 10000)
    strength = max(35, min(92, round(strength)))

    atr_ratio = float(last.atr / last.Close) if float(last.Close) else 0.0
    volatility = "High" if atr_ratio > 0.004 else "Normal"
    return df, last, trend, direction, strength, volatility


def _result(signal, timeframe, reasons, strength, trend, volatility, last):
    return {
        "signal": signal,
        "strength": strength,
        "close": f"{float(last.Close):.6f}",
        "trend": trend,
        "rsi": f"{float(last.rsi):.2f}",
        "fast_ma": f"{float(last.fast_ma):.6f}",
        "slow_ma": f"{float(last.slow_ma):.6f}",
        "volatility": volatility,
        "reasons": reasons + [f"Selected timeframe: {timeframe}"],
        "timestamp": datetime.now(PAKISTAN_TZ).strftime("%Y-%m-%d %H:%M:%S PKT"),
    }


def analyze_forex(candles: pd.DataFrame, timeframe: str):
    _, last, trend, direction, strength, volatility = _base_analysis(candles)
    reasons = ["BUY/SELL signal is based on EMA trend, RSI, and the latest candle close."]

    if direction == "up" and volatility == "Normal":
        signal = "BUY"
        reasons.append("Fast EMA is above slow EMA and the latest candle confirms upward momentum.")
    elif direction == "down" and volatility == "Normal":
        signal = "SELL"
        reasons.append("Fast EMA is below slow EMA and the latest candle confirms downward momentum.")
    else:
        signal = "NO TRADE"
        reasons.append("Trend confirmation is weak or volatility is elevated; waiting is safer.")

    return _result(signal, timeframe, reasons, strength, trend, volatility, last)

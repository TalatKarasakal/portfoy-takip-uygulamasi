"""Teknik analiz indikatörleri.

Geçmiş kapanış fiyatlarından SMA, EMA, RSI ve MACD gibi indikatörleri hesaplar
ve bunlardan basit bir trend "sinyali" üretir. Tüm hesaplamalar yerel ve
ücretsizdir (yalnızca numpy/pandas). Bu çıktılar yatırım tavsiyesi değil,
teknik gösterge olarak sunulur.
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


def sma(prices: pd.Series, window: int) -> pd.Series:
    """Basit hareketli ortalama (Simple Moving Average)."""
    return prices.rolling(window=window, min_periods=1).mean()


def ema(prices: pd.Series, window: int) -> pd.Series:
    """Üssel hareketli ortalama (Exponential Moving Average)."""
    return prices.ewm(span=window, adjust=False).mean()


def rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    """Göreceli Güç Endeksi (Relative Strength Index, 0-100)."""
    delta = prices.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi_series = 100.0 - (100.0 / (1.0 + rs))
    # avg_loss 0 ise (sürekli yükseliş) RSI 100 kabul edilir
    rsi_series = rsi_series.where(avg_loss != 0.0, 100.0)
    return rsi_series


def macd(
    prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> Dict[str, pd.Series]:
    """MACD çizgisi, sinyal çizgisi ve histogramı döndürür."""
    macd_line = ema(prices, fast) - ema(prices, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def _to_series(prices: List[float]) -> pd.Series:
    return pd.Series([float(p) for p in prices], dtype="float64")


def compute_indicators(prices: List[float]) -> Dict[str, Any]:
    """Bir fiyat serisi için özet indikatör değerlerini hesaplar.

    Args:
        prices: Kronolojik (eskiden yeniye) kapanış fiyatları.

    Returns:
        Son değerleri ve trend sinyalini içeren sözlük. Yetersiz veri varsa
        ``{"available": False}`` döner.
    """
    if not prices or len(prices) < 15:
        return {"available": False, "reason": "Yeterli geçmiş fiyat verisi yok."}

    series = _to_series(prices)
    sma20 = sma(series, 20)
    sma50 = sma(series, 50)
    rsi14 = rsi(series, 14)
    macd_data = macd(series)

    last_price = float(series.iloc[-1])
    last_rsi = _safe_last(rsi14)
    last_sma20 = _safe_last(sma20)
    last_sma50 = _safe_last(sma50)
    last_macd = _safe_last(macd_data["macd"])
    last_signal = _safe_last(macd_data["signal"])

    signal, reasons = _trend_signal(
        last_price, last_sma20, last_sma50, last_rsi, last_macd, last_signal
    )

    return {
        "available": True,
        "last_price": last_price,
        "sma20": last_sma20,
        "sma50": last_sma50,
        "rsi": last_rsi,
        "macd": last_macd,
        "macd_signal": last_signal,
        "trend": signal,
        "reasons": reasons,
    }


def _safe_last(series: pd.Series) -> Optional[float]:
    """Serinin son geçerli (NaN olmayan) değerini float olarak döndürür."""
    valid = series.dropna()
    if valid.empty:
        return None
    return float(valid.iloc[-1])


def _trend_signal(
    price: float,
    sma20: Optional[float],
    sma50: Optional[float],
    rsi_val: Optional[float],
    macd_val: Optional[float],
    signal_val: Optional[float],
) -> tuple:
    """İndikatörlerden basit bir trend sinyali üretir.

    Returns:
        ("Yükseliş"|"Düşüş"|"Nötr", gerekçe listesi) çifti.
    """
    score = 0
    reasons: List[str] = []

    if sma20 is not None and sma50 is not None:
        if sma20 > sma50:
            score += 1
            reasons.append(
                "Kısa vadeli ortalama (SMA20) uzun vadelinin (SMA50) üzerinde."
            )
        elif sma20 < sma50:
            score -= 1
            reasons.append(
                "Kısa vadeli ortalama (SMA20) uzun vadelinin (SMA50) altında."
            )

    if sma20 is not None:
        if price > sma20:
            score += 1
            reasons.append("Fiyat 20 günlük ortalamanın üzerinde.")
        else:
            score -= 1
            reasons.append("Fiyat 20 günlük ortalamanın altında.")

    if macd_val is not None and signal_val is not None:
        if macd_val > signal_val:
            score += 1
            reasons.append("MACD sinyal çizgisinin üzerinde (pozitif momentum).")
        else:
            score -= 1
            reasons.append("MACD sinyal çizgisinin altında (negatif momentum).")

    if rsi_val is not None:
        if rsi_val >= 70:
            reasons.append(f"RSI {rsi_val:.0f}: aşırı alım bölgesi.")
        elif rsi_val <= 30:
            reasons.append(f"RSI {rsi_val:.0f}: aşırı satım bölgesi.")

    if score >= 2:
        trend = "Yükseliş"
    elif score <= -2:
        trend = "Düşüş"
    else:
        trend = "Nötr"
    return trend, reasons

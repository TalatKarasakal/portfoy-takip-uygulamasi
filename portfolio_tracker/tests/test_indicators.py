"""Teknik indikatör birim testleri."""

import numpy as np
import pandas as pd

from app.services.ml import indicators


def test_sma_basit():
    s = pd.Series([1.0, 2.0, 3.0, 4.0])
    result = indicators.sma(s, 2)
    # min_periods=1 olduğu için ilk değer kendisi
    assert abs(result.iloc[-1] - 3.5) < 1e-9


def test_rsi_surekli_yukselis_100():
    prices = pd.Series([float(i) for i in range(1, 30)])
    rsi = indicators.rsi(prices, 14)
    # Sürekli yükselişte RSI 100'e yakın olmalı
    assert rsi.dropna().iloc[-1] == 100.0


def test_yetersiz_veri():
    res = indicators.compute_indicators([1, 2, 3])
    assert res["available"] is False


def test_yukselis_trendi_tespiti():
    # Düzenli artan seri -> Yükseliş sinyali beklenir
    prices = [100 + i * 1.5 for i in range(60)]
    res = indicators.compute_indicators(prices)
    assert res["available"] is True
    assert res["trend"] == "Yükseliş"
    assert res["sma20"] is not None


def test_dusus_trendi_tespiti():
    prices = [200 - i * 1.5 for i in range(60)]
    res = indicators.compute_indicators(prices)
    assert res["available"] is True
    assert res["trend"] == "Düşüş"


def test_macd_anahtarlari():
    s = pd.Series([float(i) for i in range(1, 50)])
    macd = indicators.macd(s)
    assert set(macd.keys()) == {"macd", "signal", "histogram"}

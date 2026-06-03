"""Anomali tespiti birim testleri."""

import datetime

from app.services.ml import anomaly


def _records(prices):
    base = datetime.date(2024, 1, 1)
    return [
        {"date": base + datetime.timedelta(days=i), "close_price": p}
        for i, p in enumerate(prices)
    ]


def test_yetersiz_veri_bos_doner():
    assert anomaly.detect_anomalies(_records([100, 101, 102])) == []


def test_belirgin_sicrama_tespit_edilir():
    # 30 gün durağan, sonra ani %50 sıçrama
    prices = [100.0 + (i % 2) * 0.1 for i in range(30)]
    prices.append(150.0)  # ani sıçrama
    prices += [150.0 + (i % 2) * 0.1 for i in range(10)]
    anomalies = anomaly.detect_anomalies(_records(prices))
    assert len(anomalies) >= 1
    assert any(a["direction"] == "yükseliş" for a in anomalies)


def test_duragan_seride_anomali_yok():
    prices = [100.0 + (i % 2) * 0.05 for i in range(40)]
    anomalies = anomaly.detect_anomalies(_records(prices))
    assert anomalies == []


def test_describe_bos():
    assert "tespit edilmedi" in anomaly.describe_anomalies([])

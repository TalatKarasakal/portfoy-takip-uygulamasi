"""Olağandışı fiyat hareketi (anomali) tespiti.

Günlük getirilerin istatistiksel dağılımını kullanarak alışılmadık fiyat
sıçramalarını/düşüşlerini yakalar. Yöntem: günlük yüzde getirilerin z-skoru;
eşik aşıldığında anomali işaretlenir. Tamamen yerel ve ücretsizdir.
"""

import datetime
from typing import Any, Dict, List

import numpy as np

# Z-skoru bu eşiği aşan günler anomali sayılır.
DEFAULT_Z_THRESHOLD = 2.5


def detect_anomalies(
    price_records: List[Dict[str, Any]], z_threshold: float = DEFAULT_Z_THRESHOLD
) -> List[Dict[str, Any]]:
    """Fiyat geçmişinde olağandışı günlük hareketleri tespit eder.

    Args:
        price_records: ``{"date": date, "close_price": float}`` kayıtları
            (kronolojik sırada).
        z_threshold: Anomali için günlük getiri z-skoru eşiği.

    Returns:
        Anomali günlerini açıklayan sözlükler listesi. Yetersiz veri ya da
        anomali yoksa boş liste döner.
    """
    if not price_records or len(price_records) < 20:
        return []

    records = sorted(price_records, key=lambda r: r["date"])
    prices = np.array([float(r["close_price"]) for r in records], dtype="float64")

    # Günlük yüzde getiriler
    returns = np.diff(prices) / prices[:-1]
    if returns.size < 2:
        return []

    mean = float(np.mean(returns))
    std = float(np.std(returns))
    if std == 0.0:
        return []

    anomalies: List[Dict[str, Any]] = []
    for i, ret in enumerate(returns):
        z = (ret - mean) / std
        if abs(z) >= z_threshold:
            # returns[i], records[i] -> records[i+1] geçişine ait
            rec = records[i + 1]
            anomalies.append(
                {
                    "date": rec["date"],
                    "change_pct": float(ret * 100.0),
                    "z_score": float(z),
                    "direction": "yükseliş" if ret > 0 else "düşüş",
                    "price": float(rec["close_price"]),
                }
            )
    return anomalies


def describe_anomalies(anomalies: List[Dict[str, Any]]) -> str:
    """Anomali listesini okunabilir Türkçe metne çevirir."""
    if not anomalies:
        return "Olağandışı bir fiyat hareketi tespit edilmedi."
    lines = ["Tespit edilen olağandışı hareketler:"]
    for a in anomalies:
        date_str = (
            a["date"].isoformat()
            if isinstance(a["date"], (datetime.date, datetime.datetime))
            else str(a["date"])
        )
        lines.append(
            f"- {date_str}: %{a['change_pct']:.2f} {a['direction']} "
            f"(z={a['z_score']:.1f})"
        )
    return "\n".join(lines)

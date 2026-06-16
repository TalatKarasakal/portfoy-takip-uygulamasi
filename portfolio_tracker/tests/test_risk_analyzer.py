"""Risk analizi (deterministik) birim testleri."""

from app.services.ai.risk_analyzer import analyze_risk


def _item(code, value, asset_type="BIST"):
    return {"code": code, "name": code, "type": asset_type, "current_value": value}


def test_bos_portfoy_uyari_uretmez():
    assert analyze_risk([]) == []


def test_yuksek_konsantrasyon_tespiti():
    items = [_item("THYAO", 900), _item("GARAN", 100)]
    warnings = analyze_risk(items)
    titles = [w["title"] for w in warnings]
    assert any(w["severity"] == "high" for w in warnings)
    assert "Yüksek Konsantrasyon Riski" in titles


def test_orta_konsantrasyon_tespiti():
    # THYAO %30 -> orta seviye (25-40 arası)
    items = [
        _item("THYAO", 300),
        _item("GARAN", 250),
        _item("AKBNK", 250),
        _item("SISE", 200),
    ]
    warnings = analyze_risk(items)
    assert any(
        w["severity"] == "medium" and "Konsantrasyon" in w["title"] for w in warnings
    )


def test_yetersiz_cesitlendirme():
    items = [_item("THYAO", 100), _item("GARAN", 100)]
    warnings = analyze_risk(items)
    assert any(w["title"] == "Sınırlı Çeşitlendirme" for w in warnings)


def test_dengeli_portfoy_az_uyari():
    # 5 eşit pozisyon: her biri %20, konsantrasyon yok, çeşitlendirme yeterli
    items = [_item(f"A{i}", 100) for i in range(5)]
    warnings = analyze_risk(items)
    # Yüksek/orta konsantrasyon ya da çeşitlendirme uyarısı olmamalı
    assert all(w["title"] != "Sınırlı Çeşitlendirme" for w in warnings)
    assert all(w["severity"] != "high" for w in warnings)


def test_profil_temkinli_daha_hassas():
    # 5 eşit pozisyon (%20): Dengeli'de konsantrasyon uyarısı yok,
    # Temkinli'de %20 >= orta eşik (%15) olduğu için uyarı çıkmalı.
    items = [_item(f"A{i}", 100) for i in range(5)]
    balanced = analyze_risk(items, profile="balanced")
    conservative = analyze_risk(items, profile="conservative")
    assert all("Konsantrasyon" not in w["title"] for w in balanced)
    assert any("Konsantrasyon" in w["title"] for w in conservative)
    # Temkinli min pozisyon 6 -> 5 pozisyon "Sınırlı Çeşitlendirme" verir
    assert any(w["title"] == "Sınırlı Çeşitlendirme" for w in conservative)


def test_profil_atak_daha_toleransli():
    # THYAO %45: Dengeli'de yüksek (>=40), Atak'ta yüksek değil (<55)
    items = [_item("THYAO", 450), _item("GARAN", 250),
             _item("AKBNK", 200), _item("SISE", 100)]
    balanced = analyze_risk(items, profile="balanced")
    aggressive = analyze_risk(items, profile="aggressive")
    assert any(w["severity"] == "high" for w in balanced)
    assert all(w["severity"] != "high" for w in aggressive)

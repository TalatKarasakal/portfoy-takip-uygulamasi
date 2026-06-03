from app.utils.display import display


def test_try_mode_formats_in_lira():
    display.set_mode("TRY")
    display.set_rate(32.0)
    out = display.format(1000.0)
    assert "₺" in out
    # 1.000,00 ₺ (Türkçe biçim)
    assert out.startswith("1.000,00")


def test_usd_mode_converts():
    display.set_mode("USD")
    display.set_rate(40.0)
    out = display.format(4000.0)  # 4000 TL / 40 = 100 USD
    assert "$" in out
    assert out.startswith("100,00")
    display.set_mode("TRY")  # diğer testleri etkilememesi için sıfırla


def test_usd_mode_without_rate_falls_back_to_try():
    display.set_mode("USD")
    display.set_rate(0)
    out = display.format(500.0)
    assert "₺" in out
    display.set_mode("TRY")


def test_format_opposite():
    display.set_mode("TRY")
    display.set_rate(50.0)
    # TRY modunda karşı taraf USD
    assert "$" in display.format_opposite(5000.0)  # 100 USD
    display.set_mode("USD")
    # USD modunda karşı taraf TRY
    assert "₺" in display.format_opposite(5000.0)
    display.set_mode("TRY")

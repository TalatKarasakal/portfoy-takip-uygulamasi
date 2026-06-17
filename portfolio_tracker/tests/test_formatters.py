import pytest
from app.utils.formatters import format_currency, format_percent

def test_format_currency_positive():
    assert format_currency(1234.56) == "1.234,56 ₺"
    assert format_currency(50.00) == "50,00 ₺"

def test_format_currency_negative():
    assert format_currency(-1234.56) == "-1.234,56 ₺"

def test_format_currency_zero():
    assert format_currency(0.0) == "0,00 ₺"

def test_format_currency_large_numbers():
    assert format_currency(1234567.89) == "1.234.567,89 ₺"
    assert format_currency(1234567890.12) == "1.234.567.890,12 ₺"

def test_format_currency_custom_symbol():
    assert format_currency(1234.56, "$") == "1.234,56 $"
    assert format_currency(500.0, "€") == "500,00 €"

def test_format_percent_positive():
    assert format_percent(12.34) == "+12,34%"
    assert format_percent(0.01) == "+0,01%"

def test_format_percent_negative():
    assert format_percent(-12.34) == "-12,34%"
    assert format_percent(-0.01) == "-0,01%"

def test_format_percent_zero():
    assert format_percent(0.0) == "0,00%"

def test_format_percent_large_numbers():
    assert format_percent(1234.56) == "+1.234,56%"
    assert format_percent(-1234.56) == "-1.234,56%"

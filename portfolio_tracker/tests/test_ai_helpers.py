"""LLM yardımcıları, doğal dil ayrıştırma ve bağlam üretimi testleri.

LLM çağrıları sahte (mock) bir sağlayıcıyla taklit edilir; gerçek ağ isteği
yapılmaz.
"""

import datetime

from app.services.ai.llm_provider import LLMProvider, extract_json, get_provider
from app.services.ai import nl_transaction
from app.services.ai.portfolio_context import build_portfolio_context


class FakeProvider(LLMProvider):
    """Testler için sabit yanıt döndüren sahte sağlayıcı."""

    name = "fake"

    def __init__(self, response):
        self._response = response

    def is_available(self):
        return True

    def chat(self, messages, system=None):
        return self._response


def test_extract_json_kod_blogu():
    text = '```json\n{"a": 1, "b": "x"}\n```'
    assert extract_json(text) == {"a": 1, "b": "x"}


def test_extract_json_aciklama_ile():
    text = 'İşte sonuç: {"tx_type": "BUY"} umarım yardımcı olur.'
    assert extract_json(text) == {"tx_type": "BUY"}


def test_extract_json_gecersiz():
    assert extract_json("hiç json yok") is None


def test_get_provider_none():
    assert get_provider({"ai_provider": "none"}) is None


def test_get_provider_ollama():
    p = get_provider({"ai_provider": "ollama", "ai_ollama_model": "qwen2.5"})
    assert p is not None and p.name == "ollama"
    assert p.model == "qwen2.5"


def test_get_provider_gemini():
    p = get_provider({"ai_provider": "gemini", "ai_gemini_api_key": "abc"})
    assert p is not None and p.name == "gemini"


def test_parse_transaction_normalize():
    provider = FakeProvider(
        '{"asset_code": "thyao", "tx_type": "buy", "date": "2024-05-01", '
        '"quantity": 100, "unit_price": 280.5, "commission": 2, "note": "test"}'
    )
    result = nl_transaction.parse_transaction(
        provider, "100 thyao aldım", today=datetime.date(2024, 5, 2)
    )
    assert result["asset_code"] == "THYAO"
    assert result["tx_type"] == "BUY"
    assert result["quantity"] == 100.0
    assert result["unit_price"] == 280.5
    assert result["date"] == "2024-05-01"


def test_parse_transaction_gecersiz_tarih_bugune_doner():
    today = datetime.date(2024, 5, 2)
    provider = FakeProvider(
        '{"asset_code": "AFT", "tx_type": "SELL", "date": "bilinmiyor", '
        '"quantity": 10, "unit_price": 5}'
    )
    result = nl_transaction.parse_transaction(provider, "sat", today=today)
    assert result["date"] == today.isoformat()
    assert result["tx_type"] == "SELL"


def test_build_context_bos():
    assert "kayıtlı bir pozisyon yok" in build_portfolio_context([], {})


def test_build_context_dolu():
    items = [
        {
            "code": "THYAO",
            "name": "Türk Hava Yolları",
            "type": "BIST",
            "quantity": 100,
            "avg_cost": 200.0,
            "current_price": 280.0,
            "total_cost": 20000.0,
            "current_value": 28000.0,
            "unrealized_pnl": 8000.0,
            "portfolio_pct": 100.0,
        }
    ]
    kpi = {
        "total_value_try": 28000.0,
        "total_cost_try": 20000.0,
        "unrealized_pnl": 8000.0,
        "realized_pnl": 0.0,
        "total_pnl": 8000.0,
        "pnl_pct": 40.0,
    }
    context = build_portfolio_context(items, kpi)
    assert "THYAO" in context
    assert "PORTFÖY ÖZETİ" in context

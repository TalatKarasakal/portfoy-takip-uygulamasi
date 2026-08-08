"""LLM yardımcıları, doğal dil ayrıştırma ve bağlam üretimi testleri.

LLM çağrıları sahte (mock) bir sağlayıcıyla taklit edilir; gerçek ağ isteği
yapılmaz.
"""

import datetime

from app.services.ai import nl_transaction
from app.services.ai.llm_provider import LLMProvider, extract_json, get_provider
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
    p = get_provider({"ai_provider": "gemini"}, gemini_api_key="abc")
    assert p is not None and p.name == "gemini"


def test_gemini_uses_api_key_header_not_url(monkeypatch):
    from app.services.ai import llm_provider as mod

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "yanıt"}]}}]}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.update(url=url, headers=headers, payload=json)
        return FakeResponse()

    monkeypatch.setattr(mod.httpx, "post", fake_post)
    provider = mod.GeminiProvider(api_key="super-secret", model="gemini-test")

    assert provider.complete("merhaba") == "yanıt"
    assert "super-secret" not in captured["url"]
    assert "?key=" not in captured["url"]
    assert captured["headers"]["x-goog-api-key"] == "super-secret"


def test_get_provider_local():
    p = get_provider({
        "ai_provider": "local",
        "ai_local_url": "http://localhost:8080/v1/",
        "ai_local_model": "qwen2.5-7b",
    })
    assert p is not None and p.name == "local"
    assert p.base_url == "http://localhost:8080/v1"  # sondaki / temizlenir
    assert p.model == "qwen2.5-7b"


def test_local_provider_chat_parses_openai_response(monkeypatch):
    """OpenAI-uyumlu yanıt biçiminin doğru ayrıştırıldığını doğrular (ağ yok)."""
    from app.services.ai import llm_provider as mod

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [
                    {"message": {"role": "assistant", "content": " Merhaba! "}}
                ]
            }

    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return FakeResponse()

    monkeypatch.setattr(mod.httpx, "post", fake_post)

    p = mod.OpenAICompatibleProvider(base_url="http://localhost:1234/v1", model="m1")
    out = p.chat([{"role": "user", "content": "selam"}], system="sys")

    assert out == "Merhaba!"
    assert captured["url"].endswith("/chat/completions")
    # Sistem talimatı ilk mesaj olarak eklenir
    assert captured["payload"]["messages"][0] == {"role": "system", "content": "sys"}
    assert captured["payload"]["model"] == "m1"


def test_vision_normalize_holdings():
    from app.services.ai.vision_import import normalize_holdings
    data = {"holdings": [
        {"code": "thyao", "type": "bist", "quantity": "100", "avg_cost": "280,5"},
        {"code": "AFT", "quantity": 50, "avg_cost": 12.3},   # tür yok -> sezgi TEFAS
        {"type": "BIST"},                                     # kod yok -> atlanır
    ]}
    out = normalize_holdings(data)
    assert len(out) == 2
    assert out[0]["code"] == "THYAO" and out[0]["type"] == "BIST"
    assert out[0]["quantity"] == 100.0
    assert out[1]["code"] == "AFT" and out[1]["type"] == "TEFAS"  # 3 harf -> TEFAS


def test_vision_extract_holdings_uses_provider(monkeypatch):
    from app.services.ai import vision_import

    class VisionProvider(FakeProvider):
        def supports_vision(self):
            return True

        def analyze_image(self, image_bytes, mime_type, prompt, system=None):
            return self._response

    provider = VisionProvider('{"holdings": [{"code": "GARAN", "type": "BIST", "quantity": 10, "avg_cost": 100}]}')
    out = vision_import.extract_holdings(provider, b"fakebytes", "image/png")
    assert out == [{"code": "GARAN", "type": "BIST", "quantity": 10.0, "avg_cost": 100.0}]


def test_vision_guess_mime():
    from app.services.ai.vision_import import guess_mime
    assert guess_mime("/x/portfoy.PNG") == "image/png"
    assert guess_mime("/x/a.jpeg") == "image/jpeg"
    assert guess_mime("/x/a.unknown") == "image/png"


def test_text_provider_rejects_image():
    from app.services.ai.llm_provider import LLMError
    p = FakeProvider("x")
    import pytest
    with pytest.raises(LLMError):
        p.analyze_image(b"x", "image/png", "prompt")


def test_local_provider_list_models(monkeypatch):
    from app.services.ai import llm_provider as mod

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [{"id": "llama-3.1-8b"}, {"id": "qwen2.5"}]}

    monkeypatch.setattr(mod.httpx, "get", lambda *a, **k: FakeResponse())

    p = mod.OpenAICompatibleProvider()
    assert p.is_available() is True
    assert p.list_models() == ["llama-3.1-8b", "qwen2.5"]


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

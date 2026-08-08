"""LLM sağlayıcı soyutlaması.

Yerel ve bulut sağlayıcıları desteklenir:

* **Ollama** — Kullanıcının kendi makinesinde ve kendi model/lisans
  koşullarıyla çalışan yerel modeller (llama3.1, qwen2.5, gemma2 vb.).
* **Google Gemini** — Fiyat ve kota koşulları sağlayıcıya bağlı olan bulut
  modeli. API anahtarı işletim sisteminin güvenli kasasında tutulur.

Tüm sağlayıcılar `LLMProvider` arayüzünü uygular. Çağrılar `httpx` ile yapılır
(projede zaten mevcut bir bağımlılık), bu yüzden ek paket gerekmez.
"""

import base64
import json
from typing import Dict, List, Optional

import httpx

from app.utils.logger import app_logger, redact_sensitive

# LLM çağrıları yavaş olabileceğinden cömert bir zaman aşımı veriyoruz.
DEFAULT_TIMEOUT = 120.0


class LLMError(Exception):
    """LLM sağlayıcısıyla iletişimde oluşan hatalar için kullanılır."""


class LLMProvider:
    """Tüm LLM sağlayıcılarının uyguladığı temel arayüz."""

    name: str = "base"

    def is_available(self) -> bool:
        """Sağlayıcının kullanılabilir olup olmadığını kontrol eder."""
        raise NotImplementedError

    def chat(self, messages: List[Dict[str, str]], system: Optional[str] = None) -> str:
        """Mesaj listesiyle (rol/içerik) sohbet tamamlaması yapar.

        Args:
            messages: ``[{"role": "user"|"assistant", "content": str}, ...]``
            system: Modelin davranışını yönlendiren sistem talimatı.

        Returns:
            Modelin ürettiği metin.
        """
        raise NotImplementedError

    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        """Tek bir kullanıcı istemi için kısayol."""
        return self.chat([{"role": "user", "content": prompt}], system=system)

    def supports_vision(self) -> bool:
        """Sağlayıcının görüntü (multimodal) desteği olup olmadığını bildirir."""
        return False

    def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        system: Optional[str] = None,
    ) -> str:
        """Bir görüntü + metin istemiyle multimodal tamamlama yapar.

        Görüntü destekleyen sağlayıcılar bunu uygular. Desteklemeyenler
        ``LLMError`` fırlatır.
        """
        raise LLMError(
            f"'{self.name}' sağlayıcısı görüntü analizini desteklemiyor. "
            "Görüntü için Gemini ya da yerelde bir vision modeli (ör. llava, "
            "qwen2-vl) kullanın."
        )


class OllamaProvider(LLMProvider):
    """Yerel Ollama sunucusuyla konuşan sağlayıcı."""

    name = "ollama"

    def __init__(
        self, base_url: str = "http://localhost:11434", model: str = "llama3.1"
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception as e:
            app_logger.debug(f"Ollama erişilemedi: {e}")
            return False

    def list_models(self) -> List[str]:
        """Ollama'da indirilmiş modellerin adlarını döndürür (hata halinde boş)."""
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        except Exception as e:
            app_logger.debug(f"Ollama model listesi alınamadı: {e}")
            return []

    def chat(self, messages: List[Dict[str, str]], system: Optional[str] = None) -> str:
        payload_messages: List[Dict[str, str]] = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        payload_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": payload_messages,
            "stream": False,
        }
        try:
            resp = httpx.post(
                f"{self.base_url}/api/chat", json=payload, timeout=DEFAULT_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
            return (data.get("message", {}) or {}).get("content", "").strip()
        except httpx.HTTPStatusError as e:
            app_logger.error(f"Ollama HTTP hatası: {e}")
            raise LLMError(
                f"Ollama modeli '{self.model}' yanıt vermedi. Modelin indirildiğinden "
                f"emin olun (ör. 'ollama pull {self.model}')."
            )
        except Exception as e:
            app_logger.error(f"Ollama bağlantı hatası: {e}")
            raise LLMError(
                "Ollama'ya bağlanılamadı. Ollama'nın çalıştığından emin olun "
                f"({self.base_url})."
            )

    def supports_vision(self) -> bool:
        return True  # Vision modeli (llava, qwen2-vl...) yüklüyse çalışır

    def analyze_image(self, image_bytes, mime_type, prompt, system=None):
        b64 = base64.b64encode(image_bytes).decode("ascii")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt, "images": [b64]})
        payload = {"model": self.model, "messages": messages, "stream": False}
        try:
            resp = httpx.post(
                f"{self.base_url}/api/chat", json=payload, timeout=DEFAULT_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
            return (data.get("message", {}) or {}).get("content", "").strip()
        except Exception as e:
            app_logger.error(f"Ollama görüntü analizi hatası: {e}")
            raise LLMError(
                f"Ollama görüntü analizi başarısız. '{self.model}' bir vision "
                "modeli mi? (ör. 'ollama pull llava')."
            )


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI API uyumlu yerel sunucularla konuşan sağlayıcı.

    LM Studio, llama.cpp server, Jan, vLLM, GPT4All, text-generation-webui gibi
    araçların tamamı ``/v1/chat/completions`` standardını sunar. Bu sağlayıcı
    sayesinde kullanıcı Ollama dışında hangi yerel yapay zekayı kurarsa kursun
    uygulama onunla çalışabilir.
    """

    name = "local"

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model: str = "",
        api_key: str = "",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key  # Yerel sunucular çoğunlukla anahtar istemez

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def is_available(self) -> bool:
        try:
            resp = httpx.get(
                f"{self.base_url}/models", headers=self._headers(), timeout=5.0
            )
            return resp.status_code == 200
        except Exception as e:
            app_logger.debug(f"Yerel LLM sunucusuna erişilemedi: {e}")
            return False

    def list_models(self) -> List[str]:
        """Sunucuda yüklü modellerin adlarını döndürür (hata halinde boş)."""
        try:
            resp = httpx.get(
                f"{self.base_url}/models", headers=self._headers(), timeout=5.0
            )
            resp.raise_for_status()
            data = resp.json()
            return [m.get("id", "") for m in data.get("data", []) if m.get("id")]
        except Exception as e:
            app_logger.debug(f"Yerel LLM model listesi alınamadı: {e}")
            return []

    def chat(self, messages: List[Dict[str, str]], system: Optional[str] = None) -> str:
        payload_messages: List[Dict[str, str]] = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        payload_messages.extend(messages)

        model = self.model
        if not model:
            # Model belirtilmemişse sunucudaki ilk modeli kullan
            models = self.list_models()
            if models:
                model = models[0]
            else:
                raise LLMError(
                    "Yerel sunucuda yüklü model bulunamadı. Sunucunuzda bir model "
                    "yükleyin veya Ayarlar'dan model adını girin."
                )

        payload = {"model": model, "messages": payload_messages, "stream": False}
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
                timeout=DEFAULT_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise LLMError("Yerel model boş yanıt döndürdü.")
            return (choices[0].get("message", {}) or {}).get("content", "").strip()
        except httpx.HTTPStatusError as e:
            app_logger.error(f"Yerel LLM HTTP hatası: {e}")
            raise LLMError(
                f"Yerel model '{model}' yanıt vermedi (HTTP {e.response.status_code}). "
                "Sunucuda modelin yüklü olduğundan emin olun."
            )
        except LLMError:
            raise
        except Exception as e:
            app_logger.error(f"Yerel LLM bağlantı hatası: {e}")
            raise LLMError(
                f"Yerel yapay zeka sunucusuna bağlanılamadı ({self.base_url}). "
                "LM Studio / llama.cpp / Jan gibi sunucunuzun çalıştığından emin olun."
            )

    def supports_vision(self) -> bool:
        return True  # Sunucuda bir vision modeli yüklüyse çalışır

    def analyze_image(self, image_bytes, mime_type, prompt, system=None):
        b64 = base64.b64encode(image_bytes).decode("ascii")
        model = self.model or (self.list_models() or [""])[0]
        if not model:
            raise LLMError("Yerel sunucuda model bulunamadı.")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url",
                 "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
            ],
        })
        payload = {"model": model, "messages": messages, "stream": False}
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload, headers=self._headers(), timeout=DEFAULT_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise LLMError("Yerel model boş yanıt döndürdü.")
            return (choices[0].get("message", {}) or {}).get("content", "").strip()
        except LLMError:
            raise
        except Exception as e:
            app_logger.error(f"Yerel LLM görüntü analizi hatası: {e}")
            raise LLMError(
                f"Yerel görüntü analizi başarısız. '{model}' bir vision modeli mi?"
            )


class GeminiProvider(LLMProvider):
    """Google Gemini bulut API'sini güvenli header kimlik doğrulamasıyla kullanır."""

    name = "gemini"
    BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str = "", model: str = "gemini-2.0-flash") -> None:
        self.api_key = api_key
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

    def _safe_error(self, error: object) -> str:
        return redact_sensitive(error, (self.api_key,))

    def chat(self, messages: List[Dict[str, str]], system: Optional[str] = None) -> str:
        if not self.api_key:
            raise LLMError("Gemini API anahtarı tanımlı değil. Ayarlar'dan girin.")

        url = f"{self.BASE}/{self.model}:generateContent"
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        payload: Dict = {"contents": contents}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        try:
            resp = httpx.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=DEFAULT_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMError(
                    "Gemini boş yanıt döndürdü (içerik filtrelenmiş olabilir)."
                )
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts).strip()
        except httpx.HTTPStatusError as e:
            detail = ""
            try:
                detail = e.response.json().get("error", {}).get("message", "")
            except Exception:
                pass
            safe_detail = self._safe_error(detail or e)
            app_logger.error("Gemini HTTP hatası: %s", safe_detail)
            raise LLMError(f"Gemini isteği başarısız oldu: {safe_detail}")
        except LLMError:
            raise
        except Exception as e:
            safe_error = self._safe_error(e)
            app_logger.error("Gemini bağlantı hatası: %s", safe_error)
            raise LLMError(f"Gemini'ye bağlanılamadı: {safe_error}")

    def supports_vision(self) -> bool:
        return True  # gemini-2.0-flash/pro multimodaldir

    def analyze_image(self, image_bytes, mime_type, prompt, system=None):
        if not self.api_key:
            raise LLMError("Gemini API anahtarı tanımlı değil. Ayarlar'dan girin.")
        b64 = base64.b64encode(image_bytes).decode("ascii")
        url = f"{self.BASE}/{self.model}:generateContent"
        payload: Dict = {
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": b64}},
                ],
            }]
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        try:
            resp = httpx.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=DEFAULT_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMError("Gemini boş yanıt döndürdü (içerik filtrelenmiş olabilir).")
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts).strip()
        except LLMError:
            raise
        except Exception as e:
            safe_error = self._safe_error(e)
            app_logger.error("Gemini görüntü analizi hatası: %s", safe_error)
            raise LLMError(f"Gemini görüntü analizi başarısız: {safe_error}")


def get_provider(
    settings: Dict[str, str], *, gemini_api_key: Optional[str] = None
) -> Optional[LLMProvider]:
    """Ayar sözlüğüne göre uygun LLM sağlayıcısını oluşturur.

    Returns:
        Yapılandırılmış bir ``LLMProvider`` ya da yapay zeka kapalıysa ``None``.
    """
    provider = (settings.get("ai_provider") or "none").lower()
    if provider == "ollama":
        return OllamaProvider(
            base_url=settings.get("ai_ollama_url", "http://localhost:11434"),
            model=settings.get("ai_ollama_model", "llama3.1"),
        )
    if provider == "local":
        return OpenAICompatibleProvider(
            base_url=settings.get("ai_local_url", "http://localhost:1234/v1"),
            model=settings.get("ai_local_model", ""),
            api_key=settings.get("ai_local_api_key", ""),
        )
    if provider == "gemini":
        from app.services.secret_service import SecretService

        return GeminiProvider(
            api_key=(
                gemini_api_key
                if gemini_api_key is not None
                else SecretService.get_gemini_api_key()
            ),
            model=settings.get("ai_gemini_model", "gemini-2.0-flash"),
        )
    return None


def extract_json(text: str) -> Optional[dict]:
    """Model yanıtından JSON nesnesini ayıklar.

    Modeller bazen JSON'u ```json ... ``` bloğu içinde veya açıklama metniyle
    birlikte döndürür. Bu yardımcı, metindeki ilk geçerli JSON nesnesini bulur.
    """
    if not text:
        return None
    cleaned = text.strip()
    # Markdown kod bloklarını temizle
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    # İlk { ile son } arasını dene
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None

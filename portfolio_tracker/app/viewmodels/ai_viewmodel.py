"""Yapay zeka özelliklerinin ViewModel katmanı.

Sohbet, otomatik özet, doğal dil ile işlem girişi, risk analizi, teknik analiz,
haber duygu analizi ve öneri motorunu yönetir. Tüm uzun süren çağrılar (LLM ve
ağ istekleri) arka planda ``QThread`` içinde çalışır; UI asla donmaz.
"""

import datetime
from typing import Any, Callable, Dict, List

from PySide6.QtCore import QObject, QThread, Signal

from app.database.session import get_session
from app.models.asset import Asset, AssetType
from app.services.ai import advisor, news_sentiment, nl_transaction, vision_import
from app.services.ai.llm_provider import get_provider
from app.services.ai.portfolio_context import SYSTEM_PROMPT, build_portfolio_context
from app.services.ai.risk_analyzer import analyze_risk
from app.services.bist_service import BistService
from app.services.ml import anomaly, indicators
from app.services.secret_service import SecretService
from app.services.tefas_service import TefasService
from app.services.transaction_service import TransactionCommand, TransactionService
from app.utils.app_settings import CLOUD_CONSENT_VERSION, load_settings_dict
from app.utils.logger import app_logger, redact_sensitive


class AIWorker(QThread):
    """Verilen fonksiyonu arka planda çalıştıran genel amaçlı iş parçacığı."""

    result_signal = Signal(str, object)  # (etiket, sonuç)
    error_signal = Signal(str, str)  # (etiket, hata mesajı)

    def __init__(self, tag: str, fn: Callable[[], Any]) -> None:
        super().__init__()
        self.tag = tag
        self.fn = fn

    def run(self) -> None:
        if self.isInterruptionRequested():
            return
        try:
            result = self.fn()
            if not self.isInterruptionRequested():
                self.result_signal.emit(self.tag, result)
        except Exception as e:
            app_logger.error(f"AI işlemi hatası ({self.tag}): {e}")
            self.error_signal.emit(self.tag, redact_sensitive(e))


class AIViewModel(QObject):
    """Yapay zeka özelliklerini yöneten ViewModel."""

    # Sinyaller
    chat_response_ready = Signal(str)
    summary_ready = Signal(str)
    advice_ready = Signal(str)
    risk_ready = Signal(list)
    transaction_parsed = Signal(dict)
    transaction_saved = Signal(str)
    sentiment_ready = Signal(dict)
    analysis_ready = Signal(dict)
    holdings_extracted = Signal(list)
    holdings_imported = Signal(str)
    error_occurred = Signal(str)
    busy_changed = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self.bist_service = BistService()
        self.tefas_service = TefasService()
        self.portfolio_items: List[Dict[str, Any]] = []
        self.kpi_data: Dict[str, Any] = {}
        self.chat_history: List[Dict[str, str]] = []
        self._workers: List[AIWorker] = []
        self.selected_portfolio_id = 1

    def set_portfolio(self, portfolio_id) -> None:
        self.selected_portfolio_id = int(portfolio_id) if portfolio_id is not None else None

    # --- Portföy verisiyle senkronizasyon (PortfolioViewModel sinyalleri) ---

    def update_portfolio_data(self, items: List[Dict[str, Any]]) -> None:
        self.portfolio_items = items or []

    def update_kpi_data(self, kpi: Dict[str, Any]) -> None:
        self.kpi_data = kpi or {}

    # --- Sağlayıcı yardımcıları ---

    def is_ai_enabled(self) -> bool:
        """Yapay zekanın yapılandırılıp yapılandırılmadığını döndürür."""
        settings = load_settings_dict()
        provider = settings.get("ai_provider", "none")
        if provider == "gemini":
            return (
                settings.get("ai_cloud_consent_version") == CLOUD_CONSENT_VERSION
                and SecretService.has_gemini_api_key()
            )
        return provider != "none"

    def cloud_upload_notice_required(self) -> bool:
        """Seçilen sağlayıcı dosyayı cihaz dışına gönderecekse True döndürür."""
        return load_settings_dict().get("ai_provider") == "gemini"

    def _get_provider_or_raise(self):
        settings = load_settings_dict()
        if (
            settings.get("ai_provider") == "gemini"
            and settings.get("ai_cloud_consent_version") != CLOUD_CONSENT_VERSION
        ):
            raise RuntimeError(
                "Gemini kullanılmadan önce Ayarlar bölümündeki bulut veri onayını verin."
            )
        provider = get_provider(settings)
        if provider is None:
            raise RuntimeError(
                "Yapay zeka sağlayıcısı seçilmemiş. Ayarlar > Yapay Zeka "
                "bölümünden Ollama veya Gemini'yi yapılandırın."
            )
        return provider

    # --- Genel iş parçacığı başlatıcı ---

    def _run_async(self, tag: str, fn: Callable[[], Any]) -> None:
        self.busy_changed.emit(True)
        worker = AIWorker(tag, fn)
        worker.result_signal.connect(self._on_result)
        worker.error_signal.connect(self._on_error)
        worker.finished.connect(lambda w=worker: self._cleanup_worker(w))
        self._workers.append(worker)
        worker.start()

    def _cleanup_worker(self, worker: AIWorker) -> None:
        if worker in self._workers:
            self._workers.remove(worker)
        if not self._workers:
            self.busy_changed.emit(False)

    def _on_result(self, tag: str, result: Any) -> None:
        if tag == "chat":
            self.chat_history.append({"role": "assistant", "content": result})
            self.chat_response_ready.emit(result)
        elif tag == "summary":
            self.summary_ready.emit(result)
        elif tag == "advice":
            self.advice_ready.emit(result)
        elif tag == "transaction":
            self.transaction_parsed.emit(result)
        elif tag == "sentiment":
            self.sentiment_ready.emit(result)
        elif tag == "analysis":
            self.analysis_ready.emit(result)
        elif tag == "vision":
            self.holdings_extracted.emit(result)

    def _on_error(self, tag: str, message: str) -> None:
        self.error_occurred.emit(message)

    # --- 1) Portföy asistanı (sohbet) ---

    def send_message(self, text: str) -> None:
        """Kullanıcı mesajını portföy bağlamıyla birlikte LLM'e gönderir."""
        text = text.strip()
        if not text:
            return
        self.chat_history.append({"role": "user", "content": text})
        history = list(self.chat_history)
        context = build_portfolio_context(self.portfolio_items, self.kpi_data)
        system = f"{SYSTEM_PROMPT}\n\nGüncel portföy verisi:\n{context}"

        def task() -> str:
            provider = self._get_provider_or_raise()
            return provider.chat(history, system=system)

        self._run_async("chat", task)

    def clear_chat(self) -> None:
        self.chat_history = []

    # --- 2) Otomatik portföy özeti ---

    def generate_summary(self) -> None:
        """Portföyün güncel durumunu özetleyen kısa bir metin üretir."""
        context = build_portfolio_context(self.portfolio_items, self.kpi_data)

        def task() -> str:
            provider = self._get_provider_or_raise()
            prompt = (
                "Aşağıdaki portföyün durumunu 3-4 cümlelik kısa bir Türkçe "
                "paragrafla özetle. Performansı, dağılımı ve dikkat çeken "
                "noktaları vurgula:\n\n" + context
            )
            return provider.complete(prompt, system=SYSTEM_PROMPT)

        self._run_async("summary", task)

    # --- 3) Doğal dilden işlem girişi ---

    def parse_transaction_text(self, text: str) -> None:
        """Serbest metni yapılandırılmış işlem verisine çevirir (kaydetmez)."""
        known_codes = [item["code"] for item in self.portfolio_items]
        today = datetime.date.today()

        def task() -> Dict[str, Any]:
            provider = self._get_provider_or_raise()
            return nl_transaction.parse_transaction(
                provider, text, today=today, known_codes=known_codes
            )

        self._run_async("transaction", task)

    def save_parsed_transaction(self, data: Dict[str, Any], asset_type: str) -> None:
        """Onaylanan ayrıştırılmış işlemi veritabanına kaydeder.

        Varlık kodu mevcut değilse yeni bir varlık oluşturur.
        """
        try:
            code = data["asset_code"].upper()
            if self.selected_portfolio_id is None:
                raise ValueError("İşlem kaydetmek için belirli bir portföy seçin.")
            with get_session() as session:
                a_type = AssetType.BIST if asset_type == "BIST" else AssetType.TEFAS
                asset = TransactionService.get_or_create_asset(
                    session, code, name=code, asset_type=a_type
                )
                command = TransactionCommand.from_values(
                    portfolio_id=self.selected_portfolio_id,
                    asset_id=asset.id,
                    transaction_type=data["tx_type"],
                    date=data["date"],
                    quantity=data["quantity"],
                    unit_price=data["unit_price"],
                    commission=data.get("commission", 0) or 0,
                    tax=0,
                    note=data.get("note", ""),
                )
                with session.begin_nested():
                    TransactionService.create(session, command)
                session.commit()
            self.transaction_saved.emit(
                f"{code} için {data['tx_type']} işlemi kaydedildi."
            )
        except Exception as e:
            app_logger.error(f"İşlem kaydedilemedi: {e}")
            self.error_occurred.emit(f"İşlem kaydedilemedi: {e}")

    # --- 4) Akıllı risk analizi (deterministik + opsiyonel LLM yorumu) ---

    def analyze_risk(self) -> None:
        """Konsantrasyon ve çeşitlendirme risklerini (LLM'siz) hesaplar.

        Eşikler kullanıcının yatırımcı profiline göre ayarlanır.
        """
        profile = load_settings_dict().get("risk_profile", "balanced")
        warnings = analyze_risk(self.portfolio_items, profile=profile)
        self.risk_ready.emit(warnings)

    # --- 5 & 6) Teknik analiz ve anomali tespiti ---

    def run_technical_analysis(self, asset_code: str, asset_type: str) -> None:
        """Bir varlık için teknik indikatörleri ve anomalileri hesaplar."""

        def task() -> Dict[str, Any]:
            records = self._fetch_history(asset_code, asset_type)
            prices = [r["close_price"] for r in records]
            ind = indicators.compute_indicators(prices)
            anomalies = anomaly.detect_anomalies(records)
            return {
                "code": asset_code,
                "indicators": ind,
                "anomalies": anomalies,
                "anomaly_description": anomaly.describe_anomalies(anomalies),
                "history": records,
            }

        self._run_async("analysis", task)

    def _fetch_history(self, asset_code: str, asset_type: str) -> List[Dict[str, Any]]:
        """BIST/TEFAS için geçmiş fiyatları normalize edilmiş biçimde döndürür."""
        if asset_type == "BIST":
            return self.bist_service.fetch_historical_prices(asset_code, period="1y")
        # TEFAS: anahtar adı "price" -> "close_price" olarak normalize et
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=365)
        raw = self.tefas_service.fetch_historical_prices(asset_code, start, end)
        normalized = []
        for r in raw:
            normalized.append(
                {"date": r.get("date"), "close_price": float(r.get("price", 0.0))}
            )
        normalized.sort(key=lambda x: x["date"])
        return normalized

    # --- 7) Haber duygu analizi ---

    def analyze_news(self, asset_code: str, asset_name: str) -> None:
        """Bir varlık hakkındaki güncel haberlerin duygu analizini yapar."""
        query = f"{asset_code} {asset_name} hisse".strip()

        def task() -> Dict[str, Any]:
            provider = self._get_provider_or_raise()
            headlines = news_sentiment.fetch_headlines(query)
            return news_sentiment.analyze_sentiment(provider, asset_name, headlines)

        self._run_async("sentiment", task)

    # --- 8) Hedef bazlı öneri motoru ---

    def generate_advice(self, goal: str = "") -> None:
        """Portföy için yeniden dengeleme / iyileştirme önerileri üretir."""
        items = list(self.portfolio_items)
        kpi = dict(self.kpi_data)

        profile = load_settings_dict().get("risk_profile", "balanced")

        def task() -> str:
            provider = self._get_provider_or_raise()
            return advisor.generate_advice(provider, items, kpi, goal=goal, profile=profile)

        self._run_async("advice", task)

    # --- 9) Görüntüden portföy aktarımı (vision) ---

    def import_from_image(self, image_path: str) -> None:
        """Bir görüntüden varlıkları çıkarır (arka planda). Kaydetmez."""

        def task() -> List[Dict[str, Any]]:
            provider = self._get_provider_or_raise()
            if not provider.supports_vision():
                from app.services.ai.llm_provider import LLMError
                raise LLMError(
                    f"'{provider.name}' görüntü desteklemiyor. Gemini veya yerelde "
                    "bir vision modeli (llava, qwen2-vl) kullanın."
                )
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            mime = vision_import.guess_mime(image_path)
            return vision_import.extract_holdings(provider, image_bytes, mime)

        self._run_async("vision", task)

    def save_imported_holdings(self, holdings: List[Dict[str, Any]]) -> None:
        """Onaylanan varlık listesini varlık + tek BUY işlemi olarak kaydeder."""
        try:
            if self.selected_portfolio_id is None:
                raise ValueError("İçe aktarmak için belirli bir portföy seçin.")
            count = 0
            with get_session() as session:
                for h in holdings:
                    code = str(h.get("code", "")).strip().upper()
                    if not code:
                        continue
                    a_type = AssetType.BIST if h.get("type") == "BIST" else AssetType.TEFAS
                    asset = TransactionService.get_or_create_asset(
                        session, code, name=code, asset_type=a_type
                    )
                    qty = float(h.get("quantity", 0) or 0)
                    price = float(h.get("avg_cost", 0) or 0)
                    if qty > 0 and price > 0:
                        command = TransactionCommand.from_values(
                            portfolio_id=self.selected_portfolio_id,
                            asset_id=asset.id,
                            transaction_type="BUY",
                            date=datetime.date.today(),
                            quantity=qty,
                            unit_price=price,
                            note="Görüntüden içe aktarıldı",
                        )
                        TransactionService.create(session, command)
                    count += 1
                session.commit()
            self.holdings_imported.emit(f"{count} varlık görüntüden içe aktarıldı.")
        except Exception as e:
            app_logger.error(f"Görüntüden içe aktarma kaydı hatası: {e}")
            self.error_occurred.emit(f"Kaydetme hatası: {e}")

    def get_asset_choices(self) -> List[Dict[str, str]]:
        """Analiz/haber için seçilebilir varlıkları döndürür."""
        try:
            with get_session() as session:
                assets = session.query(Asset).all()
                return [
                    {
                        "code": a.code,
                        "name": a.name,
                        "type": a.asset_type.name,
                    }
                    for a in assets
                ]
        except Exception as e:
            app_logger.error(f"Varlık listesi alınamadı: {e}")
            return []

    def shutdown(self) -> None:
        for worker in list(self._workers):
            if worker.isRunning():
                worker.requestInterruption()
                worker.wait(5000)
        self._workers = [worker for worker in self._workers if worker.isRunning()]

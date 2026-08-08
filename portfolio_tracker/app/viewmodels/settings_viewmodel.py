from PySide6.QtCore import QObject, Signal

from app.database.session import get_session
from app.models.alert import Alert
from app.models.asset import Asset
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.price_history import PriceHistory
from app.models.settings import Settings
from app.models.transaction import Transaction
from app.services.ai.llm_provider import get_provider
from app.services.backup_service import BackupService
from app.services.import_export_service import PORTFOLIO_EXPORT_COLUMNS, ImportExportService
from app.services.report_service import export_cashflow_excel
from app.services.secret_service import SecretService, SecretStoreError
from app.utils.app_settings import CLOUD_CONSENT_VERSION, DEFAULT_SETTINGS
from app.viewmodels.worker import FunctionWorker, stop_worker


class SettingsViewModel(QObject):
    settings_loaded = Signal(dict)
    settings_saved = Signal()
    error_occurred = Signal(str)
    success_message = Signal(str)
    data_wiped = Signal()
    data_changed = Signal()                 # import sonrası portföyü tazele
    percentage_import_needed = Signal(str)  # (dosya yolu) — toplam değer sorulmalı
    import_preview_ready = Signal(object)
    provider_tested = Signal(dict)
    busy_changed = Signal(str, bool)
    task_progress = Signal(str, int)

    # Hassas olmayan varsayılanlar app_settings'te; API anahtarları sistem kasasındadır.
    default_settings = DEFAULT_SETTINGS
    export_columns = PORTFOLIO_EXPORT_COLUMNS

    def __init__(self) -> None:
        super().__init__()
        self._workers: dict[str, FunctionWorker] = {}

    def _run_task(self, tag, task, on_success) -> None:
        current = self._workers.get(tag)
        if current is not None and current.isRunning():
            return
        worker = FunctionWorker(tag, task)
        worker.result_ready.connect(lambda _tag, result: on_success(result))
        worker.error_occurred.connect(self._on_task_error)
        worker.progress_changed.connect(self.task_progress.emit)
        worker.finished.connect(lambda task_tag=tag: self._finish_task(task_tag))
        self._workers[tag] = worker
        self.busy_changed.emit(tag, True)
        worker.start()

    def _on_task_error(self, tag: str, message: str) -> None:
        self.error_occurred.emit(f"{tag}: {message}")

    def _finish_task(self, tag: str) -> None:
        self._workers.pop(tag, None)
        self.busy_changed.emit(tag, False)

    def load_settings(self):
        try:
            with get_session() as session:
                db_settings = session.query(Settings).all()
                settings_dict = self.default_settings.copy()
                for s in db_settings:
                    if s.key != "ai_gemini_api_key":
                        settings_dict[s.key] = s.value
                settings_dict["ai_secret_store_available"] = (
                    "1" if SecretService.is_available() else "0"
                )
                settings_dict["ai_gemini_key_configured"] = (
                    "1" if SecretService.has_gemini_api_key() else "0"
                )
                self.settings_loaded.emit(settings_dict)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def save_settings(self, new_settings: dict):
        try:
            payload = dict(new_settings)
            gemini_key = str(payload.pop("ai_gemini_api_key", "")).strip()
            clear_gemini_key = str(payload.pop("ai_gemini_clear_key", "0")) == "1"
            if payload.get("ai_provider") == "gemini":
                if payload.get("ai_cloud_consent_version") != CLOUD_CONSENT_VERSION:
                    raise ValueError("Gemini etkinleştirilmeden önce bulut veri onayı gerekir.")
                if not SecretService.is_available():
                    raise SecretStoreError(
                        "Güvenli sistem anahtar kasası kullanılamadığı için Gemini devre dışı."
                    )
                if not gemini_key and not SecretService.has_gemini_api_key():
                    raise ValueError("Gemini için API anahtarı girin.")
            if clear_gemini_key:
                SecretService.delete_gemini_api_key()
            elif gemini_key:
                SecretService.set_gemini_api_key(gemini_key)

            with get_session() as session:
                # Eski sürümlerde kalmış olabilecek düz metin sırrı da temizle.
                session.query(Settings).filter(
                    Settings.key == "ai_gemini_api_key"
                ).delete()
                if payload:
                    existing_settings = (
                        session.query(Settings)
                        .filter(Settings.key.in_(payload.keys()))
                        .all()
                    )
                    existing_dict = {s.key: s for s in existing_settings}
                    for k, v in payload.items():
                        if k in existing_dict:
                            existing_dict[k].value = str(v)
                        else:
                            session.add(Settings(key=k, value=str(v)))
                session.commit()
            self.settings_saved.emit()
            self.load_settings()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def export_data(
        self, file_path: str, columns=None, portfolio_items=None, portfolio_id=1
    ):
        selected_columns = tuple(columns or ())
        render_items = tuple(dict(item) for item in (portfolio_items or ()))

        def task():
            with get_session() as session:
                ImportExportService.export_excel(
                    session,
                    file_path,
                    portfolio_items=list(render_items),
                    columns=list(selected_columns),
                    portfolio_id=portfolio_id,
                )
            return "Dışa aktarma işlemi başarıyla tamamlandı."

        self._run_task("Dışa aktarma", task, self.success_message.emit)

    def import_data(self, file_path: str, portfolio_id: int = 1):
        def task():
            if ImportExportService.detect_percentage(file_path):
                return ("percentage", file_path)
            with get_session() as session:
                return ("preview", ImportExportService.preview_excel(session, file_path, portfolio_id))

        def on_success(result):
            result_type, payload = result
            if result_type == "percentage":
                self.percentage_import_needed.emit(payload)
            else:
                self.import_preview_ready.emit(payload)

        self._run_task("İçe aktarma önizlemesi", task, on_success)

    def apply_import_preview(self, preview, selected_rows):
        selected = tuple(selected_rows)

        def task():
            with get_session() as session:
                with session.begin():
                    return ImportExportService.apply_preview(session, preview, selected)

        def on_success(result):
            self.success_message.emit(
                f"{result.imported_count} kayıt içe aktarıldı. Batch: {result.batch_id}"
            )
            self.data_changed.emit()

        self._run_task("İçe aktarma", task, on_success)

    def undo_last_import(self, portfolio_id=None):
        def task():
            with get_session() as session:
                with session.begin():
                    return ImportExportService.undo_last_import(session, portfolio_id)

        def on_success(count):
            self.success_message.emit(f"Son içe aktarım geri alındı ({count} kayıt).")
            self.data_changed.emit()

        self._run_task("İçe aktarımı geri alma", task, on_success)

    def import_percentage(self, file_path: str, total_value: float, portfolio_id: int = 1):
        def task():
            with get_session() as session:
                return ImportExportService.import_percentage(
                    session, file_path, total_value, portfolio_id
                )

        def on_success(success):
            if success:
                self.success_message.emit("Yüzdelik portföy başarıyla içeri aktarıldı.")
                self.data_changed.emit()
            else:
                self.error_occurred.emit("Yüzdelik içeri aktarma başarısız oldu.")

        self._run_task("Yüzdelik içe aktarma", task, on_success)

    def export_cashflow_report(self, file_path: str):
        def task():
            with get_session() as session:
                return export_cashflow_excel(session, file_path)

        def on_success(ok):
            if ok:
                self.success_message.emit("Aylık nakit akışı raporu oluşturuldu.")
            else:
                self.error_occurred.emit("Rapor için işlem kaydı bulunamadı.")

        self._run_task("Rapor", task, on_success)

    def create_backup(self):
        def on_success(result):
            if result:
                self.success_message.emit(f"Veritabanı yedeği doğrulandı: {result.path}")
            else:
                self.error_occurred.emit(result.error or "Yedek alınamadı.")

        self._run_task("Yedekleme", BackupService.create_backup, on_success)

    def restore_backup(self, path: str):
        def on_success(result):
            if result:
                self.success_message.emit("Veritabanı başarıyla geri yüklendi. Uygulamayı yeniden başlatın.")
            else:
                self.error_occurred.emit(result.error or "Geri yükleme başarısız oldu.")

        self._run_task("Geri yükleme", lambda: BackupService.restore_backup(path), on_success)

    def test_ai_provider(self, settings: dict, gemini_api_key: str = "") -> None:
        safe_settings = dict(settings)

        def task():
            provider = get_provider(
                safe_settings,
                **({"gemini_api_key": gemini_api_key} if gemini_api_key else {}),
            )
            if provider is None:
                return {"name": "none", "available": False, "models": []}
            available = provider.is_available()
            models = provider.list_models() if hasattr(provider, "list_models") else []
            return {"name": provider.name, "available": available, "models": models}

        self._run_task("Sağlayıcı bağlantı testi", task, self.provider_tested.emit)

    def cancel_task(self, tag: str) -> None:
        worker = self._workers.get(tag)
        if worker is not None:
            worker.requestInterruption()

    def shutdown(self) -> None:
        for worker in list(self._workers.values()):
            stop_worker(worker)
        self._workers.clear()

    def delete_all_data(self):
        """Tüm portföy verisini siler. Güvenlik için önce otomatik yedek alınır."""
        def task():
            backup_result = BackupService.create_backup()
            if not backup_result:
                raise RuntimeError(
                    "Güvenlik yedeği alınamadığı için hiçbir veri silinmedi. "
                    + backup_result.error
                )
            with get_session() as session:
                # Sıra önemli değil (cascade var) ama açıkça temizleyelim
                session.query(Alert).delete()
                session.query(Transaction).delete()
                session.query(PriceHistory).delete()
                session.query(PortfolioSnapshot).delete()
                session.query(Asset).delete()
                session.commit()
            return "Tüm veri silindi. (Silmeden önce otomatik yedek alındı.)"

        def on_success(message):
            self.success_message.emit(message)
            self.data_wiped.emit()

        self._run_task("Tüm veriyi silme", task, on_success)

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QComboBox,
                                 QPushButton, QLabel, QGroupBox, QHBoxLayout, QFileDialog,
                                 QMessageBox, QCheckBox, QScrollArea, QDialog, QInputDialog,
                                 QApplication, QLineEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

from app.services.import_export_service import PORTFOLIO_EXPORT_COLUMNS

APP_VERSION = "1.0.0"

# Yatırımcı profili: anahtar -> Türkçe etiket
RISK_PROFILE_LABELS = {
    "conservative": "Temkinli",
    "balanced": "Dengeli",
    "aggressive": "Atak",
}


class ExportColumnsDialog(QDialog):
    """Dışa aktarılacak portföy sütunlarını seçtiren diyalog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dışa Aktarılacak Sütunlar")
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Portföy sayfasına eklenecek sütunlar:"))

        self.checks = {}
        for col in PORTFOLIO_EXPORT_COLUMNS:
            cb = QCheckBox(col)
            cb.setChecked(True)
            self.checks[col] = cb
            layout.addWidget(cb)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("İptal")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Dışa Aktar")
        ok.clicked.connect(self.accept)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        layout.addLayout(btns)

    def selected_columns(self):
        return [c for c, cb in self.checks.items() if cb.isChecked()]


class SettingsView(QWidget):
    def __init__(self, view_model, portfolio_vm=None):
        super().__init__()
        self.view_model = view_model
        self.portfolio_vm = portfolio_vm

        # Kaydırılabilir içerik (küçük pencerelerde taşmasın)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(18)

        # --- Temel Ayarlar ---
        group_basic = QGroupBox("Temel Ayarlar")
        form_basic = QFormLayout(group_basic)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["system", "light", "dark"])
        form_basic.addRow("Tema:", self.theme_combo)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["TRY", "USD"])
        form_basic.addRow("Varsayılan Para Birimi:", self.currency_combo)

        self.refresh_combo = QComboBox()
        self.refresh_combo.addItems(["15", "30", "60", "Manuel"])
        form_basic.addRow("Yenileme Sıklığı (dk):", self.refresh_combo)

        self.cost_method_combo = QComboBox()
        self.cost_method_combo.addItems(["WAC", "FIFO", "LIFO"])
        form_basic.addRow("Maliyet Metodu:", self.cost_method_combo)

        self.notifications_check = QCheckBox("Uyarı bildirimleri açık")
        form_basic.addRow("Bildirimler:", self.notifications_check)

        # Yatırımcı profili (risk eşiklerini ve YZ önerilerini etkiler)
        self.risk_profile_combo = QComboBox()
        for key, label in RISK_PROFILE_LABELS.items():
            self.risk_profile_combo.addItem(label, key)
        form_basic.addRow("Yatırımcı Profili:", self.risk_profile_combo)

        layout.addWidget(group_basic)

        # --- Yapay Zeka Ayarları ---
        group_ai = QGroupBox("Yapay Zeka")
        form_ai = QFormLayout(group_ai)

        self.ai_provider_combo = QComboBox()
        # none: kapalı, ollama: yerel ücretsiz, local: diğer yerel sunucular
        # (LM Studio, llama.cpp, Jan...), gemini: ücretsiz bulut katmanı
        self.ai_provider_combo.addItems(["none", "ollama", "local", "gemini"])
        form_ai.addRow("Sağlayıcı:", self.ai_provider_combo)

        self.ai_ollama_url_edit = QLineEdit()
        self.ai_ollama_url_edit.setPlaceholderText("http://localhost:11434")
        form_ai.addRow("Ollama Adresi:", self.ai_ollama_url_edit)

        self.ai_ollama_model_edit = QLineEdit()
        self.ai_ollama_model_edit.setPlaceholderText("llama3.1")
        form_ai.addRow("Ollama Modeli:", self.ai_ollama_model_edit)

        self.ai_local_url_edit = QLineEdit()
        self.ai_local_url_edit.setPlaceholderText("http://localhost:1234/v1")
        form_ai.addRow("Yerel Sunucu Adresi:", self.ai_local_url_edit)

        self.ai_local_model_edit = QLineEdit()
        self.ai_local_model_edit.setPlaceholderText("boş bırakılırsa ilk model kullanılır")
        form_ai.addRow("Yerel Model:", self.ai_local_model_edit)

        self.ai_gemini_key_edit = QLineEdit()
        self.ai_gemini_key_edit.setEchoMode(QLineEdit.Password)
        self.ai_gemini_key_edit.setPlaceholderText("Gemini API anahtarı")
        form_ai.addRow("Gemini API Anahtarı:", self.ai_gemini_key_edit)

        self.ai_gemini_model_edit = QLineEdit()
        self.ai_gemini_model_edit.setPlaceholderText("gemini-1.5-flash")
        form_ai.addRow("Gemini Modeli:", self.ai_gemini_model_edit)

        self.btn_test_ai = QPushButton("Bağlantıyı Sına")
        self.btn_test_ai.clicked.connect(self.on_test_ai_clicked)
        form_ai.addRow("", self.btn_test_ai)

        ai_hint = QLabel(
            "Ollama yerelde tamamen ücretsizdir (ollama.com). 'local' seçeneği "
            "LM Studio, llama.cpp, Jan gibi OpenAI-uyumlu yerel sunucularla "
            "çalışır. Gemini'nin ücretsiz katmanı için API anahtarı: "
            "aistudio.google.com/app/apikey"
        )
        ai_hint.setWordWrap(True)
        ai_hint.setStyleSheet("color: #6B7280; font-size: 11px;")
        form_ai.addRow(ai_hint)

        layout.addWidget(group_ai)

        # --- Veri Yönetimi ---
        group_data = QGroupBox("Veri Yönetimi")
        data_v = QVBoxLayout(group_data)
        data_layout = QHBoxLayout()

        self.btn_backup = QPushButton("Yedek Al")
        self.btn_restore = QPushButton("Yedekten Dön")
        self.btn_export = QPushButton("Excel'e Aktar")
        self.btn_import = QPushButton("Yükle")

        self.btn_backup.clicked.connect(self.on_backup_clicked)
        self.btn_restore.clicked.connect(self.on_restore_clicked)
        self.btn_export.clicked.connect(self.on_export_clicked)
        self.btn_import.clicked.connect(self.on_import_clicked)

        for b in (self.btn_backup, self.btn_restore, self.btn_export, self.btn_import):
            data_layout.addWidget(b)
        data_v.addLayout(data_layout)

        self.btn_cashflow = QPushButton("Aylık Nakit Akışı Raporu (Excel)")
        self.btn_cashflow.clicked.connect(self.on_cashflow_clicked)
        data_v.addWidget(self.btn_cashflow)

        self.btn_delete_all = QPushButton("Tüm Veriyi Sil")
        self.btn_delete_all.setStyleSheet(
            "QPushButton { color: #DC2626; font-weight: bold; }"
        )
        self.btn_delete_all.clicked.connect(self.on_delete_all_clicked)
        data_v.addWidget(self.btn_delete_all)

        layout.addWidget(group_data)

        # Save Button
        self.btn_save = QPushButton("Ayarları Kaydet")
        self.btn_save.setStyleSheet(
            "background-color: #E30A17; color: white; padding: 10px; border-radius: 4px;"
        )
        self.btn_save.clicked.connect(self.save_settings)
        layout.addWidget(self.btn_save)

        # --- Hakkında ---
        group_about = QGroupBox("Hakkında")
        about_v = QVBoxLayout(group_about)
        about_v.addWidget(QLabel(f"Portföy Takip ve Analiz — Sürüm {APP_VERSION}"))
        about_v.addWidget(QLabel("Geliştirici: Kişisel kullanım"))
        about_v.addWidget(QLabel("Lisans: Kişisel / LGPL (PySide6)"))
        about_v.addWidget(QLabel("Veri kaynakları: TEFAS, yfinance (BIST), TCMB (kur)"))
        layout.addWidget(group_about)

        layout.addStretch()

        self.view_model.settings_loaded.connect(self.on_settings_loaded)
        self.view_model.success_message.connect(self.on_success)
        self.view_model.error_occurred.connect(self.on_error)
        self.view_model.percentage_import_needed.connect(self.on_percentage_import_needed)
        # Not: load_settings() MainWindow tarafından kurulum tamamlandıktan sonra
        # çağrılır; burada çağırmak view'lar/timer hazır olmadan sinyal tetikler.

    def on_settings_loaded(self, settings: dict):
        self.theme_combo.setCurrentText(settings.get("theme", "system"))
        self.currency_combo.setCurrentText(settings.get("default_currency", "TRY"))
        self.refresh_combo.setCurrentText(settings.get("refresh_interval_minutes", "15"))
        self.cost_method_combo.setCurrentText(settings.get("cost_method", "WAC"))
        self.notifications_check.setChecked(
            str(settings.get("notifications_enabled", "1")) in ("1", "True", "true")
        )
        ri = self.risk_profile_combo.findData(settings.get("risk_profile", "balanced"))
        if ri >= 0:
            self.risk_profile_combo.setCurrentIndex(ri)

        # Yapay zeka ayarları
        self.ai_provider_combo.setCurrentText(settings.get("ai_provider", "none"))
        self.ai_ollama_url_edit.setText(settings.get("ai_ollama_url", "http://localhost:11434"))
        self.ai_ollama_model_edit.setText(settings.get("ai_ollama_model", "llama3.1"))
        self.ai_local_url_edit.setText(settings.get("ai_local_url", "http://localhost:1234/v1"))
        self.ai_local_model_edit.setText(settings.get("ai_local_model", ""))
        self.ai_gemini_key_edit.setText(settings.get("ai_gemini_api_key", ""))
        self.ai_gemini_model_edit.setText(settings.get("ai_gemini_model", "gemini-1.5-flash"))

    def save_settings(self):
        new_s = {
            "theme": self.theme_combo.currentText(),
            "default_currency": self.currency_combo.currentText(),
            "refresh_interval_minutes": self.refresh_combo.currentText(),
            "cost_method": self.cost_method_combo.currentText(),
            "notifications_enabled": "1" if self.notifications_check.isChecked() else "0",
            "risk_profile": self.risk_profile_combo.currentData(),
            "ai_provider": self.ai_provider_combo.currentText(),
            "ai_ollama_url": self.ai_ollama_url_edit.text().strip() or "http://localhost:11434",
            "ai_ollama_model": self.ai_ollama_model_edit.text().strip() or "llama3.1",
            "ai_local_url": self.ai_local_url_edit.text().strip() or "http://localhost:1234/v1",
            "ai_local_model": self.ai_local_model_edit.text().strip(),
            "ai_gemini_api_key": self.ai_gemini_key_edit.text().strip(),
            "ai_gemini_model": self.ai_gemini_model_edit.text().strip() or "gemini-1.5-flash",
        }
        self.view_model.save_settings(new_s)

    def _current_ai_form_settings(self) -> dict:
        """Formdaki (henüz kaydedilmemiş olabilecek) yapay zeka ayarlarını döndürür."""
        return {
            "ai_provider": self.ai_provider_combo.currentText(),
            "ai_ollama_url": self.ai_ollama_url_edit.text().strip() or "http://localhost:11434",
            "ai_ollama_model": self.ai_ollama_model_edit.text().strip() or "llama3.1",
            "ai_local_url": self.ai_local_url_edit.text().strip() or "http://localhost:1234/v1",
            "ai_local_model": self.ai_local_model_edit.text().strip(),
            "ai_local_api_key": "",
            "ai_gemini_api_key": self.ai_gemini_key_edit.text().strip(),
            "ai_gemini_model": self.ai_gemini_model_edit.text().strip() or "gemini-1.5-flash",
        }

    def on_test_ai_clicked(self):
        """Seçili sağlayıcıya bağlantıyı dener; varsa model listesini gösterir.

        Formdaki güncel değerlerle test eder, böylece kullanıcı kaydetmeden
        önce yapılandırmayı doğrulayabilir.
        """
        from app.services.ai.llm_provider import get_provider

        provider = get_provider(self._current_ai_form_settings())
        if provider is None:
            QMessageBox.information(
                self, "Yapay Zeka",
                "Sağlayıcı 'none' seçili. Önce ollama, local veya gemini seçin."
            )
            return

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            available = provider.is_available()
            models = provider.list_models() if hasattr(provider, "list_models") else []
        finally:
            QApplication.restoreOverrideCursor()

        if available:
            msg = f"'{provider.name}' sağlayıcısına bağlantı başarılı."
            if models:
                shown = ", ".join(models[:10])
                more = f" (+{len(models) - 10} model daha)" if len(models) > 10 else ""
                msg += f"\n\nYüklü modeller: {shown}{more}"
            elif provider.name in ("ollama", "local"):
                msg += (
                    "\n\nAncak yüklü model görünmüyor. Bir model indirin "
                    "(örn. 'ollama pull llama3.1')."
                )
            QMessageBox.information(self, "Bağlantı Testi", msg)
        else:
            tips = {
                "ollama": "Ollama'nın çalıştığından emin olun (uygulamayı açın veya "
                          "'ollama serve' komutunu çalıştırın).",
                "local": "LM Studio / llama.cpp / Jan sunucunuzun açık ve adresin "
                         "doğru olduğundan emin olun.",
                "gemini": "API anahtarını girdiğinizden emin olun.",
            }
            QMessageBox.warning(
                self, "Bağlantı Testi",
                f"'{provider.name}' sağlayıcısına ulaşılamadı.\n\n"
                + tips.get(provider.name, "")
            )

    def on_backup_clicked(self):
        self.view_model.create_backup()

    def on_restore_clicked(self):
        path, _ = QFileDialog.getOpenFileName(self, "Yedek Seç", "", "SQLite DB (*.db)")
        if path:
            confirm = QMessageBox.question(
                self, "Onay",
                "Mevcut veri seçilen yedekle değiştirilecek. Devam edilsin mi?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                self.view_model.restore_backup(path)

    def on_export_clicked(self):
        col_dialog = ExportColumnsDialog(self)
        if not col_dialog.exec():
            return
        columns = col_dialog.selected_columns()
        if not columns:
            QMessageBox.warning(self, "Hata", "En az bir sütun seçmelisiniz.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Excel'e Aktar", "portfoy.xlsx", "Excel (*.xlsx)")
        if path:
            items = self.portfolio_vm.cached_portfolio_data if self.portfolio_vm else None
            self.view_model.export_data(path, columns=columns, portfolio_items=items)

    def on_import_clicked(self):
        path, _ = QFileDialog.getOpenFileName(self, "Excel Seç", "", "Excel (*.xlsx)")
        if path:
            self.view_model.import_data(path)

    def on_percentage_import_needed(self, path):
        total, ok = QInputDialog.getDouble(
            self, "Toplam Portföy Değeri",
            "Yüzdelik dağılım tespit edildi.\nToplam portföy değerini (TL) girin:",
            100000.0, 0.0, 1_000_000_000.0, 2
        )
        if not ok or total <= 0:
            return
        # Güncel fiyat çekimi sürebilir; bekleme imleci göster
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            self.view_model.import_percentage(path, total)
        finally:
            QApplication.restoreOverrideCursor()

    def on_cashflow_clicked(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Aylık Nakit Akışı Raporu", "nakit_akisi.xlsx", "Excel (*.xlsx)"
        )
        if path:
            self.view_model.export_cashflow_report(path)

    def on_delete_all_clicked(self):
        confirm = QMessageBox.warning(
            self, "Dikkat",
            "TÜM varlıklar, işlemler ve uyarılar kalıcı olarak silinecek.\n"
            "(Silmeden önce otomatik yedek alınır.)\n\nDevam edilsin mi?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return
        second = QMessageBox.warning(
            self, "Son Onay", "Bu işlem geri alınamaz. Emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if second == QMessageBox.Yes:
            self.view_model.delete_all_data()

    def on_success(self, msg):
        QMessageBox.information(self, "Başarılı", msg)

    def on_error(self, msg):
        QMessageBox.warning(self, "Hata", msg)

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QComboBox,
                                 QPushButton, QLabel, QGroupBox, QHBoxLayout, QFileDialog,
                                 QMessageBox, QCheckBox, QScrollArea, QDialog, QInputDialog,
                                 QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

from app.services.import_export_service import PORTFOLIO_EXPORT_COLUMNS

APP_VERSION = "1.0.0"


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

        layout.addWidget(group_basic)

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

    def save_settings(self):
        new_s = {
            "theme": self.theme_combo.currentText(),
            "default_currency": self.currency_combo.currentText(),
            "refresh_interval_minutes": self.refresh_combo.currentText(),
            "cost_method": self.cost_method_combo.currentText(),
            "notifications_enabled": "1" if self.notifications_check.isChecked() else "0",
        }
        self.view_model.save_settings(new_s)

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

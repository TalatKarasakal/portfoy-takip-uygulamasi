from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QComboBox,
                                 QPushButton, QLabel, QGroupBox, QHBoxLayout, QFileDialog,
                                 QMessageBox, QLineEdit)

class SettingsView(QWidget):
    def __init__(self, view_model):
        super().__init__()
        self.view_model = view_model

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
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
        
        layout.addWidget(group_basic)

        # --- Yapay Zeka Ayarları ---
        group_ai = QGroupBox("Yapay Zeka")
        form_ai = QFormLayout(group_ai)

        self.ai_provider_combo = QComboBox()
        # none: kapalı, ollama: yerel ücretsiz, gemini: ücretsiz katman
        self.ai_provider_combo.addItems(["none", "ollama", "gemini"])
        form_ai.addRow("Sağlayıcı:", self.ai_provider_combo)

        self.ai_ollama_url_edit = QLineEdit()
        self.ai_ollama_url_edit.setPlaceholderText("http://localhost:11434")
        form_ai.addRow("Ollama Adresi:", self.ai_ollama_url_edit)

        self.ai_ollama_model_edit = QLineEdit()
        self.ai_ollama_model_edit.setPlaceholderText("llama3.1")
        form_ai.addRow("Ollama Modeli:", self.ai_ollama_model_edit)

        self.ai_gemini_key_edit = QLineEdit()
        self.ai_gemini_key_edit.setEchoMode(QLineEdit.Password)
        self.ai_gemini_key_edit.setPlaceholderText("Gemini API anahtarı")
        form_ai.addRow("Gemini API Anahtarı:", self.ai_gemini_key_edit)

        self.ai_gemini_model_edit = QLineEdit()
        self.ai_gemini_model_edit.setPlaceholderText("gemini-1.5-flash")
        form_ai.addRow("Gemini Modeli:", self.ai_gemini_model_edit)

        ai_hint = QLabel(
            "Ollama yerelde tamamen ücretsizdir (ollama.com). Gemini'nin ücretsiz "
            "katmanı için API anahtarı: aistudio.google.com/app/apikey"
        )
        ai_hint.setWordWrap(True)
        ai_hint.setStyleSheet("color: #6B7280; font-size: 11px;")
        form_ai.addRow(ai_hint)

        layout.addWidget(group_ai)

        # --- Veri Yönetimi ---
        group_data = QGroupBox("Veri Yönetimi")
        data_layout = QHBoxLayout(group_data)
        
        self.btn_backup = QPushButton("Yedek Al")
        self.btn_restore = QPushButton("Yedekten Dön")
        self.btn_export = QPushButton("Excel'e Aktar")
        self.btn_import = QPushButton("Yükle")
        
        self.btn_backup.clicked.connect(self.on_backup_clicked)
        self.btn_restore.clicked.connect(self.on_restore_clicked)
        self.btn_export.clicked.connect(self.on_export_clicked)
        self.btn_import.clicked.connect(self.on_import_clicked)
        
        data_layout.addWidget(self.btn_backup)
        data_layout.addWidget(self.btn_restore)
        data_layout.addWidget(self.btn_export)
        data_layout.addWidget(self.btn_import)
        
        layout.addWidget(group_data)
        
        # Save Button
        self.btn_save = QPushButton("Ayarları Kaydet")
        self.btn_save.setStyleSheet("background-color: #E30A17; color: white; padding: 10px; border-radius: 4px;")
        self.btn_save.clicked.connect(self.save_settings)
        layout.addWidget(self.btn_save)
        
        layout.addStretch()
        
        self.view_model.settings_loaded.connect(self.on_settings_loaded)
        self.view_model.success_message.connect(self.on_success)
        self.view_model.error_occurred.connect(self.on_error)
        self.view_model.load_settings()
        
    def on_settings_loaded(self, settings: dict):
        self.theme_combo.setCurrentText(settings.get("theme", "dark"))
        self.currency_combo.setCurrentText(settings.get("default_currency", "TRY"))
        self.refresh_combo.setCurrentText(settings.get("refresh_interval_minutes", "15"))
        self.cost_method_combo.setCurrentText(settings.get("cost_method", "WAC"))

        # Yapay zeka ayarları
        self.ai_provider_combo.setCurrentText(settings.get("ai_provider", "none"))
        self.ai_ollama_url_edit.setText(settings.get("ai_ollama_url", "http://localhost:11434"))
        self.ai_ollama_model_edit.setText(settings.get("ai_ollama_model", "llama3.1"))
        self.ai_gemini_key_edit.setText(settings.get("ai_gemini_api_key", ""))
        self.ai_gemini_model_edit.setText(settings.get("ai_gemini_model", "gemini-1.5-flash"))

    def save_settings(self):
        new_s = {
            "theme": self.theme_combo.currentText(),
            "default_currency": self.currency_combo.currentText(),
            "refresh_interval_minutes": self.refresh_combo.currentText(),
            "cost_method": self.cost_method_combo.currentText(),
            "ai_provider": self.ai_provider_combo.currentText(),
            "ai_ollama_url": self.ai_ollama_url_edit.text().strip() or "http://localhost:11434",
            "ai_ollama_model": self.ai_ollama_model_edit.text().strip() or "llama3.1",
            "ai_gemini_api_key": self.ai_gemini_key_edit.text().strip(),
            "ai_gemini_model": self.ai_gemini_model_edit.text().strip() or "gemini-1.5-flash",
        }
        self.view_model.save_settings(new_s)

    def on_backup_clicked(self):
        self.view_model.create_backup()

    def on_restore_clicked(self):
        path, _ = QFileDialog.getOpenFileName(self, "Yedek Seç", "", "SQLite DB (*.db)")
        if path:
            self.view_model.restore_backup(path)

    def on_export_clicked(self):
        path, _ = QFileDialog.getSaveFileName(self, "Excel'e Aktar", "portfoy.xlsx", "Excel (*.xlsx)")
        if path:
            self.view_model.export_data(path)

    def on_import_clicked(self):
        path, _ = QFileDialog.getOpenFileName(self, "Excel Seç", "", "Excel (*.xlsx)")
        if path:
            self.view_model.import_data(path)

    def on_success(self, msg):
        QMessageBox.information(self, "Başarılı", msg)

    def on_error(self, msg):
        QMessageBox.warning(self, "Hata", msg)

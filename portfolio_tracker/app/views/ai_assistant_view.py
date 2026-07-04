"""Yapay Zeka Asistanı görünümü.

Tek bir sekmeli arayüzde tüm yapay zeka özelliklerini sunar:
- Sohbet asistanı ve otomatik özet
- Risk taraması ve hedef bazlı öneri
- Teknik analiz (indikatörler + anomali)
- Haber duygu analizi
- Doğal dil ile işlem girişi
"""

from typing import Any, Dict, List

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.services.ml import anomaly as anomaly_mod
from app.utils.formatters import format_currency

_SEVERITY_COLORS = {"high": "#B91C1C", "medium": "#D97706", "info": "#00B5E2"}


class AIAssistantView(QWidget):
    """Yapay zeka özelliklerinin toplandığı ana görünüm."""

    def __init__(self, ai_view_model) -> None:
        super().__init__()
        self.vm = ai_view_model
        self._last_parsed: Dict[str, Any] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        header = QLabel("Yapay Zeka Asistanı")
        header.setObjectName("page_title")
        header.setStyleSheet("font-size: 22px; font-weight: bold;")
        root.addWidget(header)

        # Yapay zeka kapalıysa uyarı şeridi
        self.warning_label = QLabel(
            "⚠ Yapay zeka henüz yapılandırılmadı. Ayarlar > Yapay Zeka bölümünden "
            "Ollama (ücretsiz, yerel) veya Google Gemini (ücretsiz katman) seçin."
        )
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet(
            "background-color: #D97706; color: white; padding: 10px; border-radius: 6px;"
        )
        root.addWidget(self.warning_label)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #6B7280;")
        root.addWidget(self.status_label)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, stretch=1)

        self.tabs.addTab(self._build_chat_tab(), "Asistan")
        self.tabs.addTab(self._build_risk_tab(), "Risk & Öneri")
        self.tabs.addTab(self._build_technical_tab(), "Teknik Analiz")
        self.tabs.addTab(self._build_news_tab(), "Haber Analizi")
        self.tabs.addTab(self._build_nl_tab(), "Doğal Dil İşlem")
        self.tabs.addTab(self._build_vision_tab(), "Fotoğraftan Aktar")

        self._connect_signals()
        self.refresh_state()

    # ------------------------------------------------------------------
    # Sekme oluşturucular
    # ------------------------------------------------------------------

    def _build_chat_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        layout.addWidget(self.chat_display, stretch=1)

        input_row = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText(
            "Portföyün hakkında bir soru sor (ör. 'En çok hangi varlığım kazandırdı?')"
        )
        self.chat_input.returnPressed.connect(self._on_send_chat)
        self.btn_send = QPushButton("Gönder")
        self.btn_send.clicked.connect(self._on_send_chat)
        input_row.addWidget(self.chat_input, stretch=1)
        input_row.addWidget(self.btn_send)
        layout.addLayout(input_row)

        actions = QHBoxLayout()
        self.btn_summary = QPushButton("Portföy Özeti Oluştur")
        self.btn_summary.clicked.connect(
            lambda: self._guarded(self.vm.generate_summary)
        )
        self.btn_clear = QPushButton("Sohbeti Temizle")
        self.btn_clear.clicked.connect(self._on_clear_chat)
        actions.addWidget(self.btn_summary)
        actions.addWidget(self.btn_clear)
        actions.addStretch()
        layout.addLayout(actions)
        return widget

    def _build_risk_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.btn_risk = QPushButton("Riskleri Tara")
        self.btn_risk.clicked.connect(lambda: self.vm.analyze_risk())
        layout.addWidget(self.btn_risk)

        self.risk_display = QTextBrowser()
        layout.addWidget(self.risk_display, stretch=1)

        layout.addWidget(QLabel("Hedefin (opsiyonel):"))
        self.goal_input = QLineEdit()
        self.goal_input.setPlaceholderText(
            "Ör. uzun vadeli birikim, düşük risk, temettü odaklı..."
        )
        layout.addWidget(self.goal_input)

        self.btn_advice = QPushButton("Yapay Zekadan Öneri Al")
        self.btn_advice.clicked.connect(
            lambda: self._guarded(
                lambda: self.vm.generate_advice(self.goal_input.text())
            )
        )
        layout.addWidget(self.btn_advice)

        self.advice_display = QTextBrowser()
        layout.addWidget(self.advice_display, stretch=1)
        return widget

    def _build_technical_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        row = QHBoxLayout()
        self.tech_asset_combo = QComboBox()
        self.btn_analyze = QPushButton("Analiz Et")
        self.btn_analyze.clicked.connect(self._on_run_technical)
        row.addWidget(QLabel("Varlık:"))
        row.addWidget(self.tech_asset_combo, stretch=1)
        row.addWidget(self.btn_analyze)
        layout.addLayout(row)

        self.tech_display = QTextBrowser()
        layout.addWidget(self.tech_display, stretch=1)
        return widget

    def _build_news_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        row = QHBoxLayout()
        self.news_asset_combo = QComboBox()
        self.btn_news = QPushButton("Haberleri Analiz Et")
        self.btn_news.clicked.connect(self._on_run_news)
        row.addWidget(QLabel("Varlık:"))
        row.addWidget(self.news_asset_combo, stretch=1)
        row.addWidget(self.btn_news)
        layout.addLayout(row)

        self.news_display = QTextBrowser()
        self.news_display.setOpenExternalLinks(True)
        layout.addWidget(self.news_display, stretch=1)
        return widget

    def _build_nl_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(
            QLabel("İşlemini gündelik dille yaz, yapay zeka forma çevirsin:")
        )
        self.nl_input = QLineEdit()
        self.nl_input.setPlaceholderText("Ör. Dün 100 THYAO aldım 280 liradan")
        self.nl_input.returnPressed.connect(self._on_parse_nl)
        layout.addWidget(self.nl_input)

        self.btn_parse = QPushButton("Çözümle")
        self.btn_parse.clicked.connect(self._on_parse_nl)
        layout.addWidget(self.btn_parse)

        self.nl_display = QTextBrowser()
        layout.addWidget(self.nl_display, stretch=1)
        return widget

    def _build_vision_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel(
            "Portföy ekran görüntünü/fotoğrafını seç; yapay zeka varlıkları "
            "çıkarsın. Çıkan listeyi düzenleyip onaylayabilirsin."
        ))

        row = QHBoxLayout()
        self.btn_pick_image = QPushButton("Fotoğraf Seç...")
        self.btn_pick_image.clicked.connect(self._on_pick_image)
        self.vision_path_label = QLabel("Henüz dosya seçilmedi.")
        self.vision_path_label.setStyleSheet("color: #6B7280;")
        row.addWidget(self.btn_pick_image)
        row.addWidget(self.vision_path_label, stretch=1)
        layout.addLayout(row)

        self.vision_table = QTableWidget(0, 4)
        self.vision_table.setHorizontalHeaderLabels(["Kod", "Tür", "Adet", "Ort. Maliyet"])
        self.vision_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.vision_table.setEditTriggers(QAbstractItemView.AllEditTriggers)
        layout.addWidget(self.vision_table, stretch=1)

        self.btn_import_holdings = QPushButton("Listeyi İçe Aktar")
        self.btn_import_holdings.clicked.connect(self._on_import_holdings)
        self.btn_import_holdings.setEnabled(False)
        layout.addWidget(self.btn_import_holdings)
        return widget

    # ------------------------------------------------------------------
    # Sinyal bağlantıları
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self.vm.chat_response_ready.connect(self._on_chat_response)
        self.vm.summary_ready.connect(self._on_summary)
        self.vm.advice_ready.connect(lambda t: self.advice_display.setMarkdown(t))
        self.vm.risk_ready.connect(self._on_risk_ready)
        self.vm.transaction_parsed.connect(self._on_transaction_parsed)
        self.vm.transaction_saved.connect(self._on_transaction_saved)
        self.vm.sentiment_ready.connect(self._on_sentiment_ready)
        self.vm.analysis_ready.connect(self._on_analysis_ready)
        self.vm.holdings_extracted.connect(self._on_holdings_extracted)
        self.vm.holdings_imported.connect(self._on_holdings_imported)
        self.vm.error_occurred.connect(self._on_error)
        self.vm.busy_changed.connect(self._on_busy_changed)

    # ------------------------------------------------------------------
    # Durum / yenileme
    # ------------------------------------------------------------------

    def refresh_state(self) -> None:
        """Sekme her açıldığında AI durumunu ve varlık listelerini günceller."""
        enabled = self.vm.is_ai_enabled()
        self.warning_label.setVisible(not enabled)
        self._populate_asset_combos()

    def _populate_asset_combos(self) -> None:
        assets = self.vm.get_asset_choices()
        for combo in (self.tech_asset_combo, self.news_asset_combo):
            current = combo.currentData()
            combo.clear()
            for a in assets:
                combo.addItem(f"{a['code']} - {a['name']}", a)
            if current is not None:
                idx = combo.findData(current)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

    # ------------------------------------------------------------------
    # Olay yöneticileri
    # ------------------------------------------------------------------

    def _guarded(self, fn) -> None:
        """AI etkin değilse uyarır, etkinse fonksiyonu çalıştırır."""
        if not self.vm.is_ai_enabled():
            self.status_label.setText(
                "Yapay zeka yapılandırılmadı. Ayarlar bölümünden etkinleştirin."
            )
            return
        fn()

    def _on_send_chat(self) -> None:
        text = self.chat_input.text().strip()
        if not text:
            return
        self._append_chat("Sen", text)
        self.chat_input.clear()
        self._guarded(lambda: self.vm.send_message(text))

    def _on_clear_chat(self) -> None:
        self.vm.clear_chat()
        self.chat_display.clear()

    def _on_chat_response(self, text: str) -> None:
        self._append_chat("Asistan", text)

    def _append_chat(self, sender: str, text: str) -> None:
        color = "#00B5E2" if sender == "Asistan" else "#10B981"
        self.chat_display.append(
            f'<p style="margin:8px 0;"><b style="color:{color};">{sender}:</b> '
            f"{text}</p>"
        )

    def _on_summary(self, text: str) -> None:
        self._append_chat("Asistan", "📊 Portföy Özeti: " + text)

    def _on_risk_ready(self, warnings: List[Dict[str, str]]) -> None:
        if not warnings:
            self.risk_display.setHtml(
                "<p style='color:#10B981;'>✔ Belirgin bir konsantrasyon ya da "
                "çeşitlendirme riski tespit edilmedi.</p>"
            )
            return
        html = ["<h3>Risk Bulguları</h3>"]
        for w in warnings:
            color = _SEVERITY_COLORS.get(w["severity"], "#6B7280")
            html.append(
                f"<p><b style='color:{color};'>● {w['title']}</b><br>{w['message']}</p>"
            )
        self.risk_display.setHtml("".join(html))

    def _on_transaction_parsed(self, data: Dict[str, Any]) -> None:
        self._last_parsed = data
        dialog = TransactionConfirmDialog(data, self)
        if dialog.exec() == QDialog.Accepted:
            result = dialog.get_data()
            self.vm.save_parsed_transaction(result["data"], result["asset_type"])

    def _on_transaction_saved(self, message: str) -> None:
        self.nl_display.append(f"<p style='color:#10B981;'>✔ {message}</p>")
        self.nl_input.clear()

    def _on_sentiment_ready(self, data: Dict[str, Any]) -> None:
        color = {
            "pozitif": "#10B981",
            "negatif": "#B91C1C",
            "nötr": "#6B7280",
        }.get(data.get("sentiment", "nötr"), "#6B7280")
        html = [
            f"<h3>Duygu: <span style='color:{color};'>{data.get('sentiment', '').upper()}</span> "
            f"(skor: {data.get('score', 0):.2f})</h3>",
            f"<p>{data.get('summary', '')}</p>",
        ]
        headlines = data.get("headlines", [])
        if headlines:
            html.append("<h4>Başlıklar</h4><ul>")
            for h in headlines:
                html.append(f"<li>{h}</li>")
            html.append("</ul>")
        self.news_display.setHtml("".join(html))

    def _on_analysis_ready(self, data: Dict[str, Any]) -> None:
        ind = data.get("indicators", {})
        html = [f"<h3>{data.get('code', '')} Teknik Analiz</h3>"]
        if not ind.get("available"):
            html.append(
                f"<p style='color:#D97706;'>{ind.get('reason', 'Yeterli veri yok.')}</p>"
            )
        else:
            trend_color = {
                "Yükseliş": "#10B981",
                "Düşüş": "#B91C1C",
                "Nötr": "#6B7280",
            }.get(ind["trend"], "#6B7280")
            html.append(
                f"<p>Son Fiyat: <b>{format_currency(ind['last_price'])}</b></p>"
            )
            html.append(
                f"<p>Trend Sinyali: <b style='color:{trend_color};'>{ind['trend']}</b></p>"
            )
            html.append("<ul>")
            html.append(
                f"<li>SMA20: {self._fmt(ind.get('sma20'))} | "
                f"SMA50: {self._fmt(ind.get('sma50'))}</li>"
            )
            html.append(f"<li>RSI(14): {self._fmt(ind.get('rsi'), 1)}</li>")
            html.append(
                f"<li>MACD: {self._fmt(ind.get('macd'), 3)} | "
                f"Sinyal: {self._fmt(ind.get('macd_signal'), 3)}</li>"
            )
            html.append("</ul>")
            if ind.get("reasons"):
                html.append("<p><b>Gerekçeler:</b></p><ul>")
                for r in ind["reasons"]:
                    html.append(f"<li>{r}</li>")
                html.append("</ul>")

        anomalies = data.get("anomalies", [])
        html.append("<h4>Olağandışı Hareketler</h4>")
        html.append(
            "<p>"
            + anomaly_mod.describe_anomalies(anomalies).replace("\n", "<br>")
            + "</p>"
        )
        self.tech_display.setHtml("".join(html))

    @staticmethod
    def _fmt(value, digits: int = 2) -> str:
        if value is None:
            return "—"
        return f"{value:.{digits}f}"

    def _on_run_technical(self) -> None:
        asset = self.tech_asset_combo.currentData()
        if not asset:
            self.status_label.setText("Önce bir varlık seçin.")
            return
        self.tech_display.setHtml("<p>Hesaplanıyor...</p>")
        self.vm.run_technical_analysis(asset["code"], asset["type"])

    def _on_run_news(self) -> None:
        asset = self.news_asset_combo.currentData()
        if not asset:
            self.status_label.setText("Önce bir varlık seçin.")
            return
        self.news_display.setHtml("<p>Haberler getiriliyor...</p>")
        self._guarded(lambda: self.vm.analyze_news(asset["code"], asset["name"]))

    def _on_parse_nl(self) -> None:
        text = self.nl_input.text().strip()
        if not text:
            return
        self._guarded(lambda: self.vm.parse_transaction_text(text))

    # --- Görüntüden aktarım ---

    def _on_pick_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Portföy Görüntüsü Seç", "",
            "Görüntü (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"
        )
        if not path:
            return
        self.vision_path_label.setText(path)
        self.vision_table.setRowCount(0)
        self.btn_import_holdings.setEnabled(False)
        self.status_label.setText("Görüntü analiz ediliyor...")
        self._guarded(lambda: self.vm.import_from_image(path))

    def _on_holdings_extracted(self, holdings: List[Dict[str, Any]]) -> None:
        self.vision_table.setRowCount(0)
        for h in holdings:
            r = self.vision_table.rowCount()
            self.vision_table.insertRow(r)
            self.vision_table.setItem(r, 0, QTableWidgetItem(str(h.get("code", ""))))
            self.vision_table.setItem(r, 1, QTableWidgetItem(str(h.get("type", "BIST"))))
            self.vision_table.setItem(r, 2, QTableWidgetItem(str(h.get("quantity", 0))))
            self.vision_table.setItem(r, 3, QTableWidgetItem(str(h.get("avg_cost", 0))))
        has_rows = self.vision_table.rowCount() > 0
        self.btn_import_holdings.setEnabled(has_rows)
        self.status_label.setText(
            f"{self.vision_table.rowCount()} varlık bulundu. Düzenleyip içe aktarabilirsin."
            if has_rows else "Görüntüde varlık bulunamadı."
        )

    def _on_import_holdings(self) -> None:
        holdings = []
        for r in range(self.vision_table.rowCount()):
            def _cell(c):
                item = self.vision_table.item(r, c)
                return item.text().strip() if item else ""

            def _num(c):
                try:
                    return float(_cell(c).replace(",", "."))
                except ValueError:
                    return 0.0

            code = _cell(0).upper()
            if not code:
                continue
            a_type = _cell(1).upper()
            holdings.append({
                "code": code,
                "type": "TEFAS" if a_type == "TEFAS" else "BIST",
                "quantity": _num(2),
                "avg_cost": _num(3),
            })
        if holdings:
            self.vm.save_imported_holdings(holdings)

    def _on_holdings_imported(self, message: str) -> None:
        self.status_label.setText(message)
        self.vision_table.setRowCount(0)
        self.btn_import_holdings.setEnabled(False)
        self._populate_asset_combos()

    def _on_error(self, message: str) -> None:
        self.status_label.setText(f"Hata: {message}")

    def _on_busy_changed(self, busy: bool) -> None:
        self.status_label.setText("Yapay zeka çalışıyor..." if busy else "")
        for btn in (
            self.btn_send,
            self.btn_summary,
            self.btn_advice,
            self.btn_analyze,
            self.btn_news,
            self.btn_parse,
            self.btn_pick_image,
        ):
            btn.setEnabled(not busy)
        # İçe aktar butonu yalnızca tabloda satır varsa ve meşgul değilken aktif
        self.btn_import_holdings.setEnabled(
            not busy and self.vision_table.rowCount() > 0
        )


class TransactionConfirmDialog(QDialog):
    """Ayrıştırılan işlemi kullanıcıya onaylatan/düzenleten diyalog."""

    def __init__(self, data: Dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("İşlemi Onayla")
        self.setMinimumWidth(360)

        form = QFormLayout(self)

        self.code_edit = QLineEdit(data.get("asset_code", ""))
        form.addRow("Kod:", self.code_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["BIST", "TEFAS"])
        self.type_combo.setCurrentText(data.get("asset_type", "BIST"))
        form.addRow("Varlık Türü:", self.type_combo)

        self.tx_combo = QComboBox()
        self.tx_combo.addItem("Alım", "BUY")
        self.tx_combo.addItem("Satım", "SELL")
        ti = self.tx_combo.findData(data.get("tx_type", "BUY"))
        if ti >= 0:
            self.tx_combo.setCurrentIndex(ti)
        form.addRow("İşlem:", self.tx_combo)

        self.date_edit = QLineEdit(data.get("date", ""))
        form.addRow("Tarih (YYYY-AA-GG):", self.date_edit)

        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setMaximum(1_000_000_000)
        self.qty_spin.setDecimals(6)
        self.qty_spin.setValue(float(data.get("quantity", 0)))
        form.addRow("Adet:", self.qty_spin)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setMaximum(1_000_000_000)
        self.price_spin.setDecimals(6)
        self.price_spin.setValue(float(data.get("unit_price", 0)))
        form.addRow("Birim Fiyat:", self.price_spin)

        self.commission_spin = QDoubleSpinBox()
        self.commission_spin.setMaximum(1_000_000)
        self.commission_spin.setDecimals(4)
        self.commission_spin.setValue(float(data.get("commission", 0)))
        form.addRow("Komisyon:", self.commission_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def get_data(self) -> Dict[str, Any]:
        return {
            "asset_type": self.type_combo.currentText(),
            "data": {
                "asset_code": self.code_edit.text().strip().upper(),
                "tx_type": self.tx_combo.currentData(),
                "date": self.date_edit.text().strip(),
                "quantity": self.qty_spin.value(),
                "unit_price": self.price_spin.value(),
                "commission": self.commission_spin.value(),
                "note": "",
            },
        }

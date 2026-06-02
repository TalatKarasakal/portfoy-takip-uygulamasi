from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableView,
                                 QPushButton, QLineEdit, QComboBox, QHeaderView, QLabel,
                                 QMessageBox, QDialog, QFormLayout, QMenu)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor
import qtawesome as qta
from app.utils.formatters import format_currency, format_percent
from app.utils.display import display
from app.views.transactions_view import AddTransactionDialog
from app.views.widgets.table_filter import TableFilterProxyModel
from app.views.widgets.asset_chart_dialog import AssetChartDialog

PROFIT_COLOR = QColor("#10B981")
LOSS_COLOR = QColor("#DC2626")


class PortfolioTableModel(QAbstractTableModel):
    # Sütun indeksleri
    COL_ID, COL_CODE, COL_NAME, COL_TYPE, COL_QTY, COL_AVG, COL_PRICE, \
        COL_TOTCOST, COL_VALUE, COL_DAILY, COL_PNL, COL_PNL_PCT, COL_PORT_PCT = range(13)

    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self._headers = ["ID", "Kod", "Ad", "Tür", "Adet", "Ort. Maliyet",
                         "Güncel Fiyat", "Toplam Maliyet", "Güncel Değer", "Günlük Değ.",
                         "Toplam K/Z", "K/Z %", "Portföy %"]

    def _pnl(self, row):
        return row.get("realized_pnl", 0) + row.get("unrealized_pnl", 0)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._data[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == self.COL_ID: return str(row.get("id", ""))
            elif col == self.COL_CODE: return row.get("code", "")
            elif col == self.COL_NAME: return row.get("name", "")
            elif col == self.COL_TYPE: return row.get("type", "")
            elif col == self.COL_QTY: return f"{row.get('quantity', 0):,.2f}"
            elif col == self.COL_AVG: return display.format(row.get("avg_cost", 0))
            elif col == self.COL_PRICE: return display.format(row.get("current_price", 0))
            elif col == self.COL_TOTCOST: return display.format(row.get("total_cost", 0))
            elif col == self.COL_VALUE: return display.format(row.get("current_value", 0))
            elif col == self.COL_DAILY: return display.format(row.get("daily_change", 0))
            elif col == self.COL_PNL: return display.format(self._pnl(row))
            elif col == self.COL_PNL_PCT:
                cost = row.get("total_cost", 0)
                pct = (self._pnl(row) / cost * 100) if cost > 0 else 0
                return format_percent(pct)
            elif col == self.COL_PORT_PCT: return format_percent(row.get("portfolio_pct", 0))

        elif role == Qt.UserRole:
            # Sıralama için ham karşılaştırılabilir değerler
            if col == self.COL_ID: return row.get("id", 0)
            elif col == self.COL_CODE: return row.get("code", "")
            elif col == self.COL_NAME: return row.get("name", "")
            elif col == self.COL_TYPE: return row.get("type", "")
            elif col == self.COL_QTY: return float(row.get("quantity", 0))
            elif col == self.COL_AVG: return float(row.get("avg_cost", 0))
            elif col == self.COL_PRICE: return float(row.get("current_price", 0))
            elif col == self.COL_TOTCOST: return float(row.get("total_cost", 0))
            elif col == self.COL_VALUE: return float(row.get("current_value", 0))
            elif col == self.COL_DAILY: return float(row.get("daily_change", 0))
            elif col == self.COL_PNL: return float(self._pnl(row))
            elif col == self.COL_PNL_PCT:
                cost = row.get("total_cost", 0)
                return (self._pnl(row) / cost * 100) if cost > 0 else 0
            elif col == self.COL_PORT_PCT: return float(row.get("portfolio_pct", 0))

        elif role == Qt.ForegroundRole:
            if col in (self.COL_DAILY,):
                v = row.get("daily_change", 0)
                if v > 0: return PROFIT_COLOR
                if v < 0: return LOSS_COLOR
            elif col in (self.COL_PNL, self.COL_PNL_PCT):
                v = self._pnl(row)
                if v > 0: return PROFIT_COLOR
                if v < 0: return LOSS_COLOR

        elif role == Qt.TextAlignmentRole:
            if col >= self.COL_QTY:
                return int(Qt.AlignRight | Qt.AlignVCenter)

        return None

    def rowCount(self, index=QModelIndex()):
        return len(self._data)

    def columnCount(self, index=QModelIndex()):
        return len(self._headers)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def row_dict(self, source_row):
        if 0 <= source_row < len(self._data):
            return self._data[source_row]
        return None


class AssetDialog(QDialog):
    """Yeni varlık ekleme / düzenleme diyaloğu."""

    def __init__(self, parent=None, asset=None):
        super().__init__(parent)
        self.setWindowTitle("Varlık Düzenle" if asset else "Yeni Varlık Ekle")
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.input_code = QLineEdit()
        self.input_code.setPlaceholderText("Örn: THYAO veya AFT")
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Varlık Adı")
        self.combo_type = QComboBox()
        self.combo_type.addItems(["BIST", "TEFAS"])

        if asset:
            self.input_code.setText(asset.get("code", ""))
            self.input_code.setEnabled(False)  # kod değiştirilemez
            self.input_name.setText(asset.get("name", ""))
            self.combo_type.setCurrentText(asset.get("type", "BIST"))

        form.addRow("Varlık Kodu:", self.input_code)
        form.addRow("Varlık Adı:", self.input_name)
        form.addRow("Tür:", self.combo_type)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Kaydet")
        self.btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def get_data(self):
        return {
            "code": self.input_code.text().strip(),
            "name": self.input_name.text().strip(),
            "type": self.combo_type.currentText(),
        }


class PortfolioView(QWidget):
    def __init__(self, view_model):
        super().__init__()
        self.view_model = view_model

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # --- Üst Araç Çubuğu ---
        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Varlık Kodu veya Adı Ara...")
        self.search_input.setFixedWidth(250)
        toolbar.addWidget(self.search_input)

        self.type_filter = QComboBox()
        self.type_filter.addItems(["Tümü", "BIST", "TEFAS"])
        toolbar.addWidget(self.type_filter)

        toolbar.addStretch()

        self.refresh_btn = QPushButton(" Fiyatları Yenile")
        self.refresh_btn.setIcon(qta.icon("fa5s.sync"))
        self.refresh_btn.clicked.connect(lambda: self.view_model.load_data(force_refresh=True))
        toolbar.addWidget(self.refresh_btn)

        self.add_btn = QPushButton(" + Varlık Ekle")
        self.add_btn.setObjectName("primary_btn")
        self.add_btn.setStyleSheet(
            "QPushButton { background-color: #E30A17; color: white; border-radius: 4px;"
            " padding: 6px 12px; font-weight: bold; }"
        )
        self.add_btn.clicked.connect(self.on_add_btn_clicked)
        toolbar.addWidget(self.add_btn)

        layout.addLayout(toolbar)

        # --- Portföy Tablosu (proxy ile filtre + sıralama) ---
        self.table_view = QTableView()
        self.table_model = PortfolioTableModel()
        self.proxy = TableFilterProxyModel(
            search_columns=[PortfolioTableModel.COL_CODE, PortfolioTableModel.COL_NAME],
            type_column=PortfolioTableModel.COL_TYPE,
        )
        self.proxy.setSourceModel(self.table_model)
        self.table_view.setModel(self.proxy)

        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setColumnHidden(PortfolioTableModel.COL_ID, True)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)

        layout.addWidget(self.table_view)

        # Bilgi Satırı
        self.footer_label = QLabel("Toplam Kayıt: 0")
        self.footer_label.setProperty("class", "CardTitle")
        layout.addWidget(self.footer_label)

        # Güncellenemeyen / bayat fiyat uyarısı
        self.warning_label = QLabel("")
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet("color: #F59E0B;")
        self.warning_label.setVisible(False)
        layout.addWidget(self.warning_label)

        # Bağlantılar
        self.view_model.data_loaded.connect(self.on_data_loaded)
        self.view_model.kpi_updated.connect(self.on_kpi_updated)
        self.view_model.error_occurred.connect(
            lambda msg: QMessageBox.warning(self, "Hata", msg)
        )
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)
        self.table_view.doubleClicked.connect(self.on_row_double_clicked)
        self.search_input.textChanged.connect(self.proxy.set_search_text)
        self.type_filter.currentTextChanged.connect(self._on_type_filter_changed)

    def _on_type_filter_changed(self, text):
        self.proxy.set_type_value(None if text == "Tümü" else text)

    def on_data_loaded(self, portfolio_items):
        self.table_model.update_data(portfolio_items)
        total_value = sum(i.get("current_value", 0) for i in portfolio_items)
        self.footer_label.setText(
            f"Toplam Kayıt: {len(portfolio_items)}   |   "
            f"Toplam Değer: {display.format(total_value)}"
        )

    def on_kpi_updated(self, kpi_data):
        stale = kpi_data.get("stale_codes", [])
        failed = kpi_data.get("failed_codes", [])
        parts = []
        if stale:
            parts.append(f"⚠ Son bilinen fiyat kullanılıyor: {', '.join(stale)}")
        if failed:
            parts.append(f"⛔ Fiyatı alınamadı: {', '.join(failed)}")
        self.warning_label.setText("   ".join(parts))
        self.warning_label.setVisible(bool(parts))

    def _selected_source_row(self, proxy_index):
        if not proxy_index.isValid():
            return None
        src = self.proxy.mapToSource(proxy_index)
        return self.table_model.row_dict(src.row())

    def on_add_btn_clicked(self):
        dialog = AssetDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if data["code"] and data["name"]:
                self.view_model.add_asset(data["code"], data["name"], data["type"])
            else:
                QMessageBox.warning(self, "Hata", "Lütfen Kod ve Ad alanlarını doldurunuz.")

    def show_context_menu(self, pos):
        index = self.table_view.indexAt(pos)
        if not index.isValid():
            return
        row = self._selected_source_row(index)
        if row is None:
            return

        menu = QMenu(self)
        act_edit = menu.addAction("Düzenle")
        act_tx = menu.addAction("Yeni İşlem Ekle (Al/Sat)")
        act_chart = menu.addAction("Grafiği Aç")
        menu.addSeparator()
        act_delete = menu.addAction("Sil")

        action = menu.exec(self.table_view.viewport().mapToGlobal(pos))
        if action == act_edit:
            self.edit_asset(row)
        elif action == act_tx:
            self.open_transaction_dialog_for_row(row)
        elif action == act_chart:
            self.open_chart(row)
        elif action == act_delete:
            self.delete_asset(row)

    def on_row_double_clicked(self, index):
        row = self._selected_source_row(index)
        if row:
            self.open_transaction_dialog_for_row(row)

    def edit_asset(self, row):
        dialog = AssetDialog(self, asset=row)
        if dialog.exec():
            data = dialog.get_data()
            if data["name"]:
                self.view_model.update_asset(row["id"], data["name"], data["type"])

    def delete_asset(self, row):
        confirm = QMessageBox.question(
            self, "Onay",
            f"'{row['code']}' varlığı ve ona bağlı TÜM işlemler/uyarılar silinecek. "
            "Devam edilsin mi?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.view_model.delete_asset(row["id"])

    def open_chart(self, row):
        dialog = AssetChartDialog(
            row["code"], row["type"],
            self.view_model.bist_service, self.view_model.tefas_service,
            self
        )
        dialog.exec()

    def open_transaction_dialog_for_row(self, row):
        assets = self.view_model.cached_portfolio_data
        dialog = AddTransactionDialog(assets, self)
        idx = dialog.combo_asset.findData(row["id"])
        if idx >= 0:
            dialog.combo_asset.setCurrentIndex(idx)
        if dialog.exec():
            data = dialog.get_data()
            if data["asset_id"] and data["quantity"] > 0 and data["unit_price"] > 0:
                self.view_model.add_transaction(**data)
            else:
                QMessageBox.warning(self, "Hata", "Girdiğiniz veriler hatalı veya eksik.")

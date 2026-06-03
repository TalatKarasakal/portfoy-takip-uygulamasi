from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableView,
                                 QPushButton, QLineEdit, QComboBox, QHeaderView, QLabel,
                                 QMessageBox, QDialog, QFormLayout, QDoubleSpinBox, QDateEdit, QMenu)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QDate
from PySide6.QtGui import QColor
from app.utils.formatters import format_currency
from app.utils.display import display
from app.views.widgets.table_filter import TableFilterProxyModel

BUY_COLOR = QColor("#00B5E2")
SELL_COLOR = QColor("#A855F7")
DIVIDEND_COLOR = QColor("#10B981")
SPLIT_COLOR = QColor("#9CA3AF")

TYPE_LABELS = {"BUY": "Alım", "SELL": "Satım", "DIVIDEND": "Temettü", "SPLIT": "Bölünme"}
TYPE_COLORS = {"BUY": BUY_COLOR, "SELL": SELL_COLOR, "DIVIDEND": DIVIDEND_COLOR, "SPLIT": SPLIT_COLOR}


class TransactionTableModel(QAbstractTableModel):
    COL_DATE, COL_ASSET, COL_TYPE, COL_QTY, COL_PRICE, COL_COMM, COL_TAX, COL_TOTAL, COL_NOTE = range(9)

    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self._headers = ["Tarih", "Varlık", "Tür", "Adet", "Birim Fiyat",
                         "Komisyon", "Vergi", "Toplam", "Not"]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._data[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == self.COL_DATE: return row.get("date", "")
            elif col == self.COL_ASSET: return row.get("asset_code", "")
            elif col == self.COL_TYPE: return TYPE_LABELS.get(row.get("type"), row.get("type", ""))
            elif col == self.COL_QTY: return f"{row.get('quantity', 0):,.2f}"
            elif col == self.COL_PRICE: return display.format(row.get("unit_price", 0))
            elif col == self.COL_COMM: return display.format(row.get("commission", 0))
            elif col == self.COL_TAX: return display.format(row.get("tax", 0))
            elif col == self.COL_TOTAL: return display.format(row.get("total", 0))
            elif col == self.COL_NOTE: return row.get("note", "")

        elif role == Qt.UserRole:
            if col == self.COL_DATE: return row.get("date", "")
            elif col == self.COL_ASSET: return row.get("asset_code", "")
            elif col == self.COL_TYPE: return row.get("type", "")
            elif col == self.COL_QTY: return float(row.get("quantity", 0))
            elif col == self.COL_PRICE: return float(row.get("unit_price", 0))
            elif col == self.COL_COMM: return float(row.get("commission", 0))
            elif col == self.COL_TAX: return float(row.get("tax", 0))
            elif col == self.COL_TOTAL: return float(row.get("total", 0))
            elif col == self.COL_NOTE: return row.get("note", "")

        elif role == Qt.ForegroundRole:
            if col == self.COL_TYPE:
                return TYPE_COLORS.get(row.get("type"), BUY_COLOR)

        elif role == Qt.TextAlignmentRole:
            if col in (self.COL_QTY, self.COL_PRICE, self.COL_COMM, self.COL_TAX, self.COL_TOTAL):
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


class AddTransactionDialog(QDialog):
    def __init__(self, assets, parent=None, tx=None):
        super().__init__(parent)
        self.setWindowTitle("İşlem Düzenle" if tx else "Yeni İşlem Ekle")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.combo_asset = QComboBox()
        for a in assets:
            self.combo_asset.addItem(a["code"], a["id"])

        self.combo_type = QComboBox()
        self.combo_type.addItem("Alım", "BUY")
        self.combo_type.addItem("Satım", "SELL")
        self.combo_type.addItem("Temettü", "DIVIDEND")
        self.combo_type.addItem("Bölünme / Bedelsiz", "SPLIT")

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())

        self.spin_qty = QDoubleSpinBox()
        self.spin_qty.setRange(0.0001, 1_000_000_000)
        self.spin_qty.setDecimals(4)

        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0.0001, 1_000_000_000)
        self.spin_price.setDecimals(4)

        self.spin_commission = QDoubleSpinBox()
        self.spin_commission.setRange(0, 1_000_000_000)
        self.spin_commission.setDecimals(2)

        self.spin_tax = QDoubleSpinBox()
        self.spin_tax.setRange(0, 1_000_000_000)
        self.spin_tax.setDecimals(2)

        self.line_note = QLineEdit()

        self.lbl_qty = QLabel("Adet:")
        self.lbl_price = QLabel("Birim Fiyat:")
        form.addRow("Varlık:", self.combo_asset)
        form.addRow("Tür:", self.combo_type)
        form.addRow("Tarih:", self.date_edit)
        form.addRow(self.lbl_qty, self.spin_qty)
        form.addRow(self.lbl_price, self.spin_price)
        form.addRow("Komisyon:", self.spin_commission)
        form.addRow("Vergi/Stopaj:", self.spin_tax)
        form.addRow("Not:", self.line_note)
        layout.addLayout(form)

        self.hint = QLabel("")
        self.hint.setWordWrap(True)
        self.hint.setProperty("class", "CardTitle")
        layout.addWidget(self.hint)
        self.combo_type.currentIndexChanged.connect(self._update_hint)
        self._update_hint()

        if tx:
            ai = self.combo_asset.findData(tx.get("asset_id"))
            if ai >= 0:
                self.combo_asset.setCurrentIndex(ai)
            ti = self.combo_type.findData(tx.get("type"))
            if ti >= 0:
                self.combo_type.setCurrentIndex(ti)
            d = tx.get("date_obj")
            if d is not None:
                self.date_edit.setDate(QDate(d.year, d.month, d.day))
            self.spin_qty.setValue(tx.get("quantity", 0))
            self.spin_price.setValue(tx.get("unit_price", 0))
            self.spin_commission.setValue(tx.get("commission", 0))
            self.spin_tax.setValue(tx.get("tax", 0))
            self.line_note.setText(tx.get("note", ""))

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Kaydet")
        self.btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def _update_hint(self):
        t = self.combo_type.currentData()
        hints = {
            "BUY": "Alım: Adet ve birim fiyat girin. Komisyon toplam maliyeti artırır.",
            "SELL": "Satım: Adet ve birim fiyat. Komisyon + vergi net geliri düşürür.",
            "DIVIDEND": "Temettü: 'Adet' = hisse sayısı, 'Birim Fiyat' = hisse başı temettü "
                        "(toplam = adet × fiyat). Stopajı Vergi/Stopaj alanına yazın.",
            "SPLIT": "Bölünme/Bedelsiz: 'Katsayı' = adetin çarpanı (örn. 2.0 ⇒ adet iki "
                     "katına, maliyet yarıya iner). Adet alanı kullanılmaz.",
        }
        self.hint.setText(hints.get(t, ""))
        if t == "SPLIT":
            self.lbl_qty.setText("Adet (kullanılmaz):")
            self.lbl_price.setText("Katsayı:")
        elif t == "DIVIDEND":
            self.lbl_qty.setText("Adet (hisse):")
            self.lbl_price.setText("Hisse Başı Temettü:")
        else:
            self.lbl_qty.setText("Adet:")
            self.lbl_price.setText("Birim Fiyat:")

    def get_data(self):
        return {
            "asset_id": self.combo_asset.currentData(),
            "tx_type": self.combo_type.currentData(),
            "date": self.date_edit.date().toPython(),
            "quantity": self.spin_qty.value(),
            "unit_price": self.spin_price.value(),
            "commission": self.spin_commission.value(),
            "tax": self.spin_tax.value(),
            "note": self.line_note.text(),
        }


class TransactionsView(QWidget):
    def __init__(self, view_model):
        super().__init__()
        self.view_model = view_model

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # --- Üst Araç Çubuğu ---
        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Varlık Kodu ile Ara...")
        self.search_input.setFixedWidth(200)
        toolbar.addWidget(self.search_input)

        self.type_filter = QComboBox()
        self.type_filter.addItems(["Tümü", "Alım", "Satım"])
        toolbar.addWidget(self.type_filter)

        toolbar.addStretch()

        self.add_btn = QPushButton(" + Yeni İşlem")
        self.add_btn.setStyleSheet(
            "QPushButton { background-color: #E30A17; color: white; border-radius: 4px;"
            " padding: 6px 12px; font-weight: bold; }"
        )
        self.add_btn.clicked.connect(self.on_add_btn_clicked)
        toolbar.addWidget(self.add_btn)

        layout.addLayout(toolbar)

        # --- Tablo (proxy ile filtre + sıralama) ---
        self.table_view = QTableView()
        self.table_model = TransactionTableModel()
        self.proxy = TableFilterProxyModel(
            search_columns=[TransactionTableModel.COL_ASSET],
            type_column=TransactionTableModel.COL_TYPE,
        )
        self.proxy.setSourceModel(self.table_model)
        self.table_view.setModel(self.proxy)

        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        layout.addWidget(self.table_view)

        self.footer_label = QLabel("Toplam İşlem: 0")
        self.footer_label.setProperty("class", "CardTitle")
        layout.addWidget(self.footer_label)

        # Bağlantılar
        self.view_model.transactions_loaded.connect(self.on_data_loaded)
        self.view_model.action_failed.connect(
            lambda msg: QMessageBox.warning(self, "Hata", msg)
        )
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)
        self.table_view.doubleClicked.connect(self.on_row_double_clicked)
        self.search_input.textChanged.connect(self.proxy.set_search_text)
        self.type_filter.currentTextChanged.connect(
            lambda t: self.proxy.set_type_value(None if t == "Tümü" else t)
        )

        # İlk yükleme
        self.view_model.load_transactions()

    def on_data_loaded(self, tx_items):
        self.table_model.update_data(tx_items)
        self.footer_label.setText(f"Toplam İşlem: {len(tx_items)}")

    def _selected_source_row(self, proxy_index):
        if not proxy_index.isValid():
            return None
        src = self.proxy.mapToSource(proxy_index)
        return self.table_model.row_dict(src.row())

    def on_add_btn_clicked(self):
        assets = self.view_model.get_available_assets()
        if not assets:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce 'Portföy' sekmesinden bir varlık ekleyin.")
            return
        dialog = AddTransactionDialog(assets, self)
        if dialog.exec():
            data = dialog.get_data()
            if data["asset_id"] and data["quantity"] > 0 and data["unit_price"] > 0:
                self.view_model.add_transaction(
                    asset_id=data["asset_id"], tx_type=data["tx_type"], date=data["date"],
                    quantity=data["quantity"], unit_price=data["unit_price"],
                    commission=data["commission"], tax=data["tax"], note=data["note"],
                )
            else:
                QMessageBox.warning(self, "Hata", "Girdiğiniz veriler hatalı veya eksik.")

    def show_context_menu(self, pos):
        index = self.table_view.indexAt(pos)
        row = self._selected_source_row(index)
        if row is None:
            return
        menu = QMenu(self)
        act_edit = menu.addAction("Düzenle")
        menu.addSeparator()
        act_delete = menu.addAction("Sil")
        action = menu.exec(self.table_view.viewport().mapToGlobal(pos))
        if action == act_edit:
            self.edit_transaction(row)
        elif action == act_delete:
            self.delete_transaction(row)

    def on_row_double_clicked(self, index):
        row = self._selected_source_row(index)
        if row:
            self.edit_transaction(row)

    def edit_transaction(self, row):
        assets = self.view_model.get_available_assets()
        dialog = AddTransactionDialog(assets, self, tx=row)
        if dialog.exec():
            data = dialog.get_data()
            if data["asset_id"] and data["quantity"] > 0 and data["unit_price"] > 0:
                self.view_model.update_transaction(
                    tx_id=row["id"], asset_id=data["asset_id"], tx_type=data["tx_type"],
                    date=data["date"], quantity=data["quantity"], unit_price=data["unit_price"],
                    commission=data["commission"], tax=data["tax"], note=data["note"],
                )
            else:
                QMessageBox.warning(self, "Hata", "Girdiğiniz veriler hatalı veya eksik.")

    def delete_transaction(self, row):
        confirm = QMessageBox.question(
            self, "Onay",
            f"{row['date']} tarihli {row['asset_code']} işlemi silinsin mi?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.view_model.delete_transaction(row["id"])

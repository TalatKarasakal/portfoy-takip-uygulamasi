from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableView, 
                                 QPushButton, QLineEdit, QComboBox, QHeaderView, QLabel, QMessageBox, QDialog, QFormLayout, QDoubleSpinBox, QDateEdit)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QDate
import qtawesome as qta
from app.utils.formatters import format_currency

class TransactionTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self._headers = ["Tarih", "Varlık", "Tür", "Adet", "Birim Fiyat", 
                         "Komisyon", "Vergi", "Toplam", "Not"]

    def data(self, index, role):
        if role == Qt.DisplayRole:
            row = self._data[index.row()]
            col = index.column()
            
            if col == 0: return row.get("date", "")
            elif col == 1: return row.get("asset_code", "")
            elif col == 2: return "Alım" if row.get("type") == "BUY" else "Satım"
            elif col == 3: return f"{row.get('quantity', 0):.2f}"
            elif col == 4: return format_currency(row.get("unit_price", 0))
            elif col == 5: return format_currency(row.get("commission", 0))
            elif col == 6: return format_currency(row.get("tax", 0))
            elif col == 7: return format_currency(row.get("total", 0))
            elif col == 8: return row.get("note", "")
            
        elif role == Qt.ForegroundRole:
            col = index.column()
            if col == 2:
                ttype = self._data[index.row()].get("type", "")
                if ttype == "BUY": return Qt.cyan
                elif ttype == "SELL": return Qt.magenta
        return None

    def rowCount(self, index=QModelIndex()):
        return len(self._data)

    def columnCount(self, index=QModelIndex()):
        return len(self._headers)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

class AddTransactionDialog(QDialog):
    def __init__(self, assets, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni İşlem Ekle")
        self.setFixedSize(400, 350)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.combo_asset = QComboBox()
        for idx, a in enumerate(assets):
            self.combo_asset.addItem(a["code"], a["id"]) # userData is the ID
            
        self.combo_type = QComboBox()
        self.combo_type.addItems(["BUY", "SELL"])
        
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        
        self.spin_qty = QDoubleSpinBox()
        self.spin_qty.setRange(0.0001, 1000000000)
        self.spin_qty.setDecimals(4)
        
        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0.0001, 1000000000)
        self.spin_price.setDecimals(4)
        
        self.spin_commission = QDoubleSpinBox()
        self.spin_commission.setRange(0, 1000000000)
        
        self.spin_tax = QDoubleSpinBox()
        self.spin_tax.setRange(0, 1000000000)
        
        self.line_note = QLineEdit()
        
        form.addRow("Varlık:", self.combo_asset)
        form.addRow("Tür (BUY/SELL):", self.combo_type)
        form.addRow("Tarih:", self.date_edit)
        form.addRow("Adet:", self.spin_qty)
        form.addRow("Birim Fiyat:", self.spin_price)
        form.addRow("Komisyon:", self.spin_commission)
        form.addRow("Vergi:", self.spin_tax)
        form.addRow("Not:", self.line_note)
        
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Kaydet")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        
        layout.addLayout(btn_layout)
        
    def get_data(self):
        return {
            "asset_id": self.combo_asset.currentData(),
            "tx_type": self.combo_type.currentText(),
            "date": self.date_edit.date().toPython(),
            "quantity": self.spin_qty.value(),
            "unit_price": self.spin_price.value(),
            "commission": self.spin_commission.value(),
            "tax": self.spin_tax.value(),
            "note": self.line_note.text()
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
        self.type_filter.addItems(["Tümü", "Alım (BUY)", "Satım (SELL)"])
        toolbar.addWidget(self.type_filter)
        
        toolbar.addStretch()
        
        self.add_btn = QPushButton(" + Yeni İşlem")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #E30A17; 
                color: white; 
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
        """)
        self.add_btn.clicked.connect(self.on_add_btn_clicked)
        toolbar.addWidget(self.add_btn)
        
        layout.addLayout(toolbar)
        
        # --- Tablo ---
        self.table_view = QTableView()
        self.table_model = TransactionTableModel()
        self.table_view.setModel(self.table_model)
        
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setAlternatingRowColors(True)
        
        layout.addWidget(self.table_view)
        
        self.view_model.transactions_loaded.connect(self.on_data_loaded)
        
        # İlk yükleme
        self.view_model.load_transactions()
        
    def on_data_loaded(self, tx_items):
        self.table_model.update_data(tx_items)

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
                    asset_id=data["asset_id"],
                    tx_type=data["tx_type"],
                    date=data["date"],
                    quantity=data["quantity"],
                    unit_price=data["unit_price"],
                    commission=data["commission"],
                    tax=data["tax"],
                    note=data["note"]
                )
            else:
                QMessageBox.warning(self, "Hata", "Girdiğiniz veriler hatalı veya eksik.")

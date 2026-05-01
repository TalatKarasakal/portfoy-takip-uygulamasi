from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableView, 
                                 QPushButton, QLineEdit, QComboBox, QHeaderView, QLabel, QMessageBox, QDialog, QFormLayout, QMenu)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
import qtawesome as qta
from app.utils.formatters import format_currency, format_percent
from app.views.transactions_view import AddTransactionDialog

class PortfolioTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self._headers = ["ID", "Kod", "Ad", "Tür", "Adet", "Ort. Maliyet", 
                         "Güncel Fiyat", "Toplam Maliyet", "Güncel Değer", 
                         "Toplam K/Z", "K/Z %", "Portföy %"]

    def data(self, index, role):
        if role == Qt.DisplayRole:
            row = self._data[index.row()]
            col = index.column()
            
            # Formatting logic
            if col == 0: return str(row.get("id", ""))
            elif col == 1: return row.get("code", "")
            elif col == 2: return row.get("name", "")
            elif col == 3: return row.get("type", "")
            elif col == 4: return f"{row.get('quantity', 0):.2f}"
            elif col == 5: return format_currency(row.get("avg_cost", 0))
            elif col == 6: return format_currency(row.get("current_price", 0))
            elif col == 7: return format_currency(row.get("total_cost", 0))
            elif col == 8: return format_currency(row.get("current_value", 0))
            elif col == 9: 
                # Realized + Unrealized
                return format_currency(row.get("realized_pnl", 0) + row.get("unrealized_pnl", 0))
            elif col == 10:
                pnl = row.get("realized_pnl", 0) + row.get("unrealized_pnl", 0)
                cost = row.get("total_cost", 0)
                pct = (pnl / cost * 100) if cost > 0 else 0
                return format_percent(pct)
            elif col == 11: return format_percent(row.get("portfolio_pct", 0))
            
        elif role == Qt.ForegroundRole:
            col = index.column()
            if col in [9, 10]:
                pnl = self._data[index.row()].get("realized_pnl", 0) + self._data[index.row()].get("unrealized_pnl", 0)
                if pnl > 0: return Qt.green
                elif pnl < 0: return Qt.red
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

class AddAssetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Varlık Ekle")
        self.setFixedSize(350, 200)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.input_code = QLineEdit()
        self.input_code.setPlaceholderText("Örn: THYAO veya AFT")
        
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Varlık Adı")
        
        self.combo_type = QComboBox()
        self.combo_type.addItems(["BIST", "TEFAS"])
        
        form.addRow("Varlık Kodu:", self.input_code)
        form.addRow("Varlık Adı:", self.input_name)
        form.addRow("Tür:", self.combo_type)
        
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
            "code": self.input_code.text().strip(),
            "name": self.input_name.text().strip(),
            "type": self.combo_type.currentText()
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
        
        # --- Portföy Tablosu ---
        self.table_view = QTableView()
        self.table_model = PortfolioTableModel()
        self.table_view.setModel(self.table_model)
        
        # Tablo Stilleri
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        
        layout.addWidget(self.table_view)
        
        # Bilgi Satırı
        self.footer_label = QLabel("Toplam Kayıt: 0")
        self.footer_label.setProperty("class", "CardTitle")
        layout.addWidget(self.footer_label)
        
        # Bağlantılar
        self.view_model.data_loaded.connect(self.on_data_loaded)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)
        self.table_view.doubleClicked.connect(self.on_row_double_clicked)
        
    def on_data_loaded(self, portfolio_items):
        self.table_model.update_data(portfolio_items)
        self.footer_label.setText(f"Toplam Kayıt: {len(portfolio_items)}")

    def on_add_btn_clicked(self):
        dialog = AddAssetDialog(self)
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
            
        menu = QMenu(self)
        add_tx_action = menu.addAction("Yeni İşlem Ekle (Al/Sat)")
        
        action = menu.exec(self.table_view.viewport().mapToGlobal(pos))
        if action == add_tx_action:
            self.open_transaction_dialog_for_index(index)

    def on_row_double_clicked(self, index):
        self.open_transaction_dialog_for_index(index)

    def open_transaction_dialog_for_index(self, index):
        asset_id_str = self.table_model.data(self.table_model.index(index.row(), 0), Qt.DisplayRole)
        try:
            asset_id = int(asset_id_str)
        except (ValueError, TypeError):
            return
            
        assets = self.view_model.cached_portfolio_data
        dialog = AddTransactionDialog(assets, self)
        
        # Seçili varlığı varsayılan yap
        idx = dialog.combo_asset.findData(asset_id)
        if idx >= 0:
            dialog.combo_asset.setCurrentIndex(idx)
            
        if dialog.exec():
            data = dialog.get_data()
            if data["asset_id"] and data["quantity"] > 0 and data["unit_price"] > 0:
                self.view_model.add_transaction(**data)
            else:
                QMessageBox.warning(self, "Hata", "Girdiğiniz veriler hatalı veya eksik.")

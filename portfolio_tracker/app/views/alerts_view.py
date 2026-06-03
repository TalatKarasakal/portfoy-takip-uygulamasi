from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                                 QTableWidgetItem, QPushButton, QLabel, QDialog,
                                 QFormLayout, QComboBox, QDoubleSpinBox, QMessageBox,
                                 QHeaderView, QAbstractItemView)
from PySide6.QtCore import Qt

from app.viewmodels.alerts_viewmodel import ALERT_TYPE_LABELS
from app.models.alert import AlertType


class AddAlertDialog(QDialog):
    def __init__(self, assets, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Uyarı")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.combo_asset = QComboBox()
        for a in assets:
            self.combo_asset.addItem(a["code"], a["id"])

        self.combo_type = QComboBox()
        for atype, label in ALERT_TYPE_LABELS.items():
            self.combo_type.addItem(label, atype.name)

        self.spin_threshold = QDoubleSpinBox()
        self.spin_threshold.setRange(-1_000_000, 1_000_000_000)
        self.spin_threshold.setDecimals(2)

        form.addRow("Varlık:", self.combo_asset)
        form.addRow("Koşul:", self.combo_type)
        form.addRow("Eşik Değeri:", self.spin_threshold)
        layout.addLayout(form)

        hint = QLabel("Fiyat koşulları için TL fiyat, yüzde koşulları için günlük % girin.")
        hint.setWordWrap(True)
        hint.setProperty("class", "CardTitle")
        layout.addWidget(hint)

        btns = QHBoxLayout()
        btns.addStretch()
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Kaydet")
        self.btn_save.clicked.connect(self.accept)
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_save)
        layout.addLayout(btns)

    def get_data(self):
        return {
            "asset_id": self.combo_asset.currentData(),
            "alert_type": self.combo_type.currentData(),
            "threshold": self.spin_threshold.value(),
        }


class AlertsView(QWidget):
    def __init__(self, alerts_vm, portfolio_vm):
        super().__init__()
        self.alerts_vm = alerts_vm
        self.portfolio_vm = portfolio_vm

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Araç çubuğu
        toolbar = QHBoxLayout()
        title = QLabel("Fiyat ve Değişim Uyarıları")
        title.setProperty("class", "CardValue")
        toolbar.addWidget(title)
        toolbar.addStretch()

        self.btn_add = QPushButton(" + Yeni Uyarı")
        self.btn_add.setStyleSheet(
            "QPushButton { background-color: #E30A17; color: white; border-radius: 4px;"
            " padding: 6px 12px; font-weight: bold; }"
        )
        self.btn_add.clicked.connect(self.on_add)
        toolbar.addWidget(self.btn_add)
        layout.addLayout(toolbar)

        # Tablo
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Varlık", "Koşul", "Eşik", "Durum", "Tetiklenme", ""]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        self.empty_label = QLabel("Henüz uyarı tanımlanmadı. '+ Yeni Uyarı' ile başlayın.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setProperty("class", "CardTitle")
        layout.addWidget(self.empty_label)

        # Sinyaller
        self.alerts_vm.alerts_loaded.connect(self.on_alerts_loaded)
        self.alerts_vm.error_occurred.connect(
            lambda msg: QMessageBox.warning(self, "Hata", msg)
        )

        self.refresh()

    def refresh(self):
        self.alerts_vm.load_alerts()

    def on_alerts_loaded(self, alerts):
        self.empty_label.setVisible(len(alerts) == 0)
        self.table.setRowCount(0)
        for row in alerts:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(row["asset_code"]))
            self.table.setItem(r, 1, QTableWidgetItem(row["type_label"]))
            self.table.setItem(r, 2, QTableWidgetItem(f"{row['threshold']:.2f}"))

            status = "Aktif" if row["is_active"] else "Pasif"
            if row["triggered_at"]:
                status = "Tetiklendi"
            self.table.setItem(r, 3, QTableWidgetItem(status))
            self.table.setItem(r, 4, QTableWidgetItem(row["triggered_at"] or "—"))

            del_btn = QPushButton("Sil")
            del_btn.clicked.connect(lambda _, aid=row["id"]: self.on_delete(aid))
            self.table.setCellWidget(r, 5, del_btn)

    def on_add(self):
        assets = self.alerts_vm.get_available_assets()
        if not assets:
            QMessageBox.information(
                self, "Bilgi", "Önce Portföy sekmesinden bir varlık ekleyin."
            )
            return
        dialog = AddAlertDialog(assets, self)
        if dialog.exec():
            data = dialog.get_data()
            if data["asset_id"] is not None:
                self.alerts_vm.add_alert(data["asset_id"], data["alert_type"], data["threshold"])

    def on_delete(self, alert_id):
        confirm = QMessageBox.question(
            self, "Onay", "Bu uyarı silinsin mi?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.alerts_vm.delete_alert(alert_id)

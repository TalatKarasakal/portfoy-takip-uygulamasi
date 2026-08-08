"""Kontrollere ortak erişilebilir ad, açıklama ve tab sırası uygular."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QLineEdit,
    QTableView,
    QWidget,
)


def apply_accessibility(root: QWidget) -> None:
    focusable = []
    for widget in root.findChildren(QWidget):
        name = widget.accessibleName().strip()
        if not name:
            if isinstance(widget, QAbstractButton):
                name = widget.text().replace("&", "").strip()
            elif isinstance(widget, QLineEdit):
                name = widget.placeholderText().strip()
            elif isinstance(widget, QComboBox):
                name = widget.toolTip().strip() or "Seçim alanı"
            elif isinstance(widget, QTableView):
                name = widget.toolTip().strip() or "Veri tablosu"
            if name:
                widget.setAccessibleName(name)
        if not widget.accessibleDescription() and widget.toolTip():
            widget.setAccessibleDescription(widget.toolTip())
        if widget.focusPolicy() != Qt.NoFocus and widget.isEnabled():
            focusable.append(widget)
    for previous, current in zip(focusable[:-1], focusable[1:]):
        QWidget.setTabOrder(previous, current)

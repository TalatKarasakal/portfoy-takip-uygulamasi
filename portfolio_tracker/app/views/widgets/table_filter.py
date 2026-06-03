from PySide6.QtCore import QSortFilterProxyModel, Qt


class TableFilterProxyModel(QSortFilterProxyModel):
    """Metin araması + opsiyonel sütun-eşitlik filtresi yapan, sayısal sıralamayı
    Qt.UserRole üzerinden doğru uygulayan genel bir proxy model.

    Kaynak modeller sayısal sütunlar için Qt.UserRole'da ham (karşılaştırılabilir)
    değer döndürmelidir; aksi halde sıralama biçimlendirilmiş metne göre yanlış olur.
    """

    def __init__(self, search_columns, type_column=None, parent=None):
        super().__init__(parent)
        self._search_text = ""
        self._type_value = None  # None => tümü kabul
        self._search_columns = search_columns
        self._type_column = type_column
        self.setSortRole(Qt.UserRole)
        self.setDynamicSortFilter(True)

    def set_search_text(self, text: str):
        self._search_text = (text or "").strip().lower()
        self.invalidateFilter()

    def set_type_value(self, value):
        self._type_value = value or None
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        if model is None:
            return True

        if self._search_text:
            matched = False
            for col in self._search_columns:
                idx = model.index(source_row, col, source_parent)
                val = str(model.data(idx, Qt.DisplayRole) or "").lower()
                if self._search_text in val:
                    matched = True
                    break
            if not matched:
                return False

        if self._type_value is not None and self._type_column is not None:
            idx = model.index(source_row, self._type_column, source_parent)
            val = str(model.data(idx, Qt.DisplayRole) or "")
            if val != self._type_value:
                return False

        return True

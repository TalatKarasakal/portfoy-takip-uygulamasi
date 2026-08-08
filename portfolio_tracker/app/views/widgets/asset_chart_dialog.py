import time

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

from app.config import COLORS
from app.views.widgets.chart_interaction import install_crosshair


class AssetChartDialog(QDialog):
    """Bir varlığın son 1 yıllık fiyat grafiğini gösterir (veri arka planda çekilir)."""

    def __init__(self, code, asset_type, portfolio_vm, parent=None):
        super().__init__(parent)
        self._code = code
        self._portfolio_vm = portfolio_vm
        self.setWindowTitle(f"{code} — Fiyat Grafiği")
        self.resize(720, 460)

        # Aktif temayı ana pencereden bul (aksi halde grafik her zaman koyu
        # olup aydınlık modda kötü görünüyordu).
        self._theme = "dark"
        w = parent
        while w is not None and not hasattr(w, "current_theme"):
            w = w.parent()
        if w is not None:
            self._theme = getattr(w, "current_theme", "dark")
        self._palette = COLORS.get(self._theme, COLORS["dark"])

        layout = QVBoxLayout(self)
        self.status = QLabel("Veri çekiliyor, lütfen bekleyin...")
        self.status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status)

        self.plot = pg.PlotWidget(axisItems={"bottom": pg.DateAxisItem(orientation="bottom")})
        self.plot.setBackground(self._palette["background"])
        for ax_name in ("left", "bottom"):
            ax = self.plot.getAxis(ax_name)
            ax.setPen(pg.mkPen(color=self._palette["text_secondary"]))
            ax.setTextPen(pg.mkPen(color=self._palette["text_secondary"]))
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        install_crosshair(self.plot)
        self.plot.setVisible(False)
        layout.addWidget(self.plot)

        self._portfolio_vm.asset_history_loaded.connect(self._on_loaded)
        self._portfolio_vm.asset_history_failed.connect(self._on_failed)
        self._portfolio_vm.load_asset_history(code, asset_type)

    def _on_loaded(self, code, records):
        if code != self._code:
            return
        if not records:
            self.status.setText("Bu varlık için geçmiş fiyat verisi bulunamadı.")
            return
        self.status.setVisible(False)
        self.plot.setVisible(True)
        xs = [time.mktime(r["date"].timetuple()) for r in records]
        ys = [r["price"] for r in records]
        self.plot.plot(xs, ys, pen=pg.mkPen(color=self._palette["secondary"], width=2))

    def _on_failed(self, code, msg):
        if code != self._code:
            return
        self.status.setText(f"Grafik yüklenemedi: {msg}")

    def closeEvent(self, event):
        self._portfolio_vm.asset_history_loaded.disconnect(self._on_loaded)
        self._portfolio_vm.asset_history_failed.disconnect(self._on_failed)
        super().closeEvent(event)

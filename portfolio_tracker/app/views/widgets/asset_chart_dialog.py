import datetime
import time

import pyqtgraph as pg
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

from app.config import COLORS


class _HistoryLoader(QThread):
    loaded = Signal(list)  # [{"date": date, "price": float}, ...]
    failed = Signal(str)

    def __init__(self, code, asset_type, bist_service, tefas_service):
        super().__init__()
        self.code = code
        self.asset_type = asset_type
        self.bist_service = bist_service
        self.tefas_service = tefas_service

    def run(self):
        try:
            records = []
            if self.asset_type == "BIST":
                raw = self.bist_service.fetch_historical_prices(self.code, period="1y")
                records = [{"date": r["date"], "price": r["close_price"]} for r in raw]
            else:
                end = datetime.datetime.now()
                start = end - datetime.timedelta(days=365)
                raw = self.tefas_service.fetch_historical_prices(self.code, start, end)
                for r in raw:
                    d = r.get("date")
                    p = r.get("price")
                    if d is not None and p is not None:
                        records.append({"date": d, "price": float(p)})
            records.sort(key=lambda x: x["date"])
            self.loaded.emit(records)
        except Exception as e:
            self.failed.emit(str(e))


class AssetChartDialog(QDialog):
    """Bir varlığın son 1 yıllık fiyat grafiğini gösterir (veri arka planda çekilir)."""

    def __init__(self, code, asset_type, bist_service, tefas_service, parent=None):
        super().__init__(parent)
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
        self.plot.setVisible(False)
        layout.addWidget(self.plot)

        self._loader = _HistoryLoader(code, asset_type, bist_service, tefas_service)
        self._loader.loaded.connect(self._on_loaded)
        self._loader.failed.connect(self._on_failed)
        self._loader.start()

    def _on_loaded(self, records):
        if not records:
            self.status.setText("Bu varlık için geçmiş fiyat verisi bulunamadı.")
            return
        self.status.setVisible(False)
        self.plot.setVisible(True)
        xs = [time.mktime(r["date"].timetuple()) for r in records]
        ys = [r["price"] for r in records]
        self.plot.plot(xs, ys, pen=pg.mkPen(color=self._palette["secondary"], width=2))

    def _on_failed(self, msg):
        self.status.setText(f"Grafik yüklenemedi: {msg}")

    def closeEvent(self, event):
        if self._loader.isRunning():
            self._loader.wait(2000)
        super().closeEvent(event)

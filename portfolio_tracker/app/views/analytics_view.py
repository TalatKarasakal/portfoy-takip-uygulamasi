import datetime
import time

import pyqtgraph as pg
from PySide6.QtCharts import QChart, QChartView, QPieSeries
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import COLORS

PIE_PALETTE = ["#00B5E2", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#6B7280",
               "#EF4444", "#14B8A6", "#A855F7", "#F97316"]

# Karşılaştırma serisi renkleri
SERIES_COLORS = {
    "Portföy": "#00B5E2",
    "BIST 100": "#E30A17",
    "USD/TRY": "#10B981",
    "Gram Altın": "#F59E0B",
}

RANGE_DAYS = {"1H": 7, "1A": 30, "3A": 90, "6A": 180, "1Y": 365}


class AnalyticsView(QWidget):
    def __init__(self, analytics_vm, portfolio_vm):
        super().__init__()
        self.analytics_vm = analytics_vm
        self.portfolio_vm = portfolio_vm
        self._theme = "dark"
        self._range = "Tümü"
        self._history = []
        self._monthly_returns = {}
        self._benchmark = {}
        self._benchmark_error = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_performance_tab(), "Performans")
        self.tabs.addTab(self._create_allocation_tab(), "Dağılım")
        self.tabs.addTab(self._create_benchmark_tab(), "Karşılaştırma")
        self.tabs.addTab(self._create_calendar_tab(), "Takvim")
        layout.addWidget(self.tabs)

        self.analytics_vm.analytics_loaded.connect(self.on_analytics_loaded)
        self.analytics_vm.benchmark_loaded.connect(self._on_benchmark_loaded)
        self.apply_chart_theme(self._theme)

    # ---------- Tab kurulumları ----------
    def _create_performance_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        metrics_layout = QHBoxLayout()
        self.xirr_label = QLabel("XIRR: —")
        self.sharpe_label = QLabel("Sharpe: —")
        self.drawdown_label = QLabel("Max Düşüş: —")
        self.volatility_label = QLabel("Volatilite: —")
        for lbl in (self.xirr_label, self.sharpe_label, self.drawdown_label, self.volatility_label):
            lbl.setProperty("class", "CardWidget")
            metrics_layout.addWidget(lbl)
        layout.addLayout(metrics_layout)

        filter_layout = QHBoxLayout()
        self.range_group = QButtonGroup(self)
        self.range_group.setExclusive(True)
        for r in ["1H", "1A", "3A", "6A", "YBB", "1Y", "Tümü"]:
            btn = QPushButton(r)
            btn.setCheckable(True)
            if r == "Tümü":
                btn.setChecked(True)
            btn.clicked.connect(lambda _checked, rng=r: self._on_range_changed(rng))
            self.range_group.addButton(btn)
            filter_layout.addWidget(btn)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self.plot_widget = pg.PlotWidget(
            axisItems={"bottom": pg.DateAxisItem(orientation="bottom")}
        )
        self.plot_widget.setBackground("transparent")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend()
        self.empty_perf_label = QLabel(
            "Bu aralıkta yeterli geçmiş veri yok. Uygulamayı kullandıkça portföy "
            "değer geçmişi otomatik birikecek."
        )
        self.empty_perf_label.setAlignment(Qt.AlignCenter)
        self.empty_perf_label.setWordWrap(True)
        layout.addWidget(self.empty_perf_label)
        layout.addWidget(self.plot_widget)
        return widget

    def _create_allocation_tab(self):
        widget = QWidget()
        outer = QVBoxLayout(widget)
        donut_row = QWidget()
        layout = QHBoxLayout(donut_row)

        self.type_donut_series = QPieSeries()
        self.type_donut_series.setHoleSize(0.4)
        self.type_chart = QChart()
        self.type_chart.addSeries(self.type_donut_series)
        self.type_chart.setBackgroundBrush(Qt.transparent)
        self.type_chart.setTitle("BIST / TEFAS Dağılımı")
        self.type_donut_view = QChartView(self.type_chart)
        self.type_donut_view.setRenderHint(QPainter.Antialiasing)
        self.type_donut_view.setProperty("class", "CardWidget")
        self.type_donut_view.setStyleSheet("background: transparent; border: none;")

        self.asset_donut_series = QPieSeries()
        self.asset_donut_series.setHoleSize(0.4)
        self.asset_chart = QChart()
        self.asset_chart.addSeries(self.asset_donut_series)
        self.asset_chart.setBackgroundBrush(Qt.transparent)
        self.asset_chart.setTitle("Varlık Dağılımı")
        self.asset_donut_view = QChartView(self.asset_chart)
        self.asset_donut_view.setRenderHint(QPainter.Antialiasing)
        self.asset_donut_view.setProperty("class", "CardWidget")
        self.asset_donut_view.setStyleSheet("background: transparent; border: none;")

        layout.addWidget(self.type_donut_view)
        layout.addWidget(self.asset_donut_view)

        outer.addWidget(donut_row, 2)

        # Varlık K/Z katkısı (attribution) çubuk grafiği
        attr_title = QLabel("Varlık K/Z Katkısı (TL)")
        attr_title.setProperty("class", "CardTitle")
        outer.addWidget(attr_title)
        self.attr_plot = pg.PlotWidget()
        self.attr_plot.setBackground("transparent")
        self.attr_plot.showGrid(x=False, y=True, alpha=0.3)
        outer.addWidget(self.attr_plot, 1)
        return widget

    def _create_calendar_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        info = QLabel("Aylık getiriler portföy değer geçmişinden (snapshot) hesaplanır.")
        info.setWordWrap(True)
        layout.addWidget(info)
        self.calendar_table = QTableWidget(0, 13)
        self.calendar_table.setHorizontalHeaderLabels(
            ["Yıl", "Oca", "Şub", "Mar", "Nis", "May", "Haz",
             "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
        )
        self.calendar_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.calendar_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.calendar_table)
        self.calendar_empty = QLabel("Henüz yeterli geçmiş veri yok.")
        self.calendar_empty.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.calendar_empty)
        return widget

    def _create_benchmark_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info = QLabel("Tüm seriler seçili aralığın başında 100'e normalize edilir.")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Aç/kapa kutuları
        toggles = QHBoxLayout()
        self.series_checks = {}
        for name in ("Portföy", "BIST 100", "USD/TRY", "Gram Altın"):
            cb = QCheckBox(name)
            cb.setChecked(True)
            cb.stateChanged.connect(lambda _s: self._render_benchmark())
            self.series_checks[name] = cb
            toggles.addWidget(cb)
        toggles.addStretch()
        layout.addLayout(toggles)

        self.benchmark_status = QLabel("")
        self.benchmark_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.benchmark_status)

        self.benchmark_plot = pg.PlotWidget(
            title="Normalize Karşılaştırma (Başlangıç = 100)",
            axisItems={"bottom": pg.DateAxisItem(orientation="bottom")},
        )
        self.benchmark_plot.setBackground("transparent")
        self.benchmark_plot.showGrid(x=True, y=True, alpha=0.3)
        self.benchmark_plot.addLegend()
        layout.addWidget(self.benchmark_plot)
        return widget

    # ---------- Tema ----------
    def apply_chart_theme(self, theme: str):
        self._theme = theme
        palette = COLORS.get(theme, COLORS["dark"])
        text_color = QColor(palette["text_primary"])
        from PySide6.QtGui import QBrush
        bg = QColor(palette["background"])
        for chart in (getattr(self, "type_chart", None), getattr(self, "asset_chart", None)):
            if chart is not None:
                chart.setBackgroundBrush(QBrush(bg))
                chart.setTitleBrush(text_color)
                chart.legend().setLabelColor(text_color)
        for plot in (getattr(self, "plot_widget", None), getattr(self, "benchmark_plot", None),
                     getattr(self, "attr_plot", None)):
            if plot is not None:
                plot.setBackground(bg)
                for ax_name in ("left", "bottom"):
                    ax = plot.getAxis(ax_name)
                    ax.setPen(pg.mkPen(color=palette["text_secondary"]))
                    ax.setTextPen(pg.mkPen(color=palette["text_secondary"]))

    # ---------- Veri ----------
    def on_analytics_loaded(self, data: dict):
        self.xirr_label.setText(f"XIRR (Yıllık): {data.get('xirr', 0) * 100:.2f}%")
        self.sharpe_label.setText(f"Sharpe: {data.get('sharpe', 0):.2f}")
        self.drawdown_label.setText(f"Max Düşüş: {data.get('max_drawdown', 0) * 100:.2f}%")
        self.volatility_label.setText(f"Volatilite: {data.get('volatility', 0) * 100:.2f}%")

        # Dağılım grafikleri
        self.type_donut_series.clear()
        alloc_type = data.get("allocation_type", {})
        if alloc_type.get("BIST", 0) > 0:
            self.type_donut_series.append("BIST", alloc_type["BIST"]).setColor(QColor("#00B5E2"))
        if alloc_type.get("TEFAS", 0) > 0:
            self.type_donut_series.append("TEFAS", alloc_type["TEFAS"]).setColor(QColor("#10B981"))

        self.asset_donut_series.clear()
        for i, item in enumerate(data.get("allocation_asset", [])[:10]):
            self.asset_donut_series.append(item["name"], item["value"]).setColor(
                QColor(PIE_PALETTE[i % len(PIE_PALETTE)])
            )

        # Varlık K/Z katkısı + aylık getiri takvimi
        self._render_attribution(data.get("attribution", []))

        # Geçmiş & yeniden çizim
        self._history = data.get("history", [])
        self._monthly_returns = data.get("monthly_returns", {})
        self._render_performance()
        self._render_calendar(self._history)

        # Benchmark verisini bir kez (portföy aralığı, en az 1 yıl) arka planda çek;
        # sonra bellekte tutulan veriyle yeniden çiz (her yenilemede yeni thread açma).
        if len(self._history) >= 2 and not self._benchmark:
            start = min(self._history[0]["date"], datetime.date.today() - datetime.timedelta(days=365))
            end = datetime.date.today()
            self.analytics_vm.load_benchmark(start, end)
        else:
            self._render_benchmark()

    def _on_benchmark_loaded(self, series: dict):
        self._benchmark = series
        self._benchmark_error = getattr(series, "error", "") or ""
        self._render_benchmark()

    def _render_attribution(self, attribution):
        if not hasattr(self, "attr_plot"):
            return
        self.attr_plot.clear()
        items = attribution[:15]
        if not items:
            return
        xs = list(range(len(items)))
        heights = [it["pnl"] for it in items]
        brushes = ["#10B981" if h >= 0 else "#DC2626" for h in heights]
        bar = pg.BarGraphItem(x=xs, height=heights, width=0.6, brushes=brushes)
        self.attr_plot.addItem(bar)
        ticks = [(i, items[i]["code"]) for i in range(len(items))]
        self.attr_plot.getAxis("bottom").setTicks([ticks])

    def _render_calendar(self, history):
        if not hasattr(self, "calendar_table"):
            return
        self.calendar_table.setRowCount(0)
        if len(history) < 2:
            self.calendar_empty.setVisible(True)
            self.calendar_table.setVisible(False)
            return

        returns = self._monthly_returns

        if not returns:
            self.calendar_empty.setVisible(True)
            self.calendar_table.setVisible(False)
            return

        self.calendar_empty.setVisible(False)
        self.calendar_table.setVisible(True)
        years = sorted({y for (y, _m) in returns})
        for y in years:
            r = self.calendar_table.rowCount()
            self.calendar_table.insertRow(r)
            self.calendar_table.setItem(r, 0, QTableWidgetItem(str(y)))
            for m in range(1, 13):
                val = returns.get((y, m))
                cell = QTableWidgetItem("" if val is None else f"{val:+.1f}%")
                if val is not None:
                    cell.setForeground(QColor("#10B981" if val >= 0 else "#DC2626"))
                self.calendar_table.setItem(r, m, cell)

    # ---------- Aralık / filtreleme ----------
    def _on_range_changed(self, rng: str):
        self._range = rng
        self._render_performance()
        self._render_benchmark()

    def _window_start(self):
        today = datetime.date.today()
        if self._range == "YBB":
            return datetime.date(today.year, 1, 1)
        days = RANGE_DAYS.get(self._range)
        if days is None:  # "Tümü"
            return None
        return today - datetime.timedelta(days=days)

    @staticmethod
    def _filter_points(points, start):
        if start is None:
            return list(points)
        return [p for p in points if p[0] >= start]

    # ---------- Çizim ----------
    def _render_performance(self):
        self.plot_widget.clear()
        start = self._window_start()
        hist = [h for h in self._history if start is None or h["date"] >= start]

        if len(hist) >= 2:
            self.empty_perf_label.setVisible(False)
            self.plot_widget.setVisible(True)
            xs = [time.mktime(h["date"].timetuple()) for h in hist]
            self.plot_widget.plot(xs, [h["total_value_try"] for h in hist],
                                  pen=pg.mkPen(color=COLORS[self._theme]["secondary"], width=3),
                                  name="Portföy Değeri")
            self.plot_widget.plot(xs, [h["total_cost_try"] for h in hist],
                                  pen=pg.mkPen(color=COLORS[self._theme]["text_secondary"], width=2,
                                               style=Qt.DashLine),
                                  name="Yatırılan Maliyet")
        else:
            self.empty_perf_label.setVisible(True)
            self.plot_widget.setVisible(False)

    def _render_benchmark(self):
        if not hasattr(self, "benchmark_plot"):
            return
        self.benchmark_plot.clear()
        start = self._window_start()

        # Tüm serileri tek sözlükte topla (Portföy + benchmark'lar)
        all_series = {}
        if self._history:
            all_series["Portföy"] = [(h["date"], h["total_value_try"]) for h in self._history]
        for name, pts in self._benchmark.items():
            all_series[name] = pts

        plotted = 0
        for name, pts in all_series.items():
            cb = self.series_checks.get(name)
            if cb is not None and not cb.isChecked():
                continue
            window = self._filter_points(pts, start)
            if len(window) < 2:
                continue
            base = window[0][1]
            if base == 0:
                continue
            xs = [time.mktime(d.timetuple()) for d, _ in window]
            ys = [v / base * 100 for _, v in window]
            color = SERIES_COLORS.get(name, "#9CA3AF")
            self.benchmark_plot.plot(xs, ys, pen=pg.mkPen(color=color, width=2), name=name)
            plotted += 1

        if plotted == 0:
            self.benchmark_status.setText(
                self._benchmark_error
                or "Karşılaştırma verisi yok. Portföy geçmişi henüz yetersiz olabilir."
            )
        else:
            self.benchmark_status.setText("")

import time
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                                 QLabel, QPushButton, QButtonGroup)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCharts import QChart, QChartView, QPieSeries
import pyqtgraph as pg
from app.config import COLORS
from app.utils.formatters import format_percent

PIE_PALETTE = ["#00B5E2", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#6B7280",
               "#EF4444", "#14B8A6", "#A855F7", "#F97316"]


class AnalyticsView(QWidget):
    def __init__(self, analytics_vm, portfolio_vm):
        super().__init__()
        self.analytics_vm = analytics_vm
        self.portfolio_vm = portfolio_vm
        self._theme = "dark"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_performance_tab(), "Performans")
        self.tabs.addTab(self._create_allocation_tab(), "Dağılım")
        self.tabs.addTab(self._create_benchmark_tab(), "Karşılaştırma")

        layout.addWidget(self.tabs)

        # Sinyaller
        self.analytics_vm.analytics_loaded.connect(self.on_analytics_loaded)
        self.apply_chart_theme(self._theme)

    def _create_performance_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Metrikler
        metrics_layout = QHBoxLayout()
        self.xirr_label = QLabel("XIRR: —")
        self.sharpe_label = QLabel("Sharpe: —")
        self.drawdown_label = QLabel("Max Düşüş: —")
        self.volatility_label = QLabel("Volatilite: —")
        for lbl in (self.xirr_label, self.sharpe_label, self.drawdown_label, self.volatility_label):
            lbl.setProperty("class", "CardWidget")
            metrics_layout.addWidget(lbl)
        layout.addLayout(metrics_layout)

        # Filtre Butonları (görsel; veri seyrek olduğunda tüm geçmiş gösterilir)
        filter_layout = QHBoxLayout()
        self.range_group = QButtonGroup(self)
        ranges = ["1H", "1A", "3A", "6A", "YBB", "1Y", "Tümü"]
        for r in ranges:
            btn = QPushButton(r)
            btn.setCheckable(True)
            self.range_group.addButton(btn)
            filter_layout.addWidget(btn)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # PyQtGraph — portföy değeri vs yatırılan maliyet
        self.plot_widget = pg.PlotWidget(
            axisItems={"bottom": pg.DateAxisItem(orientation="bottom")}
        )
        self.plot_widget.setBackground("transparent")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend()
        self.empty_perf_label = QLabel(
            "Henüz yeterli geçmiş veri yok. Uygulamayı birkaç gün kullandıkça "
            "portföy değer geçmişi otomatik birikecek."
        )
        self.empty_perf_label.setAlignment(Qt.AlignCenter)
        self.empty_perf_label.setWordWrap(True)
        layout.addWidget(self.empty_perf_label)
        layout.addWidget(self.plot_widget)

        return widget

    def _create_allocation_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)

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
        return widget

    def _create_benchmark_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        info = QLabel(
            "Karşılaştırma: Portföy getirisi 100'e normalize edilerek gösterilir. "
            "BIST 100 / TÜFE / USD / altın endeksleri bir sonraki sürümde eklenecektir."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        self.benchmark_plot = pg.PlotWidget(
            title="Normalize Portföy Getirisi (Başlangıç = 100)",
            axisItems={"bottom": pg.DateAxisItem(orientation="bottom")},
        )
        self.benchmark_plot.setBackground("transparent")
        self.benchmark_plot.showGrid(x=True, y=True, alpha=0.3)
        layout.addWidget(self.benchmark_plot)
        return widget

    def apply_chart_theme(self, theme: str):
        self._theme = theme
        palette = COLORS.get(theme, COLORS["dark"])
        text_color = QColor(palette["text_primary"])
        for chart in (getattr(self, "type_chart", None), getattr(self, "asset_chart", None)):
            if chart is not None:
                chart.setTitleBrush(text_color)
                chart.legend().setLabelColor(text_color)
        for plot in (getattr(self, "plot_widget", None), getattr(self, "benchmark_plot", None)):
            if plot is not None:
                for ax_name in ("left", "bottom"):
                    ax = plot.getAxis(ax_name)
                    ax.setPen(pg.mkPen(color=palette["text_secondary"]))
                    ax.setTextPen(pg.mkPen(color=palette["text_secondary"]))

    def on_analytics_loaded(self, data: dict):
        xirr = data.get("xirr", 0) * 100
        self.xirr_label.setText(f"XIRR (Yıllık): {xirr:.2f}%")
        self.sharpe_label.setText(f"Sharpe: {data.get('sharpe', 0):.2f}")
        self.drawdown_label.setText(f"Max Düşüş: {data.get('max_drawdown', 0) * 100:.2f}%")
        self.volatility_label.setText(f"Volatilite: {data.get('volatility', 0) * 100:.2f}%")

        # Tip Dağılımı
        self.type_donut_series.clear()
        alloc_type = data.get("allocation_type", {})
        if alloc_type.get("BIST", 0) > 0:
            sl = self.type_donut_series.append("BIST", alloc_type["BIST"])
            sl.setColor(QColor("#00B5E2"))
        if alloc_type.get("TEFAS", 0) > 0:
            sl = self.type_donut_series.append("TEFAS", alloc_type["TEFAS"])
            sl.setColor(QColor("#10B981"))

        # Varlık Dağılımı
        self.asset_donut_series.clear()
        alloc_asset = data.get("allocation_asset", [])
        for i, item in enumerate(alloc_asset[:10]):
            sl = self.asset_donut_series.append(item["name"], item["value"])
            sl.setColor(QColor(PIE_PALETTE[i % len(PIE_PALETTE)]))

        # Performans grafiği: gerçek snapshot geçmişi
        history = data.get("history", [])
        self.plot_widget.clear()
        self.benchmark_plot.clear()

        if len(history) >= 2:
            self.empty_perf_label.setVisible(False)
            self.plot_widget.setVisible(True)
            xs = [time.mktime(h["date"].timetuple()) for h in history]
            value_series = [h["total_value_try"] for h in history]
            cost_series = [h["total_cost_try"] for h in history]
            self.plot_widget.plot(xs, value_series,
                                  pen=pg.mkPen(color=COLORS[self._theme]["secondary"], width=3),
                                  name="Portföy Değeri")
            self.plot_widget.plot(xs, cost_series,
                                  pen=pg.mkPen(color=COLORS[self._theme]["text_secondary"], width=2,
                                               style=Qt.DashLine),
                                  name="Yatırılan Maliyet")

            # Normalize getiri (başlangıç=100)
            base = value_series[0] if value_series[0] > 0 else 1.0
            norm = [v / base * 100 for v in value_series]
            self.benchmark_plot.plot(xs, norm,
                                     pen=pg.mkPen(color=COLORS[self._theme]["secondary"], width=3),
                                     name="Portföy")
        else:
            self.empty_perf_label.setVisible(True)
            self.plot_widget.setVisible(False)

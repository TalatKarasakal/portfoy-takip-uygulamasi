import datetime
import time

import pyqtgraph as pg
from PySide6.QtCharts import QChart, QChartView, QPieSeries
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import COLORS
from app.views.widgets.chart_interaction import configure_pie_slice, install_crosshair

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
        self.tabs.addTab(self._create_dividend_tab(), "Temettü")
        self.tabs.addTab(self._create_lot_tab(), "Lotlar")
        layout.addWidget(self.tabs)

        self.analytics_vm.analytics_loaded.connect(self.on_analytics_loaded)
        self.analytics_vm.benchmark_loaded.connect(self._on_benchmark_loaded)
        self.analytics_vm.dividend_action_completed.connect(
            lambda message: QMessageBox.information(self, "Temettü", message)
        )
        self.analytics_vm.error_occurred.connect(
            lambda message: QMessageBox.warning(self, "Analiz", message)
        )
        self.apply_chart_theme(self._theme)

    # ---------- Tab kurulumları ----------
    def _create_performance_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        metrics_layout = QHBoxLayout()
        self.xirr_label = QLabel("XIRR: —")
        self.twr_label = QLabel("TWR: —")
        self.open_return_label = QLabel("Açık Pozisyon Getirisi: —")
        self.realized_label = QLabel("Gerçekleşmiş K/Z: —")
        self.unrealized_label = QLabel("Gerçekleşmemiş K/Z: —")
        self.sharpe_label = QLabel("Sharpe: —")
        self.drawdown_label = QLabel("Max Düşüş: —")
        self.volatility_label = QLabel("Volatilite: —")
        for lbl in (
            self.xirr_label,
            self.twr_label,
            self.open_return_label,
            self.realized_label,
            self.unrealized_label,
            self.sharpe_label,
            self.drawdown_label,
            self.volatility_label,
        ):
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
        install_crosshair(self.plot_widget)
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
        install_crosshair(self.benchmark_plot)
        layout.addWidget(self.benchmark_plot)
        return widget

    def _create_dividend_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        metrics = QHBoxLayout()
        self.dividend_net_label = QLabel("Son 12 Ay Net Temettü: —")
        self.dividend_cost_yield_label = QLabel("Maliyet Bazlı Verim: —")
        self.dividend_market_yield_label = QLabel("Piyasa Değeri Bazlı Verim: —")
        for label in (
            self.dividend_net_label,
            self.dividend_cost_yield_label,
            self.dividend_market_yield_label,
        ):
            label.setProperty("class", "CardWidget")
            metrics.addWidget(label)
        layout.addLayout(metrics)
        actions = QHBoxLayout()
        add_button = QPushButton("Plan Ekle")
        add_button.clicked.connect(self._add_dividend_plan)
        paid_button = QPushButton("Seçili Planı Ödendi Yap")
        paid_button.clicked.connect(self._mark_dividend_paid)
        actions.addWidget(add_button)
        actions.addWidget(paid_button)
        actions.addStretch()
        layout.addLayout(actions)
        self.dividend_plan_table = QTableWidget(0, 7)
        self.dividend_plan_table.setHorizontalHeaderLabels(
            ["Kod", "Ödeme", "Hisse Başı", "Beklenen Adet", "Eldeki Adet", "Durum", "Not"]
        )
        self.dividend_plan_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dividend_plan_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(QLabel("Planlar"))
        layout.addWidget(self.dividend_plan_table)
        self.dividend_history_table = QTableWidget(0, 6)
        self.dividend_history_table.setHorizontalHeaderLabels(
            ["Tarih", "Kod", "Adet", "Hisse Başı", "Net Tutar", "Not"]
        )
        self.dividend_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dividend_history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(QLabel("Ödeme Geçmişi"))
        layout.addWidget(self.dividend_history_table)
        return widget

    def _create_lot_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        info = QLabel(
            "Açık FIFO/LIFO lotları, WAC havuzu ve satış-lot eşleşmeleri seçili "
            "maliyet yöntemine göre gösterilir."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        self.lot_table = QTableWidget(0, 10)
        self.lot_table.setHorizontalHeaderLabels(
            [
                "Tür", "Kod", "Yöntem", "Alım ID", "Satış ID", "Tarih",
                "Adet", "Birim Maliyet", "Satış Fiyatı", "Gerçekleşen K/Z",
            ]
        )
        self.lot_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.lot_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.lot_table)
        return widget

    # ---------- Tema ----------
    def apply_chart_theme(self, theme: str, palette_object=None):
        self._theme = theme
        palette = (
            palette_object.__dict__
            if palette_object is not None
            else COLORS.get(theme, COLORS["dark"])
        )
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
        xirr_result = data.get("xirr_result")
        xirr_rate = getattr(xirr_result, "rate", None)
        xirr_status = getattr(getattr(xirr_result, "status", None), "value", "hesaplanamadı")
        self.xirr_label.setText(
            f"XIRR (Yıllık): {xirr_rate * 100:.2f}%"
            if xirr_rate is not None
            else f"XIRR: {xirr_status}"
        )
        twr = data.get("twr")
        self.twr_label.setText(f"TWR: {twr * 100:.2f}%" if twr is not None else "TWR: —")
        open_return = data.get("open_position_return")
        self.open_return_label.setText(
            f"Açık Pozisyon: {open_return * 100:.2f}%\n"
            f"Pay: {data.get('unrealized_pnl', 0):,.2f} / Payda: {data.get('total_cost', 0):,.2f}"
            if open_return is not None
            else "Açık Pozisyon Getirisi: —"
        )
        self.realized_label.setText(f"Gerçekleşmiş K/Z: {data.get('realized_pnl', 0):,.2f} TL")
        self.unrealized_label.setText(
            f"Gerçekleşmemiş K/Z: {data.get('unrealized_pnl', 0):,.2f} TL"
        )
        self.sharpe_label.setText(f"Sharpe: {data.get('sharpe', 0):.2f}")
        self.drawdown_label.setText(f"Max Düşüş: {data.get('max_drawdown', 0) * 100:.2f}%")
        self.volatility_label.setText(f"Volatilite: {data.get('volatility', 0) * 100:.2f}%")

        # Dağılım grafikleri
        self.type_donut_series.clear()
        alloc_type = data.get("allocation_type", {})
        if alloc_type.get("BIST", 0) > 0:
            slice_item = self.type_donut_series.append("BIST", alloc_type["BIST"])
            slice_item.setColor(QColor("#00B5E2"))
            configure_pie_slice(slice_item, "BIST", alloc_type["BIST"])
        if alloc_type.get("TEFAS", 0) > 0:
            slice_item = self.type_donut_series.append("TEFAS", alloc_type["TEFAS"])
            slice_item.setColor(QColor("#10B981"))
            configure_pie_slice(slice_item, "TEFAS", alloc_type["TEFAS"])

        self.asset_donut_series.clear()
        for i, item in enumerate(data.get("allocation_asset", [])[:10]):
            slice_item = self.asset_donut_series.append(item["name"], item["value"])
            slice_item.setColor(QColor(PIE_PALETTE[i % len(PIE_PALETTE)]))
            configure_pie_slice(slice_item, item["name"], item["value"])

        # Varlık K/Z katkısı + aylık getiri takvimi
        self._render_attribution(data.get("attribution", []))

        # Geçmiş & yeniden çizim
        self._history = data.get("history", [])
        self._monthly_returns = data.get("monthly_returns", {})
        self._render_performance()
        self._render_calendar(self._history)
        self._render_dividends(data.get("dividends", {}), data.get("asset_choices", []))
        self._render_lots(data.get("lot_analysis", []))

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

    def _render_dividends(self, data, asset_choices):
        self._asset_choices = asset_choices
        self.dividend_net_label.setText(
            f"Son 12 Ay Net Temettü: {data.get('last_12_months_net', 0):,.2f} TL"
        )

        def percent(value):
            return "—" if value is None else f"{value * 100:.2f}%"

        self.dividend_cost_yield_label.setText(
            f"Maliyet Bazlı Verim: {percent(data.get('yield_on_cost'))}"
        )
        self.dividend_market_yield_label.setText(
            f"Piyasa Değeri Bazlı Verim: {percent(data.get('yield_on_market'))}"
        )
        self.dividend_plan_table.setRowCount(0)
        for plan in data.get("plans", []):
            row = self.dividend_plan_table.rowCount()
            self.dividend_plan_table.insertRow(row)
            values = [
                plan["code"],
                plan["payment_date"].isoformat(),
                f"{plan['gross_per_share']:.6f}".rstrip("0").rstrip("."),
                "—" if plan["expected_quantity"] is None else str(plan["expected_quantity"]),
                str(plan["current_quantity"]),
                plan["status"],
                plan["note"],
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, plan)
                self.dividend_plan_table.setItem(row, column, item)
        self.dividend_history_table.setRowCount(0)
        for dividend in data.get("history", []):
            row = self.dividend_history_table.rowCount()
            self.dividend_history_table.insertRow(row)
            values = [
                dividend["date"].isoformat(),
                dividend["code"],
                str(dividend["quantity"]),
                str(dividend["gross_per_share"]),
                f"{dividend['net_amount']:,.2f}",
                dividend["note"],
            ]
            for column, value in enumerate(values):
                self.dividend_history_table.setItem(row, column, QTableWidgetItem(value))

    def _render_lots(self, analysis):
        self.lot_table.setRowCount(0)
        for asset in analysis:
            for lot in asset.get("open_lots", []):
                self._append_lot_row(
                    [
                        "Açık Lot",
                        asset["code"],
                        lot["method"],
                        lot["buy_transaction_id"] or "WAC Havuzu",
                        "—",
                        lot["date"].isoformat(),
                        lot["quantity"],
                        lot["unit_cost"],
                        "—",
                        "—",
                    ]
                )
            for match in asset.get("lot_matches", []):
                self._append_lot_row(
                    [
                        "Satış Eşleşmesi",
                        asset["code"],
                        match["method"],
                        match["buy_transaction_id"] or "WAC Havuzu",
                        match["sale_transaction_id"] or "—",
                        "—",
                        match["quantity"],
                        match["unit_cost"],
                        match["sale_unit_price"],
                        match["realized_pnl"],
                    ]
                )

    def _append_lot_row(self, values):
        row = self.lot_table.rowCount()
        self.lot_table.insertRow(row)
        for column, value in enumerate(values):
            if isinstance(value, float):
                text = f"{value:.6f}".rstrip("0").rstrip(".")
            else:
                text = str(value)
            self.lot_table.setItem(row, column, QTableWidgetItem(text))

    def _add_dividend_plan(self):
        if not getattr(self, "_asset_choices", []):
            QMessageBox.warning(self, "Temettü", "Plan için açık bir varlık bulunamadı.")
            return
        dialog = DividendPlanDialog(self._asset_choices, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.values()
            self.analytics_vm.add_dividend_plan(**data)

    def _mark_dividend_paid(self):
        row = self.dividend_plan_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Temettü", "Önce planlanan bir satır seçin.")
            return
        plan = self.dividend_plan_table.item(row, 0).data(Qt.UserRole)
        if plan["status"] != "PLANNED":
            QMessageBox.warning(self, "Temettü", "Bu plan zaten sonuçlandırılmış.")
            return
        quantity, accepted = QInputDialog.getDouble(
            self,
            "Temettü Adedini Doğrula",
            "Ödeme tarihinde elde bulunan ve temettüye hak kazanan adet:",
            plan["current_quantity"],
            0.000001,
            1_000_000_000,
            6,
        )
        if accepted:
            self.analytics_vm.mark_dividend_paid(plan["id"], quantity)

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
        install_crosshair(self.plot_widget)
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
        install_crosshair(self.benchmark_plot)
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


class DividendPlanDialog(QDialog):
    def __init__(self, assets, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Temettü Planı Ekle")
        form = QFormLayout(self)
        self.asset_combo = QComboBox()
        for asset in assets:
            self.asset_combo.addItem(asset["code"], asset)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.per_share = QDoubleSpinBox()
        self.per_share.setDecimals(6)
        self.per_share.setRange(0.000001, 1_000_000_000)
        self.quantity = QDoubleSpinBox()
        self.quantity.setDecimals(6)
        self.quantity.setRange(0, 1_000_000_000)
        self.quantity.setSpecialValueText("Ödeme sırasında doğrula")
        self.note = QLineEdit()
        form.addRow("Varlık:", self.asset_combo)
        form.addRow("Ödeme Tarihi:", self.date_edit)
        form.addRow("Hisse Başı Brüt:", self.per_share)
        form.addRow("Beklenen Adet:", self.quantity)
        form.addRow("Not:", self.note)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        asset = self.asset_combo.currentData()
        return {
            "asset_id": asset["id"],
            "payment_date": self.date_edit.date().toPython(),
            "gross_per_share": self.per_share.value(),
            "expected_quantity": self.quantity.value() or None,
            "note": self.note.text(),
        }

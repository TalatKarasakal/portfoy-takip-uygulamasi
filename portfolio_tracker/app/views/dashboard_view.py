import time
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableView, QHeaderView
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCharts import QChart, QChartView, QPieSeries
import pyqtgraph as pg
from app.views.widgets.kpi_card import KPICard
from app.views.transactions_view import TransactionTableModel
from app.utils.formatters import format_currency, format_percent
from app.utils.display import display
from app.config import COLORS

# Donut grafiği dilim renk paleti (Türk kırmızısı vurgu rengi K/Z için kullanılmaz,
# burada nötr/dağılım amaçlı bir palet tercih edildi).
PIE_PALETTE = ["#00B5E2", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#6B7280"]


class DashboardView(QWidget):
    def __init__(self, view_model):
        super().__init__()
        self.view_model = view_model
        self._theme = "dark"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # --- Üst: KPI Kartları (4 adet) ---
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(15)

        self.total_val_card = KPICard("Toplam Portföy Değeri", "currency")
        self.daily_chg_card = KPICard("Bugünkü Değişim", "currency")
        self.total_pnl_card = KPICard("Toplam K/Z", "currency")
        self.best_worst_card = KPICard("En İyi / En Kötü", "currency")

        kpi_layout.addWidget(self.total_val_card)
        kpi_layout.addWidget(self.daily_chg_card)
        kpi_layout.addWidget(self.total_pnl_card)
        kpi_layout.addWidget(self.best_worst_card)

        layout.addLayout(kpi_layout)

        # --- Orta: Grafikler ---
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(20)

        # Donut Chart (Varlık Dağılımı)
        self.donut_series = QPieSeries()
        self.donut_series.setHoleSize(0.4)

        self.donut_chart = QChart()
        self.donut_chart.addSeries(self.donut_series)
        self.donut_chart.setBackgroundBrush(Qt.transparent)
        self.donut_chart.setTitle("Varlık Dağılımı")
        self.donut_chart.legend().setAlignment(Qt.AlignBottom)
        self.donut_chart.setAnimationOptions(QChart.SeriesAnimations)

        self.donut_view = QChartView(self.donut_chart)
        self.donut_view.setRenderHint(QPainter.Antialiasing)
        self.donut_view.setProperty("class", "CardWidget")
        self.donut_view.setStyleSheet("background: transparent; border: none;")

        # Line Chart (PyQtGraph) — gerçek snapshot geçmişi, tarih ekseni ile
        self.line_view = pg.PlotWidget(
            title="Portföy Değeri (Son 90 Gün)",
            axisItems={"bottom": pg.DateAxisItem(orientation="bottom")},
        )
        self.line_view.setBackground("transparent")
        self.line_view.showGrid(x=True, y=True, alpha=0.3)
        self.line_view.setProperty("class", "CardWidget")

        charts_layout.addWidget(self.donut_view, 1)
        charts_layout.addWidget(self.line_view, 2)

        layout.addLayout(charts_layout, 1)

        # --- Alt: Son 5 İşlem ---
        self.tx_table = QTableView()
        self.tx_model = TransactionTableModel()
        self.tx_table.setModel(self.tx_model)
        self.tx_table.setProperty("class", "CardWidget")

        header = self.tx_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.tx_table.setSelectionBehavior(QTableView.SelectRows)
        self.tx_table.setFixedHeight(180)

        layout.addWidget(self.tx_table)

        # ViewModel bağlantıları
        self.view_model.kpi_updated.connect(self.update_kpi_cards)

        self.apply_chart_theme(self._theme)

    def apply_chart_theme(self, theme: str):
        """Tema değişiminde grafik metin/eksen renklerini günceller."""
        self._theme = theme
        palette = COLORS.get(theme, COLORS["dark"])
        text_color = QColor(palette["text_primary"])
        secondary = QColor(palette["text_secondary"])

        self.donut_chart.setTitleBrush(text_color)
        self.donut_chart.legend().setLabelColor(text_color)

        axis_pen = pg.mkPen(color=palette["text_secondary"])
        for ax_name in ("left", "bottom"):
            ax = self.line_view.getAxis(ax_name)
            ax.setPen(axis_pen)
            ax.setTextPen(pg.mkPen(color=palette["text_secondary"]))
        self.line_view.setTitle("Portföy Değeri (Son 90 Gün)", color=palette["text_primary"])

    def update_kpi_cards(self, data: dict):
        # Toplam değer + karşı para birimi alt satırı
        total_try = data.get("total_value_try", 0)
        self.total_val_card.set_value(total_try)
        self.total_val_card.set_subtitle(display.format_opposite(total_try))

        # Bugünkü değişim (TL ana, yüzde alt)
        daily = data.get("daily_change_try", 0)
        daily_pct = data.get("daily_change_pct", 0)
        self.daily_chg_card.set_value(daily, colored=True)
        self.daily_chg_card.set_subtitle(format_percent(daily_pct), value_for_color=daily_pct, colored=True)

        # Toplam K/Z (TL ana, yüzde alt)
        total_pnl = data.get("total_pnl", 0)
        pnl_pct = data.get("pnl_pct", 0)
        self.total_pnl_card.set_value(total_pnl, colored=True)
        self.total_pnl_card.set_subtitle(format_percent(pnl_pct), value_for_color=pnl_pct, colored=True)

        # En iyi / En kötü pozisyon
        best = data.get("best")
        worst = data.get("worst")
        if best:
            self.best_worst_card.set_primary_text(
                f"▲ {best['code']}  {format_percent(best['pnl_pct'])}",
                value_for_color=best["pnl_pct"], colored=True
            )
        else:
            self.best_worst_card.set_primary_text("—")
        if worst:
            self.best_worst_card.set_subtitle(
                f"▼ {worst['code']}  {format_percent(worst['pnl_pct'])}",
                value_for_color=worst["pnl_pct"], colored=True
            )
        else:
            self.best_worst_card.set_subtitle("")

        # Donut: bireysel varlıklar (ilk 5 + Diğer)
        self.donut_series.clear()
        port_data = data.get("portfolio_items", [])
        sorted_assets = sorted(port_data, key=lambda x: x["current_value"], reverse=True)
        top_assets = sorted_assets[:5]
        other_assets = sorted_assets[5:]

        color_i = 0
        for item in top_assets:
            if item["current_value"] > 0:
                sl = self.donut_series.append(item["code"], item["current_value"])
                sl.setColor(QColor(PIE_PALETTE[color_i % len(PIE_PALETTE)]))
                color_i += 1

        if other_assets:
            other_val = sum(x["current_value"] for x in other_assets)
            if other_val > 0:
                sl = self.donut_series.append("Diğer", other_val)
                sl.setColor(QColor(PIE_PALETTE[-1]))

        # Çizgi grafik: gerçek snapshot geçmişi
        self.line_view.clear()
        history = data.get("history", [])
        if len(history) >= 2:
            xs = [time.mktime(h["date"].timetuple()) for h in history]
            ys = [h["total_value_try"] for h in history]
            self.line_view.plot(xs, ys, pen=pg.mkPen(color=COLORS[self._theme]["secondary"], width=3))
        elif history:
            # Tek snapshot: düz bir nokta göster
            h = history[0]
            x = time.mktime(h["date"].timetuple())
            self.line_view.plot([x], [h["total_value_try"]], symbol="o",
                                pen=None, symbolBrush=COLORS[self._theme]["secondary"])

        # Son işlemler
        recent_tx = self.view_model.get_recent_transactions(limit=5)
        self.tx_model.update_data(recent_tx or [])

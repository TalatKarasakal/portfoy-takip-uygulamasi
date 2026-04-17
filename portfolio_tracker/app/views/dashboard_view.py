from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableView, QHeaderView
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtCharts import QChart, QChartView, QPieSeries
import pyqtgraph as pg
from app.views.widgets.kpi_card import KPICard
from app.views.transactions_view import TransactionTableModel

class DashboardView(QWidget):
    def __init__(self, view_model):
        super().__init__()
        self.view_model = view_model
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # --- Üst: KPI Kartları (4 adet) ---
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(15)
        
        self.total_val_card = KPICard("Toplam Portföy Değeri (TL)", "currency")
        self.daily_chg_card = KPICard("Bugünkü Değişim", "currency")
        self.total_pnl_card = KPICard("Toplam K/Z", "percent")
        self.best_worst_card = KPICard("En İyi / En Kötü", "currency") # Placeholder for now, requires complex layout
        
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
        self.donut_chart.setTitleBrush(Qt.white) # Tema atamasında renk güncellenecek
        self.donut_chart.setTitle("Varlık Dağılımı")
        self.donut_chart.legend().setAlignment(Qt.AlignBottom)
        self.donut_chart.legend().setLabelColor(Qt.white)
        self.donut_chart.setAnimationOptions(QChart.SeriesAnimations)
        
        self.donut_view = QChartView(self.donut_chart)
        self.donut_view.setRenderHint(QPainter.Antialiasing)
        self.donut_view.setProperty("class", "CardWidget")
        self.donut_view.setStyleSheet("background: transparent; border: none;")
        
        # Line Chart (PyQtGraph)
        self.line_view = pg.PlotWidget(title="Portföy Değeri Zaman Serisi")
        self.line_view.setBackground('transparent')
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
        
    def update_kpi_cards(self, data: dict):
        self.total_val_card.set_value(data.get("total_value_try", 0))
        self.daily_chg_card.set_value(data.get("daily_change_try", 0), colored=True)
        self.total_pnl_card.set_value(data.get("pnl_pct", 0), colored=True)
        
        # Update Donut Chart to show individual assets
        self.donut_series.clear()
        port_data = data.get("portfolio_items", [])
        
        # Sort by current_value and get top 5, group rest into "Diğer"
        sorted_assets = sorted(port_data, key=lambda x: x["current_value"], reverse=True)
        top_assets = sorted_assets[:5]
        other_assets = sorted_assets[5:]
        
        for item in top_assets:
            if item["current_value"] > 0:
                self.donut_series.append(item["code"], item["current_value"])
                
        if other_assets:
            other_val = sum(x["current_value"] for x in other_assets)
            if other_val > 0:
                self.donut_series.append("Diğer", other_val)
            
        # Update Line Chart (Mock data for now until snapshot integration)
        self.line_view.clear()
        if port_data:
            # Just plotting a horizontal line of current value as placeholder for history
            val = data.get("total_value_try", 0)
            self.line_view.plot([0, 1, 2, 3], [val * 0.9, val * 0.95, val * 0.98, val], pen=pg.mkPen(color='#E30A17', width=3))
            
        # Update Transactions
        recent_tx = self.view_model.get_recent_transactions(limit=5)
        if recent_tx:
            self.tx_model.update_data(recent_tx)

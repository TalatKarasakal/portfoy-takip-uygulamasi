from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                                 QLabel, QPushButton, QButtonGroup, QGridLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtCharts import QChart, QChartView, QPieSeries
import pyqtgraph as pg

class AnalyticsView(QWidget):
    def __init__(self, analytics_vm, portfolio_vm):
        super().__init__()
        self.analytics_vm = analytics_vm
        self.portfolio_vm = portfolio_vm
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_performance_tab(), "Performans")
        self.tabs.addTab(self._create_allocation_tab(), "Dağılım")
        self.tabs.addTab(self._create_benchmark_tab(), "Karşılaştırma")
        
        layout.addWidget(self.tabs)
        
        # Sinyaller
        self.analytics_vm.analytics_loaded.connect(self.on_analytics_loaded)
        
    def _create_performance_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Metrikler
        metrics_layout = QHBoxLayout()
        self.xirr_label = QLabel("XIRR: Yükleniyor...")
        self.sharpe_label = QLabel("Sharpe Oranı: N/A")
        self.drawdown_label = QLabel("Max Düşüş: N/A")
        metrics_layout.addWidget(self.xirr_label)
        metrics_layout.addWidget(self.sharpe_label)
        metrics_layout.addWidget(self.drawdown_label)
        layout.addLayout(metrics_layout)
        
        # Filtre Butonları
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
        
        # PyQtGraph
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('transparent')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        layout.addWidget(self.plot_widget)
        
        return widget
        
    def _create_allocation_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        self.type_donut_series = QPieSeries()
        self.type_donut_series.setHoleSize(0.4)
        type_chart = QChart()
        type_chart.addSeries(self.type_donut_series)
        type_chart.setBackgroundBrush(Qt.transparent)
        type_chart.setTitleBrush(Qt.white)
        type_chart.setTitle("BIST / TEFAS Dağılımı")
        type_chart.legend().setLabelColor(Qt.white)
        self.type_donut_view = QChartView(type_chart)
        self.type_donut_view.setRenderHint(QPainter.Antialiasing)
        self.type_donut_view.setProperty("class", "CardWidget")
        self.type_donut_view.setStyleSheet("background: transparent; border: none;")
        
        self.asset_donut_series = QPieSeries()
        self.asset_donut_series.setHoleSize(0.4)
        asset_chart = QChart()
        asset_chart.addSeries(self.asset_donut_series)
        asset_chart.setBackgroundBrush(Qt.transparent)
        asset_chart.setTitleBrush(Qt.white)
        asset_chart.setTitle("Varlık Dağılımı")
        asset_chart.legend().setLabelColor(Qt.white)
        self.asset_donut_view = QChartView(asset_chart)
        self.asset_donut_view.setRenderHint(QPainter.Antialiasing)
        self.asset_donut_view.setProperty("class", "CardWidget")
        self.asset_donut_view.setStyleSheet("background: transparent; border: none;")
        
        layout.addWidget(self.type_donut_view)
        layout.addWidget(self.asset_donut_view)
        return widget
        
    def _create_benchmark_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.benchmark_plot = pg.PlotWidget(title="Karşılaştırma Grafiği (BIST 100, TÜFE, USD/TRY)")
        self.benchmark_plot.setBackground('transparent')
        self.benchmark_plot.showGrid(x=True, y=True, alpha=0.3)
        layout.addWidget(self.benchmark_plot)
        return widget
        
    def on_analytics_loaded(self, data: dict):
        xirr = data.get("xirr", 0) * 100
        self.xirr_label.setText(f"XIRR (Yıllık Getiri): {xirr:.2f}%")
        
        # Tip Dağılımı
        self.type_donut_series.clear()
        alloc_type = data.get("allocation_type", {})
        if alloc_type.get("BIST", 0) > 0:
            slice1 = self.type_donut_series.append("BIST", alloc_type["BIST"])
            slice1.setColor(Qt.red)
        if alloc_type.get("TEFAS", 0) > 0:
            slice2 = self.type_donut_series.append("TEFAS", alloc_type["TEFAS"])
            slice2.setColor(Qt.blue)
            
        # Varlık Dağılımı
        self.asset_donut_series.clear()
        alloc_asset = data.get("allocation_asset", [])
        for item in alloc_asset[:10]: # Top 10
            self.asset_donut_series.append(item["name"], item["value"])
            
        # Plot Mock Performance Data to prevent empty screen (Until Snapshot DB is hydrated)
        self.plot_widget.clear()
        self.benchmark_plot.clear()
        
        total_val = sum(a["value"] for a in alloc_asset)
        if total_val > 0:
            self.plot_widget.plot([1, 2, 3, 4, 5], [total_val*0.8, total_val*0.85, total_val*0.9, total_val*0.95, total_val], pen=pg.mkPen(color='#E30A17', width=3))
            
            # Benchmark Mock (Portfolio vs BIST100 mock)
            self.benchmark_plot.plot([1, 2, 3, 4, 5], [100, 105, 102, 108, 115], pen=pg.mkPen(color='#00B5E2', width=3, name="Portföy"))
            self.benchmark_plot.plot([1, 2, 3, 4, 5], [100, 98, 101, 104, 105], pen=pg.mkPen(color='#E5E7EB', width=2, style=Qt.DashLine, name="BIST 100"))

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                 QPushButton, QStackedWidget, QLabel, QApplication)
from PySide6.QtCore import Qt, QSize
import qtawesome as qta
import os
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Portföy Takip ve Analiz")
        self.setMinimumSize(1200, 800)
        
        # Ana Layout (Yatay: Sol Sidebar, Sağ İçerik)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- Sol Sidebar ---
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(10)
        
        # Logo veya Başlık
        logo_label = QLabel("Yatırım Portföyü")
        logo_label.setObjectName("logo_label")
        logo_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(logo_label)
        sidebar_layout.addSpacing(30)
        
        # Sekme Butonları
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "Dashboard", "fa5s.chart-pie"),
            ("portfolio", "Portföy", "fa5s.wallet"),
            ("transactions", "İşlemler", "fa5s.exchange-alt"),
            ("analytics", "Analiz", "fa5s.chart-line"),
            ("assistant", "Asistan", "fa5s.robot"),
            ("alerts", "Uyarılar", "fa5s.bell"),
            ("settings", "Ayarlar", "fa5s.cog"),
        ]
        
        for nav_id, title, icon_name in nav_items:
            btn = QPushButton(title)
            btn.setIcon(qta.icon(icon_name, color="#6B7280"))
            btn.setIconSize(QSize(20, 20))
            btn.setObjectName(f"nav_btn_{nav_id}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=nav_id: self.switch_tab(idx))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[nav_id] = btn

        sidebar_layout.addStretch()
        main_layout.addWidget(self.sidebar)
        
        # --- Sağ İçerik Alanı (Stacked Widget) ---
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("main_stack")
        main_layout.addWidget(self.stacked_widget)
        
        from app.views.dashboard_view import DashboardView
        from app.views.portfolio_view import PortfolioView
        from app.views.transactions_view import TransactionsView
        from app.views.analytics_view import AnalyticsView
        from app.views.settings_view import SettingsView
        from app.views.alerts_view import AlertsView
        from app.views.ai_assistant_view import AIAssistantView

        from app.viewmodels.portfolio_viewmodel import PortfolioViewModel
        from app.viewmodels.transaction_viewmodel import TransactionViewModel
        from app.viewmodels.analytics_viewmodel import AnalyticsViewModel
        from app.viewmodels.settings_viewmodel import SettingsViewModel
        from app.viewmodels.ai_viewmodel import AIViewModel

        self.portfolio_vm = PortfolioViewModel()
        self.transaction_vm = TransactionViewModel()
        self.analytics_vm = AnalyticsViewModel()
        self.settings_vm = SettingsViewModel()
        self.ai_vm = AIViewModel()

        self.settings_vm.settings_loaded.connect(self.apply_theme)

        # Yapay zeka asistanını güncel portföy verisiyle besle
        self.portfolio_vm.data_loaded.connect(self.ai_vm.update_portfolio_data)
        self.portfolio_vm.kpi_updated.connect(self.ai_vm.update_kpi_data)

        self.views = {
            "dashboard": DashboardView(self.portfolio_vm),
            "portfolio": PortfolioView(self.portfolio_vm),
            "transactions": TransactionsView(self.transaction_vm),
            "analytics": AnalyticsView(self.analytics_vm, self.portfolio_vm),
            "assistant": AIAssistantView(self.ai_vm),
            "alerts": AlertsView(),
            "settings": SettingsView(self.settings_vm)
        }
        
        for view_name, view_widget in self.views.items():
            self.stacked_widget.addWidget(view_widget)

        # Varsayılan sekme
        self.switch_tab("dashboard")
        
        # İlk yüklemeler
        self.portfolio_vm.load_data()
        self.settings_vm.load_settings()

    def apply_theme(self, settings_dict):
        theme = settings_dict.get("theme", "dark")
        # Ensure system default uses dark for now or implement system match
        if theme == "system":
            theme = "dark"
            
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        style_path = os.path.join(base_dir, "app", "resources", "styles", f"{theme}.qss")
        
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                QApplication.instance().setStyleSheet(f.read())
        else:
            print(f"Theme file not found: {style_path}")

    def switch_tab(self, tab_id: str):
        # Yalnızca seçilen butonu aktif yap
        for nav_id, btn in self.nav_buttons.items():
            btn.setChecked(nav_id == tab_id)
            
        # Gösterilecek widget'in index'ini bul
        if tab_id in self.views:
            idx = self.stacked_widget.indexOf(self.views[tab_id])
            self.stacked_widget.setCurrentIndex(idx)
            # Asistan sekmesi açıldığında AI durumunu ve varlık listesini tazele
            if tab_id == "assistant":
                self.views["assistant"].refresh_state()

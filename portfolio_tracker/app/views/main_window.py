from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                 QPushButton, QStackedWidget, QLabel, QApplication)
from PySide6.QtCore import Qt, QSize, QTimer
import qtawesome as qta
import os
import sys

from app.config import COLORS


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Portföy Takip ve Analiz")
        self.setMinimumSize(1200, 800)
        self.current_theme = "dark"

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

        # Yenileme durum göstergesi (sidebar altı)
        self.status_label = QLabel("")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(self.status_label)

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

        from app.viewmodels.portfolio_viewmodel import PortfolioViewModel
        from app.viewmodels.transaction_viewmodel import TransactionViewModel
        from app.viewmodels.analytics_viewmodel import AnalyticsViewModel
        from app.viewmodels.settings_viewmodel import SettingsViewModel
        from app.viewmodels.alerts_viewmodel import AlertsViewModel

        self.portfolio_vm = PortfolioViewModel()
        self.transaction_vm = TransactionViewModel()
        self.analytics_vm = AnalyticsViewModel()
        self.settings_vm = SettingsViewModel()
        self.alerts_vm = AlertsViewModel()
        self._notifications_enabled = True

        self.settings_vm.settings_loaded.connect(self.apply_theme)
        self.settings_vm.settings_loaded.connect(self.on_settings_for_runtime)
        self.settings_vm.data_wiped.connect(lambda: self.portfolio_vm.load_data())
        self.alerts_vm.alert_triggered.connect(self._on_alert_triggered)

        self.views = {
            "dashboard": DashboardView(self.portfolio_vm),
            "portfolio": PortfolioView(self.portfolio_vm),
            "transactions": TransactionsView(self.transaction_vm),
            "analytics": AnalyticsView(self.analytics_vm, self.portfolio_vm),
            "alerts": AlertsView(self.alerts_vm, self.portfolio_vm),
            "settings": SettingsView(self.settings_vm)
        }

        for view_name, view_widget in self.views.items():
            self.stacked_widget.addWidget(view_widget)

        # Portföy verisi yenilendikçe analiz, işlem listesi ve uyarıları tazele
        self.portfolio_vm.kpi_updated.connect(self._refresh_analytics)
        self.portfolio_vm.kpi_updated.connect(self._check_alerts)
        self.portfolio_vm.data_loaded.connect(lambda _: self.transaction_vm.load_transactions())
        self.portfolio_vm.loading_started.connect(lambda: self.status_label.setText("⟳ Yenileniyor..."))
        self.portfolio_vm.loading_finished.connect(lambda: self.status_label.setText(""))

        # Otomatik yenileme zamanlayıcısı
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(lambda: self.portfolio_vm.load_data())

        # Varsayılan sekme
        self.switch_tab("dashboard")

        # İlk yüklemeler
        self.settings_vm.load_settings()
        self.portfolio_vm.load_data()

    def _detect_system_theme(self) -> str:
        """İşletim sistemi temasını algılar (Qt 6.5+); aksi halde dark döner."""
        try:
            scheme = QApplication.styleHints().colorScheme()
            from PySide6.QtCore import Qt as _Qt
            if scheme == _Qt.ColorScheme.Light:
                return "light"
            if scheme == _Qt.ColorScheme.Dark:
                return "dark"
        except Exception:
            pass
        return "dark"

    def apply_theme(self, settings_dict):
        theme = settings_dict.get("theme", "system")
        if theme == "system":
            theme = self._detect_system_theme()
        self.current_theme = theme

        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        style_path = os.path.join(base_dir, "app", "resources", "styles", f"{theme}.qss")

        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                QApplication.instance().setStyleSheet(f.read())

        # Grafik içeren view'lara tema rengini bildir
        for view in self.views.values():
            if hasattr(view, "apply_chart_theme"):
                view.apply_chart_theme(theme)

    def on_settings_for_runtime(self, settings_dict):
        """Maliyet metodu ve yenileme aralığı gibi çalışma-zamanı ayarlarını uygular."""
        # Maliyet metodu
        method = settings_dict.get("cost_method", "WAC")
        self.portfolio_vm.set_cost_method(method)

        # Bildirim tercihi
        self._notifications_enabled = str(settings_dict.get("notifications_enabled", "1")) in ("1", "True", "true")

        # Otomatik yenileme aralığı
        interval = settings_dict.get("refresh_interval_minutes", "15")
        if str(interval).isdigit():
            self.refresh_timer.start(int(interval) * 60 * 1000)
        else:
            self.refresh_timer.stop()

    def _refresh_analytics(self, kpi_data):
        items = kpi_data.get("portfolio_items", [])
        self.analytics_vm.load_analytics_data(items)

    def _check_alerts(self, kpi_data):
        """Güncel fiyatlardan bir fiyat haritası kurup uyarıları değerlendirir."""
        price_map = {}
        for item in kpi_data.get("portfolio_items", []):
            prev = item.get("prev_close") or 0.0
            cur = item.get("current_price") or 0.0
            pct = ((cur - prev) / prev * 100) if prev > 0 else 0.0
            price_map[item["id"]] = {"price": cur, "pct": pct}
        if price_map:
            self.alerts_vm.check_alerts(price_map, self._notifications_enabled)

    def _on_alert_triggered(self, code, message):
        self.status_label.setText(f"🔔 {code}")

    def switch_tab(self, tab_id: str):
        # Yalnızca seçilen butonu aktif yap
        for nav_id, btn in self.nav_buttons.items():
            btn.setChecked(nav_id == tab_id)

        # Gösterilecek widget'in index'ini bul
        if tab_id in self.views:
            idx = self.stacked_widget.indexOf(self.views[tab_id])
            self.stacked_widget.setCurrentIndex(idx)
            if tab_id == "analytics":
                self.analytics_vm.load_analytics_data(self.portfolio_vm.cached_portfolio_data)
            elif tab_id == "alerts" and hasattr(self.views["alerts"], "refresh"):
                self.views["alerts"].refresh()

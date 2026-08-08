import os
import sys

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


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
        sidebar_layout.addSpacing(12)

        portfolio_row = QHBoxLayout()
        self.portfolio_selector = QComboBox()
        self.portfolio_selector.setAccessibleName("Aktif portföy")
        self.portfolio_selector.setToolTip("Tek portföy veya konsolide görünüm seçin")
        self.add_portfolio_btn = QPushButton("+")
        self.add_portfolio_btn.setFixedWidth(34)
        self.add_portfolio_btn.setToolTip("Yeni portföy oluştur")
        self.add_portfolio_btn.setAccessibleName("Yeni portföy oluştur")
        portfolio_row.addWidget(self.portfolio_selector, stretch=1)
        portfolio_row.addWidget(self.add_portfolio_btn)
        sidebar_layout.addLayout(portfolio_row)
        sidebar_layout.addSpacing(18)

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

        # Manuel yenileme butonu — fiyatları/portföyü anında güncellemek için.
        self.manual_refresh_btn = QPushButton("Şimdi Yenile")
        self.manual_refresh_btn.setObjectName("manual_refresh_btn")
        self.manual_refresh_btn.setIcon(qta.icon("fa5s.sync-alt", color="#6B7280"))
        self.manual_refresh_btn.setIconSize(QSize(16, 16))
        self.manual_refresh_btn.setToolTip("Fiyatları ve portföyü şimdi güncelle")
        self.manual_refresh_btn.clicked.connect(
            lambda: self.portfolio_vm.load_data(force_refresh=True)
        )
        sidebar_layout.addWidget(self.manual_refresh_btn)

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

        from app.viewmodels.ai_viewmodel import AIViewModel
        from app.viewmodels.alerts_viewmodel import AlertsViewModel
        from app.viewmodels.analytics_viewmodel import AnalyticsViewModel
        from app.viewmodels.portfolio_viewmodel import PortfolioViewModel
        from app.viewmodels.settings_viewmodel import SettingsViewModel
        from app.viewmodels.transaction_viewmodel import TransactionViewModel
        from app.views.ai_assistant_view import AIAssistantView
        from app.views.alerts_view import AlertsView
        from app.views.analytics_view import AnalyticsView
        from app.views.dashboard_view import DashboardView
        from app.views.portfolio_view import PortfolioView
        from app.views.settings_view import SettingsView
        from app.views.transactions_view import TransactionsView

        self.portfolio_vm = PortfolioViewModel()
        self.transaction_vm = TransactionViewModel()
        self.analytics_vm = AnalyticsViewModel()
        self.settings_vm = SettingsViewModel()
        self.ai_vm = AIViewModel()
        self.alerts_vm = AlertsViewModel()
        self._notifications_enabled = True

        self.settings_vm.settings_loaded.connect(self.apply_theme)
        self.settings_vm.settings_loaded.connect(self.on_settings_for_runtime)
        self.settings_vm.data_wiped.connect(lambda: self.portfolio_vm.load_data())
        self.settings_vm.data_changed.connect(lambda: self.portfolio_vm.load_data())
        self.alerts_vm.alert_triggered.connect(self._on_alert_triggered)
        self.portfolio_vm.portfolios_loaded.connect(self._on_portfolios_loaded)
        self.portfolio_vm.portfolio_selection_changed.connect(self.transaction_vm.set_portfolio)
        self.portfolio_vm.portfolio_selection_changed.connect(self.ai_vm.set_portfolio)
        self.portfolio_selector.currentIndexChanged.connect(self._on_portfolio_selected)
        self.add_portfolio_btn.clicked.connect(self._create_portfolio)

        # Yapay zeka asistanını güncel portföy verisiyle besle
        self.portfolio_vm.data_loaded.connect(self.ai_vm.update_portfolio_data)
        self.portfolio_vm.kpi_updated.connect(self.ai_vm.update_kpi_data)
        # Görüntüden içe aktarma sonrası portföyü yenile
        self.ai_vm.holdings_imported.connect(lambda _msg: self.portfolio_vm.load_data())

        # Otomatik yenileme zamanlayıcısı (view'lar kurulmadan önce hazır olmalı;
        # ayar sinyalleri erken tetiklenirse hata vermesin)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(lambda: self.portfolio_vm.load_data())

        # view sözlüğü erken referanslara karşı önce boş başlatılır
        self.views = {}
        self.views = {
            "dashboard": DashboardView(self.portfolio_vm),
            "portfolio": PortfolioView(self.portfolio_vm),
            "transactions": TransactionsView(self.transaction_vm),
            "analytics": AnalyticsView(self.analytics_vm, self.portfolio_vm),
            "assistant": AIAssistantView(self.ai_vm),
            "alerts": AlertsView(self.alerts_vm, self.portfolio_vm),
            "settings": SettingsView(self.settings_vm, self.portfolio_vm)
        }

        for view_name, view_widget in self.views.items():
            self.stacked_widget.addWidget(view_widget)

        # Portföy verisi yenilendikçe analiz, işlem listesi ve uyarıları tazele
        self.portfolio_vm.kpi_updated.connect(self._refresh_analytics)
        self.portfolio_vm.kpi_updated.connect(self._check_alerts)
        self.portfolio_vm.data_loaded.connect(lambda _: self.transaction_vm.load_transactions())
        # İşlemler sekmesinden yapılan ekleme/güncelleme/silme portföyü de etkiler
        self.transaction_vm.action_success.connect(lambda _msg: self.portfolio_vm.load_data())
        self.portfolio_vm.loading_started.connect(lambda: self.status_label.setText("⟳ Yenileniyor..."))
        self.portfolio_vm.loading_finished.connect(lambda: self.status_label.setText(""))

        # Varsayılan sekme
        self.switch_tab("dashboard")

        # İlk yüklemeler
        self.settings_vm.load_settings()
        self.portfolio_vm.load_portfolios()
        self.portfolio_vm.load_data()

    def _on_portfolios_loaded(self, portfolios):
        selected = self.portfolio_vm.selected_portfolio_id
        self.portfolio_selector.blockSignals(True)
        self.portfolio_selector.clear()
        self.portfolio_selector.addItem("Tüm Portföyler", None)
        for portfolio in portfolios:
            self.portfolio_selector.addItem(portfolio["name"], portfolio["id"])
        index = self.portfolio_selector.findData(selected)
        self.portfolio_selector.setCurrentIndex(index if index >= 0 else 0)
        self.portfolio_selector.blockSignals(False)

    def _on_portfolio_selected(self, _index):
        self.portfolio_vm.set_portfolio(self.portfolio_selector.currentData())

    def _create_portfolio(self):
        name, accepted = QInputDialog.getText(self, "Yeni Portföy", "Portföy adı:")
        if accepted and name.strip():
            self.portfolio_vm.create_portfolio(name)

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
        for view in getattr(self, "views", {}).values():
            if hasattr(view, "apply_chart_theme"):
                view.apply_chart_theme(theme)

    def on_settings_for_runtime(self, settings_dict):
        """Maliyet metodu, para birimi ve yenileme aralığı gibi çalışma-zamanı
        ayarlarını uygular."""
        from app.utils.display import display

        # Görüntüleme para birimi (TRY/USD)
        prev_mode = display.mode
        display.set_mode(settings_dict.get("default_currency", "TRY"))
        if display.mode != prev_mode:
            self.portfolio_vm.refresh_display()

        # Maliyet metodu
        method = settings_dict.get("cost_method", "WAC")
        self.portfolio_vm.set_cost_method(method)
        self.portfolio_vm.configure_refresh_policy(
            settings_dict.get("market_calendar_overrides", "")
        )

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
            elif tab_id == "assistant":
                # Asistan sekmesi açıldığında AI durumunu ve varlık listesini tazele
                self.views["assistant"].refresh_state()

    def closeEvent(self, event):
        """Zamanlayıcıyı ve bütün ViewModel işçilerini kontrollü biçimde kapatır."""
        self.refresh_timer.stop()
        for view_model in (
            self.portfolio_vm,
            self.transaction_vm,
            self.analytics_vm,
            self.settings_vm,
            self.ai_vm,
            self.alerts_vm,
        ):
            view_model.shutdown()
        super().closeEvent(event)

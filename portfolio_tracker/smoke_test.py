"""Başsız (offscreen) GUI smoke testi.

Ağ veya kullanıcı verisine dokunmadan tüm view'ları ve diyalogları oluşturur,
örnek verilerle besler. Import/sinyal/QSS/construction hatalarını yakalamak için.
Kalıcı bir test değildir; yalnızca geliştirme doğrulaması içindir.
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QMessageBox

# --- Ağ ve modal diyalogları etkisizleştir ---
from app.viewmodels.portfolio_viewmodel import PortfolioViewModel

PortfolioViewModel.load_data = lambda self, *a, **k: None  # type: ignore

QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.Ok)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.No)

# Benchmark ağ çağrısını örnek veriyle değiştir
import datetime as _dt

from app.services.benchmark_service import BenchmarkService

BenchmarkService.fetch_series = staticmethod(lambda *a, **k: {
    "BIST 100": [(_dt.date(2024, 1, 1), 9000.0), (_dt.date(2024, 2, 1), 9500.0)],
    "USD/TRY": [(_dt.date(2024, 1, 1), 32.0), (_dt.date(2024, 2, 1), 33.0)],
    "Gram Altın": [(_dt.date(2024, 1, 1), 2000.0), (_dt.date(2024, 2, 1), 2100.0)],
})

import datetime

from app.database.engine import init_db
from app.views.alerts_view import AddAlertDialog
from app.views.main_window import MainWindow
from app.views.portfolio_view import AssetDialog
from app.views.settings_view import ExportColumnsDialog
from app.views.transactions_view import AddTransactionDialog


def sample_items():
    return [
        {
            "id": 1, "code": "THYAO", "name": "Türk Hava Yolları", "type": "BIST",
            "quantity": 100, "avg_cost": 250.0, "current_price": 300.0, "prev_close": 290.0,
            "total_cost": 25000.0, "current_value": 30000.0, "daily_change": 1000.0,
            "realized_pnl": 500.0, "unrealized_pnl": 5000.0, "pnl": 5500.0,
            "pnl_pct": 22.0, "portfolio_pct": 60.0,
        },
        {
            "id": 2, "code": "AFT", "name": "Ak Portföy Fon", "type": "TEFAS",
            "quantity": 1000, "avg_cost": 20.0, "current_price": 18.0, "prev_close": 18.5,
            "total_cost": 20000.0, "current_value": 18000.0, "daily_change": -500.0,
            "realized_pnl": 0.0, "unrealized_pnl": -2000.0, "pnl": -2000.0,
            "pnl_pct": -10.0, "portfolio_pct": 40.0,
        },
    ]


def sample_kpi():
    items = sample_items()
    return {
        "total_value_try": 48000.0, "total_value_usd": 1500.0, "usd_try": 32.0,
        "total_cost_try": 45000.0, "realized_pnl": 500.0, "unrealized_pnl": 3000.0,
        "total_pnl": 3500.0, "pnl_pct": 7.78, "daily_change_try": 500.0,
        "daily_change_pct": 1.05,
        "best": {"code": "THYAO", "pnl_pct": 22.0},
        "worst": {"code": "AFT", "pnl_pct": -10.0},
        "failed_codes": [], "portfolio_items": items,
        "history": [
            {"date": datetime.date(2024, 1, 1), "total_value_try": 40000.0,
             "total_value_usd": 1300.0, "total_cost_try": 42000.0, "unrealized_pnl_try": -2000.0},
            {"date": datetime.date(2024, 2, 1), "total_value_try": 48000.0,
             "total_value_usd": 1500.0, "total_cost_try": 45000.0, "unrealized_pnl_try": 3000.0},
        ],
    }


def main():
    init_db()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = MainWindow()
    win.show()

    # Tüm sekmeleri gez
    for tab in ("dashboard", "portfolio", "transactions", "analytics",
                "assistant", "alerts", "settings"):
        win.switch_tab(tab)
        app.processEvents()

    # View güncelleme yollarını örnek veriyle çalıştır
    items = sample_items()
    kpi = sample_kpi()
    win.views["dashboard"].update_kpi_cards(kpi)
    win.views["portfolio"].on_data_loaded(items)
    win.views["transactions"].on_data_loaded([
        {"id": 1, "asset_id": 1, "date": "2024-01-15", "date_obj": datetime.date(2024, 1, 15),
         "asset_code": "THYAO", "type": "BUY", "quantity": 100, "unit_price": 250.0,
         "commission": 5.0, "tax": 0.0, "total": 25005.0, "note": "test"},
    ])
    win.views["analytics"].on_analytics_loaded({
        "xirr": 0.18, "sharpe": 1.2, "volatility": 0.25, "max_drawdown": -0.15,
        "allocation_type": {"BIST": 30000.0, "TEFAS": 18000.0},
        "allocation_asset": [{"name": "THYAO", "value": 30000.0}, {"name": "AFT", "value": 18000.0}],
        "attribution": [{"code": "THYAO", "pnl": 5500.0}, {"code": "AFT", "pnl": -2000.0}],
        "history": kpi["history"],
    })
    # Analiz iç sekmelerini gez (Takvim dahil)
    for i in range(win.views["analytics"].tabs.count()):
        win.views["analytics"].tabs.setCurrentIndex(i)
        app.processEvents()
    win.views["alerts"].on_alerts_loaded([
        {"id": 1, "asset_id": 1, "asset_code": "THYAO", "type": None,
         "type_label": "Fiyat şunun üstüne çıkarsa", "threshold": 320.0,
         "is_active": True, "triggered_at": None},
    ])
    app.processEvents()

    # Benchmark worker'ının tamamlanmasını bekle ve aralık butonlarını test et
    av = win.views["analytics"]
    benchmark_worker = win.analytics_vm._benchmark_worker
    if benchmark_worker is not None:
        benchmark_worker.wait(3000)
    app.processEvents()
    for rng in ("1H", "1A", "3A", "6A", "YBB", "1Y", "Tümü"):
        av._on_range_changed(rng)
        app.processEvents()
    # Benchmark serisi aç/kapa
    for name, cb in av.series_checks.items():
        cb.setChecked(False)
        app.processEvents()
        cb.setChecked(True)
    app.processEvents()

    # Temaları test et
    for theme in ("dark", "light", "system"):
        win.apply_theme({"theme": theme})
        app.processEvents()

    # Diyaloglar oluşturulabiliyor mu
    AssetDialog(win)
    AssetDialog(win, asset={"code": "THYAO", "name": "x", "type": "BIST"})
    AddTransactionDialog([{"id": 1, "code": "THYAO"}], win)
    AddTransactionDialog([{"id": 1, "code": "THYAO"}], win, tx={
        "asset_id": 1, "type": "SELL", "date_obj": datetime.date(2024, 1, 1),
        "quantity": 10, "unit_price": 5, "commission": 1, "tax": 0, "note": "n"})
    AddAlertDialog([{"id": 1, "code": "THYAO"}], win)
    ExportColumnsDialog(["Varlık", "Miktar", "Değer"], win)
    app.processEvents()

    # USD görünüm modunu test et (çevirip yeniden render)
    from app.utils.display import display
    display.set_mode("USD")
    display.set_rate(32.0)
    win.views["dashboard"].update_kpi_cards(kpi)
    win.views["portfolio"].on_data_loaded(items)
    win.views["transactions"].on_data_loaded([
        {"id": 1, "asset_id": 1, "date": "2024-01-15", "date_obj": datetime.date(2024, 1, 15),
         "asset_code": "THYAO", "type": "DIVIDEND", "quantity": 100, "unit_price": 2.0,
         "commission": 0.0, "tax": 15.0, "total": 185.0, "note": "temettü"},
    ])
    app.processEvents()
    display.set_mode("TRY")

    win.close()
    app.processEvents()
    print("SMOKE_OK")


if __name__ == "__main__":
    main()

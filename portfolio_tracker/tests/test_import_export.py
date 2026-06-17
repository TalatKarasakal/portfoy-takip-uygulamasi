import pytest
import os
import pandas as pd
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (tüm modelleri registry'ye kaydeder)
from app.database.base import Base
from app.services.import_export_service import ImportExportService
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()

@pytest.fixture
def mock_session():
    session = MagicMock()
    # Find alanları için None dön (yok gibi davransın)
    session.query().filter_by().first.return_value = None
    return session

@pytest.fixture
def sample_excel_files(tmp_path):
    # Senaryo 3: Tam İşlem
    full_tx_path = tmp_path / "full_tx.xlsx"
    pd.DataFrame({
        "Tarih": ["2023-01-01"],
        "Kod": ["THYAO"],
        "Tür": ["AL"],
        "Adet": [100],
        "Birim Fiyat": [50.0],
        "Komisyon": [1.5]
    }).to_excel(full_tx_path, index=False)

    # Senaryo 2: Adet + Maliyet
    qty_cost_path = tmp_path / "qty_cost.xlsx"
    pd.DataFrame({
        "Kod": ["AFT"],
        "Adet": [500],
        "Ortalama Maliyet": [10.5]
    }).to_excel(qty_cost_path, index=False)

    # Senaryo 1: Yüzde (Şimdilik Exception fırlatması beklenen)
    pct_path = tmp_path / "pct.xlsx"
    pd.DataFrame({
        "Kod": ["THYAO"],
        "Yüzde": [50.0]
    }).to_excel(pct_path, index=False)
    
    return full_tx_path, qty_cost_path, pct_path

def test_import_full_transaction(mock_session, sample_excel_files):
    full_tx_path, _, _ = sample_excel_files
    
    result = ImportExportService.import_excel(mock_session, str(full_tx_path))
    assert result == True
    assert mock_session.add.called or mock_session.add_all.called
    assert mock_session.commit.called

def test_import_qty_cost(mock_session, sample_excel_files):
    _, qty_cost_path, _ = sample_excel_files
    
    result = ImportExportService.import_excel(mock_session, str(qty_cost_path))
    assert result == True
    assert mock_session.add.called or mock_session.add_all.called
    assert mock_session.commit.called

def test_import_percent_raises(mock_session, sample_excel_files):
    _, _, pct_path = sample_excel_files

    # Yüzdelik dosya generic import_excel ile işlenmez (ayrı akış); False döner.
    result = ImportExportService.import_excel(mock_session, str(pct_path))
    assert result == False


def test_detect_percentage(sample_excel_files):
    full_tx_path, qty_cost_path, pct_path = sample_excel_files
    assert ImportExportService.detect_percentage(str(pct_path)) is True
    assert ImportExportService.detect_percentage(str(full_tx_path)) is False
    assert ImportExportService.detect_percentage(str(qty_cost_path)) is False


def test_import_percentage_computes_quantities(db_session, tmp_path, monkeypatch):
    # Fiyat servislerini sabit fiyat dönecek şekilde patch'le (ağ yok)
    from app.services.bist_service import BistService
    from app.services.tefas_service import TefasService
    monkeypatch.setattr(BistService, "fetch_current_price", lambda self, code, force=False: 10.0)
    monkeypatch.setattr(TefasService, "fetch_current_price", lambda self, code, force=False: 10.0)

    pct_file = tmp_path / "pct.xlsx"
    pd.DataFrame({"Kod": ["THYAO", "AFT"], "Yüzde": [60.0, 40.0]}).to_excel(pct_file, index=False)

    ok = ImportExportService.import_percentage(db_session, str(pct_file), total_value=100000.0)
    assert ok is True

    txs = {t.asset.code: t for t in db_session.query(Transaction).all()}
    assert set(txs.keys()) == {"THYAO", "AFT"}
    # adet = (toplam * yüzde/100) / fiyat
    assert abs(float(txs["THYAO"].quantity) - 6000.0) < 1e-6   # 60000/10
    assert abs(float(txs["AFT"].quantity) - 4000.0) < 1e-6     # 40000/10
    # Tür sezgisi: 5 harf BIST, 3 harf TEFAS
    assert txs["THYAO"].asset.asset_type == AssetType.BIST
    assert txs["AFT"].asset.asset_type == AssetType.TEFAS


def test_export_with_portfolio_items(db_session, tmp_path):
    items = [{
        "code": "THYAO", "name": "Türk Hava Yolları", "type": "BIST",
        "quantity": 100, "avg_cost": 250.0, "current_price": 300.0,
        "total_cost": 25000.0, "current_value": 30000.0,
        "realized_pnl": 0.0, "unrealized_pnl": 5000.0, "portfolio_pct": 100.0,
    }]
    out = tmp_path / "export.xlsx"
    ImportExportService.export_excel(
        db_session, str(out), portfolio_items=items, columns=["Kod", "Güncel Değer"]
    )
    df = pd.read_excel(str(out), sheet_name="Portföy")
    assert list(df.columns) == ["Kod", "Güncel Değer"]
    assert df.iloc[0]["Kod"] == "THYAO"
    assert abs(float(df.iloc[0]["Güncel Değer"]) - 30000.0) < 1e-6

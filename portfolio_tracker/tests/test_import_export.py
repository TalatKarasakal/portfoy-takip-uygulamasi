import pytest
import os
import pandas as pd
from unittest.mock import MagicMock
from app.services.import_export_service import ImportExportService
from app.models.asset import Asset, AssetType

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
    assert mock_session.add.called
    assert mock_session.commit.called

def test_import_qty_cost(mock_session, sample_excel_files):
    _, qty_cost_path, _ = sample_excel_files
    
    result = ImportExportService.import_excel(mock_session, str(qty_cost_path))
    assert result == True
    assert mock_session.add.called
    assert mock_session.commit.called

def test_import_percent_success(mock_session, sample_excel_files):
    _, _, pct_path = sample_excel_files
    
    result = ImportExportService.import_excel(mock_session, str(pct_path))
    assert result == True
    assert mock_session.add.called
    assert mock_session.commit.called

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from app.services.tefas_service import TefasService
from app.utils.cache import price_cache

@pytest.fixture
def override_cache():
    price_cache.clear()

@patch('app.services.tefas_service.Crawler')
def test_fetch_current_price_success(MockCrawler, override_cache):
    # Mock return value for pandas dataframe
    mock_df = pd.DataFrame([{
        "date": pd.Timestamp('2023-10-10'),
        "code": "AFT",
        "price": 10.5
    }])
    instance = MockCrawler.return_value
    instance.fetch.return_value = mock_df

    service = TefasService()
    # Cache disabled via bypass
    price = service.fetch_current_price("AFT", force_refresh=True)
    
    assert price == 10.5
    assert instance.fetch.called

@patch('app.services.tefas_service.Crawler')
def test_fetch_fund_name(MockCrawler, override_cache):
    mock_df = pd.DataFrame([
        {"date": pd.Timestamp('2024-10-09'), "code": "AFT", "title": "AK PORTFÖY X FONU"},
        {"date": pd.Timestamp('2024-10-10'), "code": "AFT", "title": "AK PORTFÖY X FONU"},
    ])
    instance = MockCrawler.return_value
    instance.fetch.return_value = mock_df

    with patch('time.sleep', return_value=None):
        service = TefasService()
        name = service.fetch_fund_name("AFT")

    assert name == "AK PORTFÖY X FONU"


@patch('app.services.tefas_service.Crawler')
def test_fetch_fund_name_handles_failure(MockCrawler, override_cache):
    instance = MockCrawler.return_value
    instance.fetch.side_effect = Exception("network")
    with patch('time.sleep', return_value=None):
        service = TefasService()
        assert service.fetch_fund_name("ZZZ") is None


@patch('app.services.tefas_service.Crawler')
def test_fetch_current_price_retry_failure(MockCrawler, override_cache):
    instance = MockCrawler.return_value
    # Simüle edilmiş exception (örn. ağ hatası)
    instance.fetch.side_effect = Exception("Network Error")

    service = TefasService()
    service.max_retries = 2
    
    with patch('time.sleep', return_value=None):
        price = service.fetch_current_price("AFT", force_refresh=True)

    assert price is None
    assert instance.fetch.call_count == 2

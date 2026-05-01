import pytest
from unittest.mock import MagicMock, patch
from app.services.bist_service import BistService
from app.utils.cache import price_cache

@pytest.fixture
def override_cache():
    price_cache.clear()

@patch('app.services.bist_service.yf.Ticker')
def test_fetch_current_price_success(MockTicker, override_cache):
    # Mock return value for yfinance Ticker history
    mock_iloc = MagicMock()
    mock_iloc.__getitem__.return_value = 15.5
    mock_close = MagicMock()
    mock_close.iloc = mock_iloc
    mock_history = MagicMock()
    mock_history.empty = False
    mock_history.__getitem__.return_value = mock_close

    instance = MockTicker.return_value
    instance.history.return_value = mock_history

    service = BistService()
    price = service.fetch_current_price("THYAO", force_refresh=True)

    assert price == 15.5
    MockTicker.assert_called_with("THYAO.IS")
    instance.history.assert_called_with(period="1d")

    # Check cache is set
    cached_price = price_cache.get("BIST_THYAO.IS")
    assert cached_price == 15.5

@patch('app.services.bist_service.yf.Ticker')
def test_fetch_current_price_suffix(MockTicker, override_cache):
    # Mock return value for yfinance Ticker history
    mock_iloc = MagicMock()
    mock_iloc.__getitem__.return_value = 10.0
    mock_close = MagicMock()
    mock_close.iloc = mock_iloc
    mock_history = MagicMock()
    mock_history.empty = False
    mock_history.__getitem__.return_value = mock_close

    instance = MockTicker.return_value
    instance.history.return_value = mock_history

    service = BistService()
    price = service.fetch_current_price("GARAN.IS", force_refresh=True)

    assert price == 10.0
    # ensure it didn't add duplicate suffix
    MockTicker.assert_called_with("GARAN.IS")

def test_fetch_current_price_from_cache(override_cache):
    service = BistService()
    # explicitly set cache
    price_cache.set("BIST_AKBNK.IS", 20.5)

    # no mock ticker, because it shouldn't be called
    with patch('app.services.bist_service.yf.Ticker') as MockTicker:
        price = service.fetch_current_price("AKBNK", force_refresh=False)
        assert price == 20.5
        assert not MockTicker.called

@patch('app.services.bist_service.yf.Ticker')
def test_fetch_current_price_empty_history(MockTicker, override_cache):
    mock_history = MagicMock()
    mock_history.empty = True

    instance = MockTicker.return_value
    instance.history.return_value = mock_history

    service = BistService()
    price = service.fetch_current_price("INVALID", force_refresh=True)

    assert price is None
    assert MockTicker.called

@patch('app.services.bist_service.yf.Ticker')
def test_fetch_current_price_exception(MockTicker, override_cache):
    instance = MockTicker.return_value
    instance.history.side_effect = Exception("API error")

    service = BistService()
    price = service.fetch_current_price("ERROR_SYM", force_refresh=True)

    assert price is None
    assert MockTicker.called

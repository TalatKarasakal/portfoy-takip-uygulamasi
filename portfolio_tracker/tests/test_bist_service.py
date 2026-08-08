from unittest.mock import MagicMock, patch

import pytest

from app.services.bist_service import BistService
from app.utils.cache import price_cache


@pytest.fixture
def override_cache():
    price_cache.clear()
    yield
    price_cache.clear()

@patch('app.services.bist_service.yf.Ticker')
@patch('app.services.bist_service.IsYatirimService.fetch_quote')
def test_fetch_current_price_success(mock_fetch_quote, MockTicker, override_cache):
    # Mock return value for yfinance Ticker history
    mock_history = MagicMock()
    mock_history.empty = False
    mock_history.__getitem__.return_value.tolist.return_value = [15.0, 15.5]

    instance = MockTicker.return_value
    instance.history.return_value = mock_history

    service = BistService()
    price = service.fetch_current_price("THYAO", force_refresh=True)

    assert price == 15.5
    MockTicker.assert_called_with("THYAO.IS")
    instance.history.assert_called_with(period="5d")
    mock_fetch_quote.assert_not_called()

    # Check cache is set with BIST_QUOTE_ suffix and quote dict
    cached_quote = price_cache.get("BIST_QUOTE_THYAO.IS")
    assert cached_quote.price == 15.5
    assert cached_quote.prev_close == 15.0

@patch('app.services.bist_service.yf.Ticker')
@patch('app.services.bist_service.IsYatirimService.fetch_quote')
def test_fetch_current_price_suffix(mock_fetch_quote, MockTicker, override_cache):
    # Mock return value for yfinance Ticker history
    mock_history = MagicMock()
    mock_history.empty = False
    mock_history.__getitem__.return_value.tolist.return_value = [10.0]

    instance = MockTicker.return_value
    instance.history.return_value = mock_history

    service = BistService()
    price = service.fetch_current_price("GARAN.IS", force_refresh=True)

    assert price == 10.0
    MockTicker.assert_called_with("GARAN.IS")
    mock_fetch_quote.assert_not_called()

def test_fetch_current_price_from_cache(override_cache):
    service = BistService()
    # explicitly set cache with BIST_QUOTE_ key
    price_cache.set("BIST_QUOTE_AKBNK.IS", {"price": 20.5, "prev_close": 20.0})

    # no mock ticker, because it shouldn't be called
    with patch('app.services.bist_service.yf.Ticker') as MockTicker:
        price = service.fetch_current_price("AKBNK", force_refresh=False)
        assert price == 20.5
        assert not MockTicker.called

@patch('app.services.bist_service.yf.Ticker')
@patch('app.services.bist_service.IsYatirimService.fetch_quote')
def test_fetch_current_price_empty_history(mock_fetch_quote, MockTicker, override_cache):
    mock_history = MagicMock()
    mock_history.empty = True

    instance = MockTicker.return_value
    instance.history.return_value = mock_history
    mock_fetch_quote.return_value = {"price": None, "prev_close": None}

    service = BistService()
    price = service.fetch_current_price("INVALID", force_refresh=True)

    assert price is None
    assert MockTicker.called
    mock_fetch_quote.assert_called_once_with("INVALID.IS")

@patch('app.services.bist_service.yf.Ticker')
@patch('app.services.bist_service.IsYatirimService.fetch_quote')
def test_fetch_current_price_exception(mock_fetch_quote, MockTicker, override_cache):
    instance = MockTicker.return_value
    instance.history.side_effect = Exception("API error")
    mock_fetch_quote.return_value = {"price": None, "prev_close": None}

    service = BistService()
    price = service.fetch_current_price("ERROR_SYM", force_refresh=True)

    assert price is None
    assert MockTicker.called
    mock_fetch_quote.assert_called_once_with("ERROR_SYM.IS")

import pytest
import sys
from unittest.mock import MagicMock, patch

# Mock dependencies to avoid errors in restricted environment
if 'yfinance' not in sys.modules:
    sys.modules['yfinance'] = MagicMock()

from app.services.bist_service import BistService

@pytest.fixture
def bist_service():
    # Clear cache before each test
    from app.utils.cache import price_cache
    price_cache.clear()
    return BistService()

@patch('app.services.bist_service.yf.Ticker')
@patch.object(BistService, '_scrape_isyatirim_price')
def test_fetch_current_price_yfinance_success(mock_scrape, mock_ticker, bist_service):
    # Mock yfinance response
    mock_history = MagicMock()
    mock_history.empty = False
    mock_history.__getitem__.return_value.iloc = [-1, 150.5]  # mock history['Close'].iloc[-1]
    mock_ticker.return_value.history.return_value = mock_history

    price = bist_service.fetch_current_price("THYAO")

    assert price == 150.5
    mock_scrape.assert_not_called()

@patch('app.services.bist_service.yf.Ticker')
@patch.object(BistService, '_scrape_isyatirim_price')
def test_fetch_current_price_yfinance_empty_fallback(mock_scrape, mock_ticker, bist_service):
    # Mock yfinance returning empty history
    mock_history = MagicMock()
    mock_history.empty = True
    mock_ticker.return_value.history.return_value = mock_history

    # Mock fallback response
    mock_scrape.return_value = 160.0

    price = bist_service.fetch_current_price("THYAO")

    assert price == 160.0
    mock_scrape.assert_called_once_with("THYAO.IS")

@patch('app.services.bist_service.yf.Ticker')
@patch.object(BistService, '_scrape_isyatirim_price')
def test_fetch_current_price_yfinance_exception_fallback(mock_scrape, mock_ticker, bist_service):
    # Mock yfinance throwing an exception
    mock_ticker.side_effect = Exception("API rate limit exceeded")

    # Mock fallback response
    mock_scrape.return_value = 170.5

    price = bist_service.fetch_current_price("THYAO")

    assert price == 170.5
    mock_scrape.assert_called_once_with("THYAO.IS")

@patch('app.services.bist_service.requests.get')
def test_scrape_isyatirim_price_success(mock_get, bist_service):
    # Mock successful HTML response
    mock_response = MagicMock()
    mock_response.text = '''
        <a href="/tr-tr/analiz/hisse/Sayfalar/sirket-karti.aspx?hisse=THYAO">
            THYAO
        </a>
        </td>
        <td class="text-right">308,25</td>
    '''
    mock_get.return_value = mock_response

    price = bist_service._scrape_isyatirim_price("THYAO")
    assert price == 308.25

@patch('app.services.bist_service.requests.get')
def test_scrape_isyatirim_price_format_with_thousands(mock_get, bist_service):
    # Mock HTML response with thousands separator
    mock_response = MagicMock()
    mock_response.text = '''
        <a href="/tr-tr/analiz/hisse/Sayfalar/sirket-karti.aspx?hisse=GARAN">
            GARAN
        </a>
        </td>
        <td class="text-right">1.234,56</td>
    '''
    mock_get.return_value = mock_response

    price = bist_service._scrape_isyatirim_price("GARAN.IS")
    assert price == 1234.56

@patch('app.services.bist_service.requests.get')
def test_scrape_isyatirim_price_failure(mock_get, bist_service):
    # Mock exception during request
    mock_get.side_effect = Exception("Connection error")

    price = bist_service._scrape_isyatirim_price("THYAO")
    assert price is None

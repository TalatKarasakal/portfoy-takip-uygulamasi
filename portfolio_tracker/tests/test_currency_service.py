from unittest.mock import MagicMock, patch

import pytest

from app.services.currency_service import CurrencyService
from app.utils.cache import price_cache


@pytest.fixture
def override_cache():
    price_cache.clear()
    yield
    price_cache.clear()

def test_fetch_usd_try_cached(override_cache):
    price_cache.set("CURRENCY_USD_TRY", 32.50)
    service = CurrencyService()

    # Should use cached value
    result = service.fetch_usd_try(force_refresh=False)
    assert result == 32.50

@patch('httpx.Client')
def test_fetch_usd_try_success(MockClient, override_cache):
    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <Tarih_Date Tarih="01.05.2024" Date="05/01/2024"  Bulten_No="2024/1">
        <Currency CrossOrder="0" Kod="USD" CurrencyCode="USD">
            <Unit>1</Unit>
            <Isim>ABD DOLARI</Isim>
            <CurrencyName>US DOLLAR</CurrencyName>
            <ForexBuying>32.3000</ForexBuying>
            <ForexSelling>32.5500</ForexSelling>
            <BanknoteBuying>32.2700</BanknoteBuying>
            <BanknoteSelling>32.6500</BanknoteSelling>
            <CrossRateUSD/>
            <CrossRateOther/>
        </Currency>
    </Tarih_Date>
    """

    mock_instance = MockClient.return_value.__enter__.return_value
    mock_response = MagicMock()
    mock_response.text = mock_xml
    mock_response.raise_for_status = MagicMock()
    mock_instance.get.return_value = mock_response

    service = CurrencyService()
    result = service.fetch_usd_try(force_refresh=True)

    assert result == 32.55
    assert price_cache.get("CURRENCY_USD_TRY") == 32.55
    mock_instance.get.assert_called_once_with(service.TCMB_URL)

@patch('httpx.Client')
def test_fetch_usd_try_missing_usd_node(MockClient, override_cache):
    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <Tarih_Date Tarih="01.05.2024" Date="05/01/2024"  Bulten_No="2024/1">
        <Currency CrossOrder="1" Kod="EUR" CurrencyCode="EUR">
            <Unit>1</Unit>
            <Isim>EURO</Isim>
            <CurrencyName>EURO</CurrencyName>
            <ForexBuying>34.5000</ForexBuying>
            <ForexSelling>34.6000</ForexSelling>
        </Currency>
    </Tarih_Date>
    """

    mock_instance = MockClient.return_value.__enter__.return_value
    mock_response = MagicMock()
    mock_response.text = mock_xml
    mock_instance.get.return_value = mock_response

    service = CurrencyService()
    result = service.fetch_usd_try(force_refresh=True)

    assert result is None
    assert price_cache.get("CURRENCY_USD_TRY") is None

@patch('httpx.Client')
def test_fetch_usd_try_missing_selling_node(MockClient, override_cache):
    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <Tarih_Date Tarih="01.05.2024" Date="05/01/2024"  Bulten_No="2024/1">
        <Currency CrossOrder="0" Kod="USD" CurrencyCode="USD">
            <Unit>1</Unit>
            <Isim>ABD DOLARI</Isim>
            <CurrencyName>US DOLLAR</CurrencyName>
            <ForexBuying>32.3000</ForexBuying>
        </Currency>
    </Tarih_Date>
    """

    mock_instance = MockClient.return_value.__enter__.return_value
    mock_response = MagicMock()
    mock_response.text = mock_xml
    mock_instance.get.return_value = mock_response

    service = CurrencyService()
    result = service.fetch_usd_try(force_refresh=True)

    assert result is None
    assert price_cache.get("CURRENCY_USD_TRY") is None

@patch('httpx.Client')
def test_fetch_usd_try_http_error(MockClient, override_cache):
    mock_instance = MockClient.return_value.__enter__.return_value
    mock_instance.get.side_effect = Exception("Network timeout")

    service = CurrencyService()
    result = service.fetch_usd_try(force_refresh=True)

    assert result is None
    assert price_cache.get("CURRENCY_USD_TRY") is None

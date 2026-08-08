import logging
import sys

import pytest

from app.services.backup_service import BackupResult
from app.services.secret_service import SecretService, SecretStoreError
from app.utils.app_settings import DEFAULT_SETTINGS
from app.utils.logger import SensitiveDataFilter, redact_sensitive
from app.viewmodels import ai_viewmodel, settings_viewmodel
from app.viewmodels.ai_viewmodel import AIViewModel
from app.viewmodels.settings_viewmodel import SettingsViewModel


class _Backend:
    priority = 1


class _FakeKeyring:
    def __init__(self):
        self.values = {}

    @staticmethod
    def get_keyring():
        return _Backend()

    def get_password(self, service, username):
        return self.values.get((service, username))

    def set_password(self, service, username, password):
        self.values[(service, username)] = password

    def delete_password(self, service, username):
        self.values.pop((service, username), None)


def test_secret_service_round_trip_uses_keyring(monkeypatch):
    fake = _FakeKeyring()
    monkeypatch.setitem(sys.modules, "keyring", fake)

    SecretService.set_gemini_api_key("secret-value")

    assert SecretService.get_gemini_api_key() == "secret-value"
    assert "ai_gemini_api_key" not in DEFAULT_SETTINGS


def test_secret_service_refuses_insecure_backend(monkeypatch):
    class InsecureKeyring(_FakeKeyring):
        @staticmethod
        def get_keyring():
            backend = _Backend()
            backend.priority = 0
            return backend

    monkeypatch.setitem(sys.modules, "keyring", InsecureKeyring())
    with pytest.raises(SecretStoreError, match="Güvenli"):
        SecretService.get_gemini_api_key()


def test_log_redaction_covers_headers_urls_and_registered_secret():
    raw = (
        "x-goog-api-key: header-secret "
        "https://example.test/path?key=query-secret "
        "Authorization: Bearer bearer-secret"
    )
    redacted = redact_sensitive(raw)
    assert "header-secret" not in redacted
    assert "query-secret" not in redacted
    assert "bearer-secret" not in redacted

    record = logging.LogRecord("test", logging.ERROR, __file__, 1, raw, (), None)
    assert SensitiveDataFilter().filter(record)
    assert "secret" not in record.getMessage().replace("[REDACTED]", "")


def test_cloud_provider_is_blocked_without_versioned_consent(monkeypatch):
    monkeypatch.setattr(
        ai_viewmodel,
        "load_settings_dict",
        lambda: {"ai_provider": "gemini", "ai_cloud_consent_version": ""},
    )
    monkeypatch.setattr(
        ai_viewmodel,
        "get_provider",
        lambda _settings: pytest.fail("Onaysız bulut sağlayıcısı çağrılmamalı"),
    )
    view_model = AIViewModel()

    with pytest.raises(RuntimeError, match="bulut veri onayını"):
        view_model._get_provider_or_raise()
    assert view_model.cloud_upload_notice_required()


def test_delete_all_data_stops_before_session_when_backup_fails(monkeypatch):
    monkeypatch.setattr(
        settings_viewmodel.BackupService,
        "create_backup",
        lambda: BackupResult(False, error="forced backup failure"),
    )
    monkeypatch.setattr(
        settings_viewmodel,
        "get_session",
        lambda: pytest.fail("Yedek başarısızken veritabanı oturumu açılmamalı"),
    )

    with pytest.raises(RuntimeError, match="hiçbir veri silinmedi"):
        SettingsViewModel._delete_all_data_task()

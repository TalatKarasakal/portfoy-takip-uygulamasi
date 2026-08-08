"""Bulut sağlayıcı sırlarını işletim sisteminin güvenli kasasında tutar."""

from __future__ import annotations

from typing import Protocol

from app.utils.logger import register_secret


class SecretStoreError(RuntimeError):
    """İşletim sistemi anahtar kasası kullanılamadığında üretilir."""


class _KeyringModule(Protocol):
    def get_keyring(self): ...

    def get_password(self, service_name: str, username: str) -> str | None: ...

    def set_password(self, service_name: str, username: str, password: str) -> None: ...

    def delete_password(self, service_name: str, username: str) -> None: ...


class SecretService:
    """Gemini anahtarını macOS Keychain/Windows Credential Locker'da yönetir."""

    SERVICE_NAME = "portfolio-tracker"
    GEMINI_ACCOUNT = "gemini-api-key"

    @classmethod
    def _keyring(cls) -> _KeyringModule:
        try:
            import keyring
        except ImportError as exc:  # pragma: no cover - paketleme hatası
            raise SecretStoreError("Sistem anahtar kasası bileşeni kurulu değil.") from exc

        try:
            backend = keyring.get_keyring()
            priority = float(getattr(backend, "priority", 0))
        except Exception as exc:
            raise SecretStoreError("Sistem anahtar kasasına erişilemedi.") from exc
        if priority <= 0:
            raise SecretStoreError("Güvenli bir sistem anahtar kasası bulunamadı.")
        return keyring

    @classmethod
    def is_available(cls) -> bool:
        try:
            cls._keyring()
            return True
        except SecretStoreError:
            return False

    @classmethod
    def get_gemini_api_key(cls) -> str:
        try:
            value = cls._keyring().get_password(cls.SERVICE_NAME, cls.GEMINI_ACCOUNT)
        except SecretStoreError:
            raise
        except Exception as exc:
            raise SecretStoreError("Gemini anahtarı sistem kasasından okunamadı.") from exc
        secret = (value or "").strip()
        if secret:
            register_secret(secret)
        return secret

    @classmethod
    def has_gemini_api_key(cls) -> bool:
        try:
            return bool(cls.get_gemini_api_key())
        except SecretStoreError:
            return False

    @classmethod
    def set_gemini_api_key(cls, api_key: str) -> None:
        secret = api_key.strip()
        if not secret:
            raise ValueError("Gemini API anahtarı boş olamaz.")
        try:
            cls._keyring().set_password(cls.SERVICE_NAME, cls.GEMINI_ACCOUNT, secret)
        except SecretStoreError:
            raise
        except Exception as exc:
            raise SecretStoreError("Gemini anahtarı sistem kasasına yazılamadı.") from exc
        register_secret(secret)

    @classmethod
    def delete_gemini_api_key(cls) -> None:
        try:
            cls._keyring().delete_password(cls.SERVICE_NAME, cls.GEMINI_ACCOUNT)
        except SecretStoreError:
            raise
        except Exception as exc:
            # Bazı backend'ler kayıt yokken hata üretir; çağıran için bu durum güvenlidir.
            if exc.__class__.__name__ != "PasswordDeleteError":
                raise SecretStoreError("Gemini anahtarı sistem kasasından silinemedi.") from exc

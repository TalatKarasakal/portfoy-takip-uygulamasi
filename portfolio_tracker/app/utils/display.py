"""Görüntüleme para birimi durumu (TRY/USD).

Tüm parasal değerler dahili olarak TL cinsinden hesaplanır. Kullanıcı USD
görünümünü seçtiğinde, gösterim katmanı bu modüldeki güncel kur ile çevirir.
Hesaplama mantığı asla USD'ye bağlı değildir — yalnızca biçimlendirme.
"""

from app.utils.formatters import format_currency


class _DisplayCurrency:
    def __init__(self):
        self.mode = "TRY"   # "TRY" | "USD"
        self.usd_try = 0.0  # 1 USD = ? TL

    def set_mode(self, mode: str) -> None:
        if mode in ("TRY", "USD"):
            self.mode = mode

    def set_rate(self, rate) -> None:
        try:
            self.usd_try = float(rate or 0)
        except (TypeError, ValueError):
            self.usd_try = 0.0

    @property
    def symbol(self) -> str:
        return "$" if self.mode == "USD" else "₺"

    def format(self, value_try: float) -> str:
        """TL cinsinden değeri aktif moda göre biçimlendirir."""
        if self.mode == "USD" and self.usd_try > 0:
            return format_currency(value_try / self.usd_try, "$")
        return format_currency(value_try, "₺")

    def format_opposite(self, value_try: float) -> str:
        """Aktif modun tersi para biriminde biçimlendirir (alt satır için)."""
        if self.mode == "USD":
            return format_currency(value_try, "₺")
        if self.usd_try > 0:
            return format_currency(value_try / self.usd_try, "$")
        return ""


# Uygulama genelinde tek örnek
display = _DisplayCurrency()

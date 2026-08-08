def format_currency(value: float, symbol: str = "₺") -> str:
    """Para birimini biçimlendirir."""
    return f"{value:,.2f} {symbol}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_percent(value: float) -> str:
    """Yüzdeyi biçimlendirir."""
    prefix = "+" if value > 0 else ""
    return f"{prefix}{value:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def format_decimal(value, min_decimals: int = 2, max_decimals: int = 6) -> str:
    """Sayısal değeri 6 basamağa kadar, gereksiz sıfırları kırparak gösterir."""
    rendered = f"{float(value):,.{max_decimals}f}"
    whole, fraction = rendered.rsplit(".", 1)
    fraction = fraction.rstrip("0")
    if len(fraction) < min_decimals:
        fraction += "0" * (min_decimals - len(fraction))
    return f"{whole}.{fraction}".replace(",", "X").replace(".", ",").replace("X", ".")

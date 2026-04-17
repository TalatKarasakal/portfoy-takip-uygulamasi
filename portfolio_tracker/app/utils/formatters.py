def format_currency(value: float, symbol: str = "₺") -> str:
    """Para birimini biçimlendirir."""
    return f"{value:,.2f} {symbol}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_percent(value: float) -> str:
    """Yüzdeyi biçimlendirir."""
    prefix = "+" if value > 0 else ""
    return f"{prefix}{value:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")

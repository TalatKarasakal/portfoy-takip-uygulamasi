"""SQLAlchemy ORM modelleri.

Bu paketi import etmek tüm model sınıflarının declarative registry'ye
kaydolmasını sağlar. Modeller arası `relationship` tanımları string isimle
(örn. "PriceHistory") çözüldüğü için, herhangi bir model kullanılmadan önce
tüm modellerin import edilmiş olması gerekir; aksi halde SQLAlchemy mapper
konfigürasyonu "failed to locate a name" hatasıyla başarısız olur.
"""

from app.models.alert import Alert, AlertType
from app.models.asset import Asset, AssetType
from app.models.import_batch import ImportBatch, ImportBatchStatus
from app.models.portfolio import CashEntry, CashEntryType, Portfolio, WatchlistItem
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.price_history import PriceHistory
from app.models.settings import Settings
from app.models.transaction import Transaction, TransactionType

__all__ = [
    "Asset",
    "AssetType",
    "Transaction",
    "TransactionType",
    "PriceHistory",
    "PortfolioSnapshot",
    "Portfolio",
    "CashEntry",
    "CashEntryType",
    "WatchlistItem",
    "Alert",
    "AlertType",
    "Settings",
    "ImportBatch",
    "ImportBatchStatus",
]

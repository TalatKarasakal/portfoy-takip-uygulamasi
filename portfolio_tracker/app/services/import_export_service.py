"""Kayıpsız Excel round-trip, önizleme ve tek transaction içe aktarımı."""

from __future__ import annotations

import datetime
import enum
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Optional

import pandas as pd
from sqlalchemy.orm import Session, joinedload

from app.database.types import utc_now
from app.models.asset import AssetType
from app.models.dividend_plan import DividendPlan, DividendPlanStatus
from app.models.import_batch import ImportBatch, ImportBatchStatus
from app.models.portfolio import CashEntry, CashEntryType, Portfolio, WatchlistItem
from app.models.transaction import Transaction, TransactionType
from app.services.portfolio_account_service import PortfolioAccountService
from app.services.transaction_service import TransactionCommand, TransactionService
from app.utils.logger import app_logger

WORKBOOK_SCHEMA_VERSION = "3"
PORTFOLIO_EXPORT_COLUMNS = [
    "Kod",
    "Ad",
    "Tür",
    "Adet",
    "Ort. Maliyet",
    "Güncel Fiyat",
    "Toplam Maliyet",
    "Güncel Değer",
    "Toplam K/Z",
    "K/Z %",
    "Portföy %",
]


class ImportRowStatus(enum.Enum):
    VALID = "Geçerli"
    WARNING = "Uyarı"
    DUPLICATE = "Mükerrer"
    ERROR = "Hatalı"


@dataclass
class ImportPreviewRow:
    sheet: str
    row_number: int
    entity: str
    status: ImportRowStatus
    data: dict[str, Any]
    message: str = ""
    selected: bool = True


@dataclass
class ImportPreview:
    source_path: str
    default_portfolio_id: int
    rows: list[ImportPreviewRow] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(row.status == ImportRowStatus.ERROR for row in self.rows)

    @property
    def selected_count(self) -> int:
        return sum(row.selected for row in self.rows)


@dataclass(frozen=True)
class ImportBatchResult:
    batch_id: int
    imported_count: int


class ImportValidationError(ValueError):
    pass


def _normalize_header(value: Any) -> str:
    text = str(value).strip().casefold().replace("ı", "i")
    text = "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )
    return " ".join(text.replace("_", " ").split())


def _decimal(value: Any, label: str) -> Decimal:
    if pd.isna(value):
        value = 0
    try:
        result = Decimal(str(value).replace(",", "."))
    except Exception as exc:
        raise ImportValidationError(f"{label} geçerli bir sayı değil.") from exc
    if not result.is_finite():
        raise ImportValidationError(f"{label} sonlu bir sayı olmalıdır.")
    return result.quantize(Decimal("0.000001"))


def _date(value: Any) -> datetime.date:
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    try:
        return pd.to_datetime(value, errors="raise").date()
    except Exception as exc:
        raise ImportValidationError("Tarih geçerli değil.") from exc


def _value(row: dict[str, Any], *aliases: str, default=None):
    normalized = {_normalize_header(key): value for key, value in row.items()}
    for alias in aliases:
        key = _normalize_header(alias)
        if key in normalized:
            return normalized[key]
    return default


class ImportExportService:
    @staticmethod
    def export_excel(
        session: Session,
        file_path: str,
        portfolio_items: Optional[list[dict[str, Any]]] = None,
        columns: Optional[list[str]] = None,
        portfolio_id: Optional[int] = 1,
    ) -> None:
        """Seçili veya tüm portföyleri sürümlü workbook olarak dışa aktarır."""
        selected = columns or PORTFOLIO_EXPORT_COLUMNS
        portfolio_rows = []
        for item in portfolio_items or []:
            pnl = item.get("realized_pnl", 0) + item.get("unrealized_pnl", 0)
            cost = item.get("total_cost", 0)
            full = {
                "Kod": item.get("code", ""),
                "Ad": item.get("name", ""),
                "Tür": item.get("type", ""),
                "Adet": item.get("quantity", 0),
                "Ort. Maliyet": item.get("avg_cost", 0),
                "Güncel Fiyat": item.get("current_price", 0),
                "Toplam Maliyet": cost,
                "Güncel Değer": item.get("current_value", 0),
                "Toplam K/Z": pnl,
                "K/Z %": pnl / cost * 100 if cost else 0,
                "Portföy %": item.get("portfolio_pct", 0),
            }
            portfolio_rows.append({key: full[key] for key in selected if key in full})

        portfolios_query = session.query(Portfolio)
        if portfolio_id is not None:
            portfolios_query = portfolios_query.filter(Portfolio.id == portfolio_id)
        portfolios = portfolios_query.order_by(Portfolio.id).all()
        portfolio_names = {row.id: row.name for row in portfolios}

        tx_query = session.query(Transaction).options(
            joinedload(Transaction.asset), joinedload(Transaction.portfolio)
        )
        cash_query = session.query(CashEntry).options(joinedload(CashEntry.portfolio))
        watch_query = session.query(WatchlistItem).options(
            joinedload(WatchlistItem.asset), joinedload(WatchlistItem.portfolio)
        )
        dividend_plan_query = session.query(DividendPlan).options(
            joinedload(DividendPlan.asset), joinedload(DividendPlan.portfolio)
        )
        if portfolio_id is not None:
            tx_query = tx_query.filter(Transaction.portfolio_id == portfolio_id)
            cash_query = cash_query.filter(CashEntry.portfolio_id == portfolio_id)
            watch_query = watch_query.filter(WatchlistItem.portfolio_id == portfolio_id)
            dividend_plan_query = dividend_plan_query.filter(
                DividendPlan.portfolio_id == portfolio_id
            )

        tx_rows = [
            {
                "Portföy": row.portfolio.name,
                "Tarih": row.date,
                "Varlık Kodu": row.asset.code,
                "Varlık Adı": row.asset.name,
                "Varlık Türü": row.asset.asset_type.name,
                "İşlem Türü": row.transaction_type.name,
                "Adet": float(row.quantity),
                "Birim Fiyat": float(row.unit_price),
                "Komisyon": float(row.commission),
                "Vergi": float(row.tax),
                "Not": row.note or "",
            }
            for row in tx_query.order_by(Transaction.date, Transaction.id).all()
        ]
        cash_rows = [
            {
                "Portföy": row.portfolio.name,
                "Tarih": row.date,
                "Hareket Türü": row.entry_type.name,
                "Tutar": float(row.amount),
                "Not": row.note or "",
            }
            for row in cash_query.order_by(CashEntry.date, CashEntry.id).all()
        ]
        watch_rows = [
            {
                "Portföy": row.portfolio.name,
                "Varlık Kodu": row.asset.code,
                "Varlık Adı": row.asset.name,
                "Varlık Türü": row.asset.asset_type.name,
                "Hedef Fiyat": float(row.target_price) if row.target_price is not None else None,
                "Not": row.note or "",
            }
            for row in watch_query.order_by(WatchlistItem.id).all()
        ]
        dividend_plan_rows = [
            {
                "Portföy": row.portfolio.name,
                "Varlık Kodu": row.asset.code,
                "Varlık Adı": row.asset.name,
                "Varlık Türü": row.asset.asset_type.name,
                "Ödeme Tarihi": row.payment_date,
                "Hisse Başı Brüt": float(row.gross_per_share),
                "Beklenen Adet": (
                    float(row.expected_quantity) if row.expected_quantity is not None else None
                ),
                "Durum": row.status.name,
                "Not": row.note or "",
            }
            for row in dividend_plan_query.order_by(
                DividendPlan.payment_date, DividendPlan.id
            ).all()
        ]
        metadata = [
            {"Anahtar": "schema_version", "Değer": WORKBOOK_SCHEMA_VERSION},
            {"Anahtar": "exported_at_utc", "Değer": utc_now().isoformat()},
        ]

        with pd.ExcelWriter(file_path, engine="openpyxl", datetime_format="yyyy-mm-dd") as writer:
            pd.DataFrame(metadata).to_excel(writer, sheet_name="_Metadata", index=False)
            pd.DataFrame(
                [{"Portföy": row.name, "Varsayılan": bool(row.is_default)} for row in portfolios]
            ).to_excel(writer, sheet_name="Portföyler", index=False)
            pd.DataFrame(portfolio_rows).to_excel(writer, sheet_name="Portföy", index=False)
            pd.DataFrame(tx_rows).to_excel(writer, sheet_name="İşlemler", index=False)
            pd.DataFrame(cash_rows).to_excel(writer, sheet_name="Nakit", index=False)
            pd.DataFrame(watch_rows).to_excel(writer, sheet_name="İzleme Listesi", index=False)
            pd.DataFrame(dividend_plan_rows).to_excel(
                writer, sheet_name="Temettü Planı", index=False
            )
        app_logger.info("Excel dışa aktarımı tamamlandı: %s", file_path)

    @staticmethod
    def _transaction_fingerprints(session: Session) -> set[tuple]:
        rows = session.query(Transaction).options(
            joinedload(Transaction.asset), joinedload(Transaction.portfolio)
        ).all()
        return {
            (
                row.portfolio.name,
                row.asset.code,
                row.transaction_type.name,
                row.date,
                Decimal(str(row.quantity)).quantize(Decimal("0.000001")),
                Decimal(str(row.unit_price)).quantize(Decimal("0.000001")),
                Decimal(str(row.commission)).quantize(Decimal("0.000001")),
                Decimal(str(row.tax)).quantize(Decimal("0.000001")),
                row.note or "",
            )
            for row in rows
        }

    @staticmethod
    def _transaction_preview_row(
        session: Session,
        sheet: str,
        row_number: int,
        raw: dict[str, Any],
        default_portfolio_name: str,
        fingerprints: set[tuple],
        legacy_quantity_cost: bool = False,
    ) -> ImportPreviewRow:
        try:
            code = str(_value(raw, "Varlık Kodu", "Kod", "Fon Kodu", default="")).strip().upper()
            if not code or code == "NAN":
                raise ImportValidationError("Varlık kodu boş olamaz.")
            name = str(_value(raw, "Varlık Adı", "Ad", "Fon Adı", default=code)).strip() or code
            portfolio_name = str(_value(raw, "Portföy", default=default_portfolio_name)).strip()
            type_raw = str(_value(raw, "Varlık Türü", default="")).strip().upper()
            warning = ""
            if type_raw not in AssetType.__members__:
                type_raw = "BIST" if 4 <= len(code) <= 5 else "TEFAS"
                warning = "Varlık türü kod uzunluğundan tahmin edildi."
            if legacy_quantity_cost:
                kind = "BUY"
                tx_date = datetime.date.today()
                price_value = _value(raw, "Ortalama Maliyet", "Ort. Maliyet", "Maliyet")
                note = "Excel Import - Toplu Maliyet"
            else:
                kind_raw = str(_value(raw, "İşlem Türü", "Tür", default="")).strip().upper()
                kind = {
                    "AL": "BUY",
                    "ALIM": "BUY",
                    "SAT": "SELL",
                    "SATIM": "SELL",
                    "TEMETTÜ": "DIVIDEND",
                    "TEMETTU": "DIVIDEND",
                    "BÖLÜNME": "SPLIT",
                    "BOLUNME": "SPLIT",
                }.get(kind_raw, kind_raw)
                if kind not in {"BUY", "SELL", "DIVIDEND", "SPLIT"}:
                    raise ImportValidationError("İşlem türü tanınmıyor.")
                tx_date = _date(_value(raw, "Tarih"))
                price_value = _value(raw, "Birim Fiyat", "Maliyet")
                note = str(_value(raw, "Not", default="") or "").strip()
            quantity = _decimal(_value(raw, "Adet", default=0), "Adet")
            price = _decimal(price_value, "Birim fiyat")
            commission = _decimal(_value(raw, "Komisyon", default=0), "Komisyon")
            tax = _decimal(_value(raw, "Vergi", default=0), "Vergi")
            fingerprint = (
                portfolio_name,
                code,
                kind,
                tx_date,
                quantity,
                price,
                commission,
                tax,
                note,
            )
            duplicate = fingerprint in fingerprints
            status = ImportRowStatus.DUPLICATE if duplicate else (
                ImportRowStatus.WARNING if warning else ImportRowStatus.VALID
            )
            return ImportPreviewRow(
                sheet,
                row_number,
                "transaction",
                status,
                {
                    "portfolio_name": portfolio_name,
                    "code": code,
                    "name": name,
                    "asset_type": type_raw,
                    "transaction_type": kind,
                    "date": tx_date,
                    "quantity": quantity,
                    "unit_price": price,
                    "commission": commission,
                    "tax": tax,
                    "note": note,
                },
                message="Aynı işlem zaten kayıtlı." if duplicate else warning,
                selected=not duplicate,
            )
        except Exception as exc:
            return ImportPreviewRow(
                sheet,
                row_number,
                "transaction",
                ImportRowStatus.ERROR,
                {},
                message=str(exc),
                selected=False,
            )

    @staticmethod
    def preview_excel(session: Session, file_path: str, default_portfolio_id: int = 1) -> ImportPreview:
        sheets = pd.read_excel(file_path, sheet_name=None)
        default_portfolio = session.get(Portfolio, default_portfolio_id)
        if default_portfolio is None:
            raise ImportValidationError("Varsayılan portföy bulunamadı.")
        preview = ImportPreview(str(file_path), default_portfolio_id)
        fingerprints = ImportExportService._transaction_fingerprints(session)
        has_transaction_sheet = any(_normalize_header(name) == "islemler" for name in sheets)

        for sheet_name, frame in sheets.items():
            normalized_sheet = _normalize_header(sheet_name)
            columns = {_normalize_header(column) for column in frame.columns}
            if normalized_sheet in {"metadata", "portfoyler"}:
                continue
            if normalized_sheet == "portfoy" and has_transaction_sheet:
                continue
            is_transaction = (
                normalized_sheet == "islemler"
                or ({"tarih", "adet"}.issubset(columns) and any("kod" in col for col in columns))
            )
            is_legacy_cost = (
                not is_transaction
                and "adet" in columns
                and any("maliyet" in col for col in columns)
                and any("kod" in col for col in columns)
            )
            if is_transaction or is_legacy_cost:
                for offset, raw in enumerate(frame.to_dict("records"), start=2):
                    preview.rows.append(
                        ImportExportService._transaction_preview_row(
                            session,
                            sheet_name,
                            offset,
                            raw,
                            default_portfolio.name,
                            fingerprints,
                            legacy_quantity_cost=is_legacy_cost,
                        )
                    )
                continue
            if normalized_sheet == "nakit":
                for offset, raw in enumerate(frame.to_dict("records"), start=2):
                    try:
                        data = {
                            "portfolio_name": str(
                                _value(raw, "Portföy", default=default_portfolio.name)
                            ).strip(),
                            "date": _date(_value(raw, "Tarih")),
                            "entry_type": str(_value(raw, "Hareket Türü")).strip().upper(),
                            "amount": _decimal(_value(raw, "Tutar"), "Tutar"),
                            "note": str(_value(raw, "Not", default="") or "").strip(),
                        }
                        if data["entry_type"] not in CashEntryType.__members__:
                            raise ImportValidationError("Nakit hareket türü tanınmıyor.")
                        preview.rows.append(
                            ImportPreviewRow(
                                sheet_name, offset, "cash", ImportRowStatus.VALID, data
                            )
                        )
                    except Exception as exc:
                        preview.rows.append(
                            ImportPreviewRow(
                                sheet_name,
                                offset,
                                "cash",
                                ImportRowStatus.ERROR,
                                {},
                                str(exc),
                                False,
                            )
                        )
                continue
            if normalized_sheet == "izleme listesi":
                for offset, raw in enumerate(frame.to_dict("records"), start=2):
                    try:
                        code = str(_value(raw, "Varlık Kodu", "Kod")).strip().upper()
                        if not code:
                            raise ImportValidationError("Varlık kodu boş olamaz.")
                        data = {
                            "portfolio_name": str(
                                _value(raw, "Portföy", default=default_portfolio.name)
                            ).strip(),
                            "code": code,
                            "name": str(_value(raw, "Varlık Adı", default=code)).strip() or code,
                            "asset_type": str(
                                _value(raw, "Varlık Türü", default="BIST")
                            ).strip().upper(),
                            "target_price": _value(raw, "Hedef Fiyat"),
                            "note": str(_value(raw, "Not", default="") or "").strip(),
                        }
                        preview.rows.append(
                            ImportPreviewRow(
                                sheet_name, offset, "watchlist", ImportRowStatus.VALID, data
                            )
                        )
                    except Exception as exc:
                        preview.rows.append(
                            ImportPreviewRow(
                                sheet_name,
                                offset,
                                "watchlist",
                                ImportRowStatus.ERROR,
                                {},
                                str(exc),
                                False,
                            )
                        )
                continue
            if normalized_sheet == "temettu plani":
                for offset, raw in enumerate(frame.to_dict("records"), start=2):
                    try:
                        code = str(_value(raw, "Varlık Kodu", "Kod")).strip().upper()
                        if not code:
                            raise ImportValidationError("Varlık kodu boş olamaz.")
                        status = str(_value(raw, "Durum", default="PLANNED")).strip().upper()
                        if status not in DividendPlanStatus.__members__:
                            raise ImportValidationError("Temettü plan durumu tanınmıyor.")
                        expected_raw = _value(raw, "Beklenen Adet")
                        data = {
                            "portfolio_name": str(
                                _value(raw, "Portföy", default=default_portfolio.name)
                            ).strip(),
                            "code": code,
                            "name": str(_value(raw, "Varlık Adı", default=code)).strip() or code,
                            "asset_type": str(
                                _value(raw, "Varlık Türü", default="BIST")
                            ).strip().upper(),
                            "payment_date": _date(_value(raw, "Ödeme Tarihi")),
                            "gross_per_share": _decimal(
                                _value(raw, "Hisse Başı Brüt"), "Hisse başı brüt"
                            ),
                            "expected_quantity": (
                                None
                                if pd.isna(expected_raw)
                                else _decimal(expected_raw, "Beklenen adet")
                            ),
                            "status": status,
                            "note": str(_value(raw, "Not", default="") or "").strip(),
                        }
                        preview.rows.append(
                            ImportPreviewRow(
                                sheet_name,
                                offset,
                                "dividend_plan",
                                ImportRowStatus.VALID,
                                data,
                            )
                        )
                    except Exception as exc:
                        preview.rows.append(
                            ImportPreviewRow(
                                sheet_name,
                                offset,
                                "dividend_plan",
                                ImportRowStatus.ERROR,
                                {},
                                str(exc),
                                False,
                            )
                        )
                continue
        if not preview.rows:
            raise ImportValidationError("Uygun içe aktarma sayfası bulunamadı.")
        return preview

    @staticmethod
    def _portfolio_for_name(session: Session, name: str) -> Portfolio:
        row = session.query(Portfolio).filter(Portfolio.name == name).first()
        return row or PortfolioAccountService.create_portfolio(session, name)

    @staticmethod
    def apply_preview(
        session: Session,
        preview: ImportPreview,
        selected_rows: Optional[Iterable[int]] = None,
    ) -> ImportBatchResult:
        if preview.has_errors:
            raise ImportValidationError("Hatalı satırlar düzeltilmeden hiçbir kayıt aktarılamaz.")
        selected_set = set(selected_rows) if selected_rows is not None else None
        rows = [
            row
            for index, row in enumerate(preview.rows)
            if (index in selected_set if selected_set is not None else row.selected)
        ]
        if not rows:
            raise ImportValidationError("İçe aktarılacak satır seçilmedi.")

        batch = ImportBatch(
            portfolio_id=preview.default_portfolio_id,
            source_name=Path(preview.source_path).name[:255],
            source_type="EXCEL",
            status=ImportBatchStatus.APPLIED,
        )
        session.add(batch)
        session.flush()

        for row in rows:
            data = row.data
            portfolio = ImportExportService._portfolio_for_name(session, data["portfolio_name"])
            if row.entity == "transaction":
                asset = TransactionService.get_or_create_asset(
                    session, data["code"], data["name"], data["asset_type"]
                )
                command = TransactionCommand.from_values(
                    portfolio_id=portfolio.id,
                    asset_id=asset.id,
                    transaction_type=data["transaction_type"],
                    date=data["date"],
                    quantity=data["quantity"],
                    unit_price=data["unit_price"],
                    commission=data["commission"],
                    tax=data["tax"],
                    note=data["note"],
                )
                transaction = TransactionService.create(session, command)
                transaction.import_batch_id = batch.id
            elif row.entity == "cash":
                entry = PortfolioAccountService.add_cash_entry(
                    session,
                    portfolio.id,
                    data["entry_type"],
                    data["date"],
                    data["amount"],
                    data["note"],
                )
                entry.import_batch_id = batch.id
            elif row.entity == "watchlist":
                asset = TransactionService.get_or_create_asset(
                    session, data["code"], data["name"], data["asset_type"]
                )
                item = PortfolioAccountService.add_to_watchlist(
                    session,
                    portfolio.id,
                    asset.id,
                    data["target_price"],
                    data["note"],
                )
                item.import_batch_id = batch.id
            elif row.entity == "dividend_plan":
                asset = TransactionService.get_or_create_asset(
                    session, data["code"], data["name"], data["asset_type"]
                )
                plan = DividendPlan(
                    portfolio_id=portfolio.id,
                    asset_id=asset.id,
                    payment_date=data["payment_date"],
                    gross_per_share=data["gross_per_share"],
                    expected_quantity=data["expected_quantity"],
                    status=DividendPlanStatus[data["status"]],
                    note=data["note"] or None,
                    import_batch_id=batch.id,
                )
                if plan.status == DividendPlanStatus.PAID:
                    plan.linked_transaction = (
                        session.query(Transaction)
                        .filter(
                            Transaction.import_batch_id == batch.id,
                            Transaction.portfolio_id == portfolio.id,
                            Transaction.asset_id == asset.id,
                            Transaction.date == plan.payment_date,
                            Transaction.transaction_type == TransactionType.DIVIDEND,
                            Transaction.quantity == plan.expected_quantity,
                            Transaction.unit_price == plan.gross_per_share,
                        )
                        .first()
                    )
                    if plan.linked_transaction is None:
                        plan.status = DividendPlanStatus.PLANNED
                session.add(plan)
        session.flush()
        return ImportBatchResult(batch.id, len(rows))

    @staticmethod
    def import_excel(session: Session, file_path: str, portfolio_id: int = 1) -> bool:
        """Uyumluluk yardımcısı; önizlemeyi yalnız hatasızsa tek transaction uygular."""
        try:
            preview = ImportExportService.preview_excel(session, file_path, portfolio_id)
            ImportExportService.apply_preview(session, preview)
            session.commit()
            return True
        except Exception as exc:
            session.rollback()
            app_logger.error("Excel içe aktarma başarısız: %s", exc)
            return False

    @staticmethod
    def undo_last_import(session: Session, portfolio_id: Optional[int] = None) -> int:
        query = session.query(ImportBatch).filter(ImportBatch.status == ImportBatchStatus.APPLIED)
        if portfolio_id is not None:
            query = query.filter(ImportBatch.portfolio_id == portfolio_id)
        batch = query.order_by(ImportBatch.created_at.desc(), ImportBatch.id.desc()).first()
        if batch is None:
            raise ImportValidationError("Geri alınabilecek bir içe aktarım bulunamadı.")

        plans = session.query(DividendPlan).filter(
            DividendPlan.import_batch_id == batch.id
        ).all()
        count = len(plans)
        for plan in plans:
            session.delete(plan)
        session.flush()

        transactions = (
            session.query(Transaction)
            .filter(Transaction.import_batch_id == batch.id)
            .order_by(Transaction.date.desc(), Transaction.id.desc())
            .all()
        )
        for transaction in transactions:
            TransactionService.delete(session, transaction.id)
            count += 1
        for model in (CashEntry, WatchlistItem):
            rows = session.query(model).filter(model.import_batch_id == batch.id).all()
            count += len(rows)
            for row in rows:
                session.delete(row)
        batch.status = ImportBatchStatus.UNDONE
        batch.undone_at = utc_now()
        session.flush()
        return count

    @staticmethod
    def _is_percentage_cols(columns) -> bool:
        normalized = {_normalize_header(column) for column in columns}
        has_code = any("kod" in column for column in normalized)
        has_percentage = any(
            token in column for column in normalized for token in ("yuzde", "%", "oran")
        )
        has_other = any(
            token in column for column in normalized for token in ("tarih", "adet", "maliyet")
        )
        return has_code and has_percentage and not has_other

    @staticmethod
    def detect_percentage(file_path: str) -> bool:
        try:
            return any(
                ImportExportService._is_percentage_cols(frame.columns)
                for frame in pd.read_excel(file_path, sheet_name=None).values()
            )
        except Exception as exc:
            app_logger.error("Yüzdelik tespiti başarısız: %s", exc)
            return False

    @staticmethod
    def import_percentage(
        session: Session,
        file_path: str,
        total_value: float,
        portfolio_id: int = 1,
    ) -> bool:
        """Fiyatı bulunamayan tek satırda dahi tamamını rollback eder."""
        from app.services.bist_service import BistService
        from app.services.tefas_service import TefasService

        try:
            pending = []
            bist = BistService()
            tefas = TefasService()
            for frame in pd.read_excel(file_path, sheet_name=None).values():
                if not ImportExportService._is_percentage_cols(frame.columns):
                    continue
                for raw in frame.to_dict("records"):
                    code = str(_value(raw, "Kod", "Varlık Kodu", default="")).strip().upper()
                    percentage = _decimal(
                        _value(raw, "Yüzde", "Yuzde", "%", "Oran"), "Yüzde"
                    )
                    if not code or percentage <= 0:
                        raise ImportValidationError("Kod ve yüzde pozitif olmalıdır.")
                    asset_type = AssetType.BIST if 4 <= len(code) <= 5 else AssetType.TEFAS
                    price = (
                        bist.fetch_current_price(code)
                        if asset_type == AssetType.BIST
                        else tefas.fetch_current_price(code)
                    )
                    if price is None or price <= 0:
                        raise ImportValidationError(f"{code} fiyatı alınamadı; aktarım durduruldu.")
                    target = Decimal(str(total_value)) * percentage / Decimal("100")
                    pending.append((code, asset_type, target / Decimal(str(price)), Decimal(str(price))))
            if not pending:
                raise ImportValidationError("Yüzdelik satır bulunamadı.")
            batch = ImportBatch(
                portfolio_id=portfolio_id,
                source_name=Path(file_path).name[:255],
                source_type="PERCENTAGE",
            )
            session.add(batch)
            session.flush()
            for code, asset_type, quantity, price in pending:
                asset = TransactionService.get_or_create_asset(
                    session, code, code, asset_type
                )
                transaction = TransactionService.create(
                    session,
                    TransactionCommand.from_values(
                        portfolio_id=portfolio_id,
                        asset_id=asset.id,
                        transaction_type="BUY",
                        date=datetime.date.today(),
                        quantity=quantity,
                        unit_price=price,
                        note="Excel Import - Yüzdelik",
                    ),
                )
                transaction.import_batch_id = batch.id
            session.commit()
            return True
        except Exception as exc:
            session.rollback()
            app_logger.error("Yüzdelik içe aktarım başarısız: %s", exc)
            return False

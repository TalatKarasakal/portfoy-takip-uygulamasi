import pandas as pd
import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, TransactionType
from app.utils.logger import app_logger

# Portföy dışa aktarımında seçilebilir tüm sütunlar (sıra korunur)
PORTFOLIO_EXPORT_COLUMNS = [
    "Kod", "Ad", "Tür", "Adet", "Ort. Maliyet", "Güncel Fiyat",
    "Toplam Maliyet", "Güncel Değer", "Toplam K/Z", "K/Z %", "Portföy %",
]


class ImportExportService:
    @staticmethod
    def export_excel(
        session: Session,
        file_path: str,
        portfolio_items: Optional[List[Dict[str, Any]]] = None,
        columns: Optional[List[str]] = None,
    ):
        """Portföyü ve işlem geçmişini Excel'e dışa aktarır.

        Args:
            portfolio_items: Güncel fiyat/değer içeren hesaplanmış liste
                (PortfolioViewModel.cached_portfolio_data). Verilirse "Portföy"
                sayfası güncel değerlerle yazılır; verilmezse varlık listesi yazılır.
            columns: Portföy sayfasında yer alacak sütun adları (None => tümü).
        """
        selected = columns or PORTFOLIO_EXPORT_COLUMNS
        portfolio_rows = []

        if portfolio_items:
            for it in portfolio_items:
                pnl = it.get("realized_pnl", 0) + it.get("unrealized_pnl", 0)
                cost = it.get("total_cost", 0)
                pnl_pct = (pnl / cost * 100) if cost else 0
                full = {
                    "Kod": it.get("code", ""),
                    "Ad": it.get("name", ""),
                    "Tür": it.get("type", ""),
                    "Adet": it.get("quantity", 0),
                    "Ort. Maliyet": it.get("avg_cost", 0),
                    "Güncel Fiyat": it.get("current_price", 0),
                    "Toplam Maliyet": cost,
                    "Güncel Değer": it.get("current_value", 0),
                    "Toplam K/Z": pnl,
                    "K/Z %": pnl_pct,
                    "Portföy %": it.get("portfolio_pct", 0),
                }
                portfolio_rows.append({c: full[c] for c in selected if c in full})
        else:
            # Fiyat verisi yoksa temel varlık listesi
            for a in session.query(Asset).all():
                full = {"Kod": a.code, "Ad": a.name, "Tür": a.asset_type.name}
                portfolio_rows.append({c: full[c] for c in selected if c in full})

        # İşlemler (her zaman tam)
        tx_data = []
        for tx in session.query(Transaction).options(joinedload(Transaction.asset)).all():
            tx_data.append({
                "Tarih": tx.date,
                "Varlık Kodu": tx.asset.code if tx.asset else "",
                "İşlem Türü": tx.transaction_type.name,
                "Adet": float(tx.quantity),
                "Birim Fiyat": float(tx.unit_price),
                "Komisyon": float(tx.commission),
                "Vergi": float(tx.tax),
                "Not": tx.note,
            })

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            pd.DataFrame(portfolio_rows).to_excel(writer, sheet_name='Portföy', index=False)
            pd.DataFrame(tx_data).to_excel(writer, sheet_name='İşlemler', index=False)

        app_logger.info(f"Exported data to {file_path}")

    @staticmethod
    def import_excel(session: Session, file_path: str) -> bool:
        """Excel'den portföy veya işlem verisini içeri aktarır."""
        try:
            # Tüm sayfaları okuyup (dict) işlem yapmaya çalışalım
            dfs = pd.read_excel(file_path, sheet_name=None)
            
            success_any = False
            for sheet_name, df in dfs.items():
                cols = [str(c).lower() for c in df.columns]
                
                # Senaryo 3: Tam İşlem Geçmişi
                if any("tarih" in c for c in cols) and any("kod" in c for c in cols) and any("tür" in c for c in cols):
                    success_any = ImportExportService._process_full_transaction_history(session, df) or success_any
                    
                # Senaryo 2: Adet + Maliyet
                elif any("kod" in c for c in cols) and any("adet" in c for c in cols) and any("maliyet" in c for c in cols):
                    success_any = ImportExportService._process_quantity_cost(session, df) or success_any
                    
                # Kendi "Varlıklar" listemizse veya basit liste ("Fon Kodu", "Fon Adı") ise
                elif any("kod" in c for c in cols) and any("ad" in c for c in cols):
                    success_any = ImportExportService._process_assets_only(session, df) or success_any
                
                # Senaryo 1: Yüzdelik — ayrı akışla (toplam değer gerekir) ele alınır.
                elif ImportExportService._is_percentage_cols(cols):
                    continue
                    
            if not success_any:
                app_logger.error("Uygun sütun formatı hiçbir sayfada bulunamadı.")
                return False
                
            return True
                
        except Exception as e:
            app_logger.error(f"Import error: {e}")
            return False

    @staticmethod
    def _is_percentage_cols(cols) -> bool:
        """Sütunlar 'kod + yüzde' yüzdelik senaryosuna mı uyuyor?"""
        has_code = any("kod" in c for c in cols)
        has_pct = any(("yüzde" in c) or ("yuzde" in c) or ("%" in c) or ("oran" in c) for c in cols)
        # Diğer senaryoların belirleyici sütunları yoksa yüzdeliktir
        has_other = any(("tarih" in c) or ("adet" in c) or ("maliyet" in c) for c in cols)
        return has_code and has_pct and not has_other

    @staticmethod
    def detect_percentage(file_path: str) -> bool:
        """Dosyada (herhangi bir sayfada) yüzdelik senaryo var mı kontrol eder."""
        try:
            dfs = pd.read_excel(file_path, sheet_name=None)
            for _, df in dfs.items():
                cols = [str(c).lower() for c in df.columns]
                if ImportExportService._is_percentage_cols(cols):
                    return True
        except Exception as e:
            app_logger.error(f"Yüzdelik tespiti hatası: {e}")
        return False

    @staticmethod
    def import_percentage(session: Session, file_path: str, total_value: float) -> bool:
        """Yüzdelik portföyü içeri aktarır.

        Her satır için adet, (toplam_değer * yüzde/100) / güncel_fiyat olarak
        hesaplanır. Güncel fiyat çekilemezse birim fiyat=hedef tutar, adet=1
        olarak kaydedilir (değer doğru kalır, adet nominal olur).
        """
        from app.services.bist_service import BistService
        from app.services.tefas_service import TefasService

        try:
            dfs = pd.read_excel(file_path, sheet_name=None)
            bist = BistService()
            tefas = TefasService()
            any_added = False

            for _, df in dfs.items():
                cols = [str(c).lower() for c in df.columns]
                if not ImportExportService._is_percentage_cols(cols):
                    continue

                # Kod ve yüzde sütunlarını bul
                code_col = next((c for c in df.columns if "kod" in str(c).lower()), None)
                pct_col = next((c for c in df.columns
                                if any(k in str(c).lower() for k in ("yüzde", "yuzde", "%", "oran"))), None)
                if code_col is None or pct_col is None:
                    continue

                for _, row in df.iterrows():
                    raw_code = row.get(code_col)
                    if pd.isna(raw_code):
                        continue
                    code = str(raw_code).strip().upper()
                    if not code or code == "NAN":
                        continue
                    try:
                        pct = float(row.get(pct_col))
                    except (TypeError, ValueError):
                        continue
                    if pct <= 0:
                        continue

                    asset = session.query(Asset).filter_by(code=code).first()
                    if not asset:
                        a_type = AssetType.BIST if len(code) >= 4 else AssetType.TEFAS
                        asset = Asset(code=code, name=code, asset_type=a_type)
                        session.add(asset)
                        session.flush()

                    target_value = total_value * pct / 100.0
                    if asset.asset_type == AssetType.BIST:
                        price = bist.fetch_current_price(code)
                    else:
                        price = tefas.fetch_current_price(code)

                    if price and price > 0:
                        quantity = target_value / price
                        unit_price = price
                        note = "Excel Import - Yüzdelik"
                    else:
                        quantity = 1.0
                        unit_price = target_value
                        note = "Excel Import - Yüzdelik (fiyat alınamadı, adet nominal)"

                    session.add(Transaction(
                        asset_id=asset.id,
                        transaction_type=TransactionType.BUY,
                        date=datetime.date.today(),
                        quantity=quantity,
                        unit_price=unit_price,
                        commission=0,
                        tax=0,
                        note=note,
                    ))
                    any_added = True

            if any_added:
                session.commit()
            return any_added
        except Exception as e:
            app_logger.error(f"Yüzdelik import hatası: {e}")
            session.rollback()
            return False

    @staticmethod
    def _ensure_assets_exist(session: Session, codes_and_names: dict) -> dict:
        """Varlıkları toplu olarak sorgular ve olmayanları toplu olarak oluşturur (N+1 query optimizasyonu).
        codes_and_names: dict of {code: name}
        Returns a dict of {code: Asset}
        """
        if not codes_and_names:
            return {}

        codes = list(codes_and_names.keys())
        existing_assets = session.query(Asset).filter(Asset.code.in_(codes)).all()
        asset_map = {a.code: a for a in existing_assets}

        new_assets = []
        for code, name in codes_and_names.items():
            if code not in asset_map:
                a_type = AssetType.BIST if len(code) >= 4 and len(code) <= 5 else AssetType.TEFAS
                asset = Asset(code=code, name=name, asset_type=a_type)
                new_assets.append(asset)
                asset_map[code] = asset

        if new_assets:
            session.add_all(new_assets)
            session.flush() # To get IDs for new assets

        return asset_map

    @staticmethod
    def _process_full_transaction_history(session: Session, df: pd.DataFrame) -> bool:
        records = df.to_dict('records')
        codes_and_names = {}
        valid_records = []

        for row in records:
            code = str(row.get("Kod", row.get("kod", ""))).strip().upper()
            if pd.isna(code) or not code or code == 'NAN':
                continue
            codes_and_names[code] = code  # varsayılan ad kodun kendisi
            valid_records.append((code, row))

        if not valid_records:
            return True

        asset_map = ImportExportService._ensure_assets_exist(session, codes_and_names)

        transactions = []
        for code, row in valid_records:
            asset = asset_map[code]
            ttype_str = str(row.get("Tür", row.get("tür", ""))).strip().upper()
            ttype = TransactionType.BUY if ttype_str in ["BUY", "AL", "ALIM"] else TransactionType.SELL
            
            tx = Transaction(
                asset_id=asset.id,
                transaction_type=ttype,
                date=row.get("Tarih", row.get("tarih", datetime.date.today())),
                quantity=row.get("Adet", row.get("adet", 0)),
                unit_price=row.get("Birim Fiyat", row.get("maliyet", 0)),
                commission=row.get("Komisyon", 0),
                tax=row.get("Vergi", 0)
            )
            transactions.append(tx)

        if transactions:
            session.add_all(transactions)
        session.commit()
        return True

    @staticmethod
    def _process_quantity_cost(session: Session, df: pd.DataFrame) -> bool:
        """Adet ve Ortalama Maliyet verilirse, tek bir sanal BUY işlemi olarak eklenecek."""
        records = df.to_dict('records')
        codes_and_names = {}
        valid_records = []

        for row in records:
            code = str(row.get("Kod", row.get("kod", ""))).strip().upper()
            if pd.isna(code) or not code or code == 'NAN':
                continue
            codes_and_names[code] = code
            valid_records.append((code, row))

        if not valid_records:
            return True

        asset_map = ImportExportService._ensure_assets_exist(session, codes_and_names)

        transactions = []
        for code, row in valid_records:
            asset = asset_map[code]
            tx = Transaction(
                asset_id=asset.id,
                transaction_type=TransactionType.BUY,
                date=datetime.date.today(),
                quantity=row.get("Adet", row.get("adet", 0)),
                unit_price=row.get("Ortalama Maliyet", row.get("maliyet", row.get("ortalama_maliyet", 0))),
                commission=0,
                tax=0,
                note="Excel Import - Toplu Maliyet"
            )
            transactions.append(tx)

        if transactions:
            session.add_all(transactions)
        session.commit()
        return True

    @staticmethod
    def _process_assets_only(session: Session, df: pd.DataFrame) -> bool:
        """Sadece varlık listesi (Kod, Ad) ve isteğe bağlı Tutar ekler."""
        kod_col, ad_col, tutar_col = None, None, None
        for col in df.columns:
            c_lower = str(col).lower()
            if "kod" in c_lower:
                kod_col = col
            elif "ad" in c_lower and "soyad" not in c_lower:
                ad_col = col
            elif "tutar" in c_lower or "maliyet" in c_lower:
                tutar_col = col

        records = df.to_dict('records')
        codes_and_names = {}
        valid_records = []

        for row in records:
            code = str(row[kod_col]).strip().upper() if kod_col and pd.notna(row.get(kod_col)) else None
            if not code or pd.isna(code) or code == 'NAN':
                continue
                
            name = str(row[ad_col]).strip() if ad_col and pd.notna(row.get(ad_col)) else None
            if not name or pd.isna(name) or name == 'NAN':
                name = code
                
            tutar = 0.0
            if tutar_col and pd.notna(row.get(tutar_col)):
                try:
                    tutar = float(row[tutar_col])
                except ValueError:
                    pass

            codes_and_names[code] = name
            valid_records.append((code, tutar))

        if not valid_records:
            return True

        asset_map = ImportExportService._ensure_assets_exist(session, codes_and_names)

        transactions = []
        for code, tutar in valid_records:
            asset = asset_map[code]

            # Eğer Tutar doldurulmuşsa bunu bir BUY işlemi olarak atalım (Miktar 1 birim)
            if tutar > 0 and not pd.isna(tutar):
                tx = Transaction(
                    asset_id=asset.id,
                    transaction_type=TransactionType.BUY,
                    date=datetime.date.today(),
                    quantity=1.0,
                    unit_price=tutar,
                    commission=0,
                    tax=0,
                    note="Excel Import - Tutar (Toplu)"
                )
                transactions.append(tx)
                
        if transactions:
            session.add_all(transactions)
        session.commit()
        return True

import pandas as pd
import datetime
from sqlalchemy.orm import Session
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, TransactionType
from app.utils.logger import app_logger

class ImportExportService:
    @staticmethod
    def export_excel(session: Session, file_path: str):
        """Tüm portföyü Excel'e dışa aktarır."""
        # Portföy durumu (TODO: Güncel fiyatlar eklenecek)
        assets = session.query(Asset).all()
        asset_data = []
        for a in assets:
            asset_data.append({
                "Kod": a.code,
                "Ad": a.name,
                "Tür": a.asset_type.name,
                "Para Birimi": a.currency
            })
            
        # İşlemler
        txs = session.query(Transaction).all()
        tx_data = []
        for tx in txs:
            tx_data.append({
                "Tarih": tx.date,
                "Varlık Kodu": tx.asset.code,
                "İşlem Türü": tx.transaction_type.name,
                "Adet": float(tx.quantity),
                "Birim Fiyat": float(tx.unit_price),
                "Komisyon": float(tx.commission),
                "Vergi": float(tx.tax),
                "Not": tx.note
            })

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            pd.DataFrame(asset_data).to_excel(writer, sheet_name='Varlıklar', index=False)
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
                
                # Senaryo 1: Yüzdelik (Henüz Tam Aktif Değil)
                elif any("kod" in c for c in cols) and any("yüzde" in c for c in cols):
                    # TODO: Yüzdelik portföy aktarımı.
                    continue
                    
            if not success_any:
                app_logger.error("Uygun sütun formatı hiçbir sayfada bulunamadı.")
                return False
                
            return True
                
        except Exception as e:
            app_logger.error(f"Import error: {e}")
            return False


    @staticmethod
    def _ensure_assets_exist(session: Session, codes_and_names: dict) -> dict:
        """
        Bulk ensures assets exist.
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
            codes_and_names[code] = code  # default name to code
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
                except:
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

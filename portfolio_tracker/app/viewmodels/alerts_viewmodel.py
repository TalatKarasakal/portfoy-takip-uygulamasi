import datetime
from typing import Dict, List

from PySide6.QtCore import QObject, Signal
from sqlalchemy.orm import joinedload

from app.database.session import get_session
from app.models.alert import Alert, AlertType
from app.models.asset import Asset
from app.utils.logger import app_logger

ALERT_TYPE_LABELS = {
    AlertType.PRICE_ABOVE: "Fiyat şunun üstüne çıkarsa",
    AlertType.PRICE_BELOW: "Fiyat şunun altına inerse",
    AlertType.PCT_CHANGE_ABOVE: "Günlük değişim % üstüne çıkarsa",
    AlertType.PCT_CHANGE_BELOW: "Günlük değişim % altına inerse",
}


class AlertsViewModel(QObject):
    alerts_loaded = Signal(list)
    alert_triggered = Signal(str, str)  # (asset_code, mesaj)
    error_occurred = Signal(str)

    def load_alerts(self):
        try:
            with get_session() as session:
                alerts = (
                    session.query(Alert)
                    .options(joinedload(Alert.asset))
                    .order_by(Alert.created_at.desc())
                    .all()
                )
                result = []
                for a in alerts:
                    result.append({
                        "id": a.id,
                        "asset_id": a.asset_id,
                        "asset_code": a.asset.code if a.asset else "?",
                        "type": a.alert_type,
                        "type_label": ALERT_TYPE_LABELS.get(a.alert_type, a.alert_type.name),
                        "threshold": float(a.threshold),
                        "is_active": bool(a.is_active),
                        "triggered_at": a.triggered_at.strftime("%Y-%m-%d %H:%M") if a.triggered_at else None,
                    })
                self.alerts_loaded.emit(result)
        except Exception as e:
            app_logger.error(f"Uyarılar yüklenemedi: {e}")
            self.error_occurred.emit(str(e))

    def add_alert(self, asset_id: int, alert_type: str, threshold: float):
        try:
            with get_session() as session:
                alert = Alert(
                    asset_id=asset_id,
                    alert_type=AlertType[alert_type],
                    threshold=threshold,
                    is_active=True,
                )
                session.add(alert)
                session.commit()
            self.load_alerts()
        except Exception as e:
            app_logger.error(f"Uyarı eklenemedi: {e}")
            self.error_occurred.emit(str(e))

    def delete_alert(self, alert_id: int):
        try:
            with get_session() as session:
                alert = session.query(Alert).filter_by(id=alert_id).first()
                if alert:
                    session.delete(alert)
                    session.commit()
            self.load_alerts()
        except Exception as e:
            app_logger.error(f"Uyarı silinemedi: {e}")
            self.error_occurred.emit(str(e))

    def set_active(self, alert_id: int, active: bool):
        try:
            with get_session() as session:
                alert = session.query(Alert).filter_by(id=alert_id).first()
                if alert:
                    alert.is_active = active
                    # Yeniden aktive edilince tekrar tetiklenebilsin
                    if active:
                        alert.triggered_at = None
                    session.commit()
            self.load_alerts()
        except Exception as e:
            app_logger.error(f"Uyarı güncellenemedi: {e}")
            self.error_occurred.emit(str(e))

    def get_available_assets(self) -> List[Dict]:
        try:
            with get_session() as session:
                return [{"id": a.id, "code": a.code} for a in session.query(Asset).all()]
        except Exception as e:
            app_logger.error(f"Varlık listesi alınamadı: {e}")
            return []

    def check_alerts(self, price_map: Dict[int, Dict[str, float]], notifications_enabled: bool = True):
        """Aktif ve henüz tetiklenmemiş uyarıları güncel fiyatlara göre değerlendirir.

        Args:
            price_map: {asset_id: {"price": float, "pct": float}}
            notifications_enabled: OS bildirimi gönderilip gönderilmeyeceği.
        """
        try:
            triggered_any = False
            with get_session() as session:
                alerts = (
                    session.query(Alert)
                    .options(joinedload(Alert.asset))
                    .filter(Alert.is_active.is_(True), Alert.triggered_at.is_(None))
                    .all()
                )
                for a in alerts:
                    info = price_map.get(a.asset_id)
                    if not info:
                        continue
                    price = info.get("price", 0.0)
                    pct = info.get("pct", 0.0)
                    threshold = float(a.threshold)
                    hit = False
                    if a.alert_type == AlertType.PRICE_ABOVE and price >= threshold:
                        hit = True
                    elif a.alert_type == AlertType.PRICE_BELOW and price <= threshold:
                        hit = True
                    elif a.alert_type == AlertType.PCT_CHANGE_ABOVE and pct >= threshold:
                        hit = True
                    elif a.alert_type == AlertType.PCT_CHANGE_BELOW and pct <= threshold:
                        hit = True

                    if hit:
                        a.triggered_at = datetime.datetime.now()
                        code = a.asset.code if a.asset else "?"
                        msg = f"{ALERT_TYPE_LABELS.get(a.alert_type)} ({threshold})"
                        triggered_any = True
                        self.alert_triggered.emit(code, msg)
                        if notifications_enabled:
                            self._notify(code, msg)
                session.commit()
            if triggered_any:
                self.load_alerts()
        except Exception as e:
            app_logger.error(f"Uyarı kontrolü hatası: {e}")

    @staticmethod
    def _notify(title: str, message: str):
        """OS native bildirimi gönderir (plyer yoksa sessizce loglar)."""
        try:
            from plyer import notification
            notification.notify(title=f"Portföy Uyarısı: {title}", message=message, timeout=10)
        except Exception as e:  # plyer kurulu değil veya platform desteklemiyor
            app_logger.info(f"Bildirim gönderilemedi ({title}: {message}) - {e}")

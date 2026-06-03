"""Test ortamı ortak ayarları.

SQLAlchemy ilişkileri (relationship) string adlarla tanımlandığından, mapper'lar
yapılandırılmadan önce ilgili tüm model sınıflarının içe aktarılmış olması
gerekir. Aksi halde yalnızca bir modeli içe aktaran testler 'failed to locate a
name' hatası alır. Bu conftest, tüm modelleri içe aktararak mapper kayıt
sorununu giderir.
"""

# Tüm modelleri içe aktararak SQLAlchemy mapper'larının tam yapılandırılmasını sağla
import app.models.alert  # noqa: F401
import app.models.asset  # noqa: F401
import app.models.portfolio_snapshot  # noqa: F401
import app.models.price_history  # noqa: F401
import app.models.settings  # noqa: F401
import app.models.transaction  # noqa: F401

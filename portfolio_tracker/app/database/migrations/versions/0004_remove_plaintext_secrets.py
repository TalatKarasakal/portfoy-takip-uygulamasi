"""SQLite ayarlarından eski düz metin bulut anahtarlarını kaldırır."""

from alembic import op

revision = "0004_remove_secrets"
down_revision = "0003_import_batches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Anahtar güvenli kasaya otomatik taşınmaz: migration yedeğinin de sırrı
    # içermemesi için eski kayıt silinir ve kullanıcıdan yeniden girmesi istenir.
    op.execute("DELETE FROM settings WHERE key = 'ai_gemini_api_key'")


def downgrade() -> None:
    # Güvenli kasadaki sır hiçbir zaman SQLite'a geri yazılmaz.
    pass

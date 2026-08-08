"""Mevcut tek portföylü şemanın Alembic başlangıç sürümü."""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("asset_type", sa.Enum("BIST", "TEFAS", name="assettype"), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="TRY"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_assets_id", "assets", ["id"])
    op.create_index("ix_assets_code", "assets", ["code"], unique=True)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column(
            "transaction_type",
            sa.Enum("BUY", "SELL", "DIVIDEND", "SPLIT", name="transactiontype"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("commission", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("tax", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("note", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_transactions_id", "transactions", ["id"])

    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("close_price", sa.Numeric(18, 6), nullable=False),
        sa.UniqueConstraint("asset_id", "date", name="uq_asset_date"),
    )
    op.create_index("ix_price_history_id", "price_history", ["id"])

    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False, unique=True),
        sa.Column("total_value_try", sa.Numeric(18, 6), nullable=False),
        sa.Column("total_value_usd", sa.Numeric(18, 6), nullable=False),
        sa.Column("total_cost_try", sa.Numeric(18, 6), nullable=False),
        sa.Column("unrealized_pnl_try", sa.Numeric(18, 6), nullable=False),
    )
    op.create_index("ix_portfolio_snapshots_id", "portfolio_snapshots", ["id"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column(
            "alert_type",
            sa.Enum(
                "PRICE_ABOVE",
                "PRICE_BELOW",
                "PCT_CHANGE_ABOVE",
                "PCT_CHANGE_BELOW",
                name="alerttype",
            ),
            nullable=False,
        ),
        sa.Column("threshold", sa.Numeric(18, 6), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("triggered_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_alerts_id", "alerts", ["id"])

    op.create_table(
        "settings",
        sa.Column("key", sa.String(50), primary_key=True),
        sa.Column("value", sa.String(255)),
    )
    op.create_index("ix_settings_key", "settings", ["key"])


def downgrade() -> None:
    for table in (
        "alerts",
        "portfolio_snapshots",
        "price_history",
        "transactions",
        "settings",
        "assets",
    ):
        op.drop_table(table)

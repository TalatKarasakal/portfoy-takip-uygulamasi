"""Çoklu portföy, nakit defteri ve izleme listesi."""

from datetime import date, timedelta
from decimal import Decimal

import sqlalchemy as sa
from alembic import op

revision = "0002_portfolios_cash"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _infer_opening_cash(connection) -> None:
    rows = connection.execute(
        sa.text(
            """
            SELECT date, transaction_type, quantity, unit_price, commission, tax
            FROM transactions ORDER BY date, id
            """
        )
    ).mappings()
    balance = Decimal("0")
    minimum = Decimal("0")
    first_date = None
    for row in rows:
        tx_date = date.fromisoformat(str(row["date"])[:10])
        first_date = first_date or tx_date
        kind = str(row["transaction_type"])
        quantity = Decimal(str(row["quantity"]))
        price = Decimal(str(row["unit_price"]))
        fees = Decimal(str(row["commission"] or 0)) + Decimal(str(row["tax"] or 0))
        if kind == "BUY":
            balance -= quantity * price + fees
        elif kind in {"SELL", "DIVIDEND"}:
            balance += quantity * price - fees
        minimum = min(minimum, balance)

    if first_date is not None and minimum < 0:
        connection.execute(
            sa.text(
                """
                INSERT INTO cash_entries
                    (portfolio_id, entry_type, date, amount, note, created_at)
                VALUES (1, 'DEPOSIT', :date, :amount,
                        'Migration açılış bakiyesi', CURRENT_TIMESTAMP)
                """
            ),
            {"date": (first_date - timedelta(days=1)).isoformat(), "amount": str(-minimum)},
        )


def upgrade() -> None:
    op.create_table(
        "portfolios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_portfolios_id", "portfolios", ["id"])
    op.execute(
        "INSERT INTO portfolios (id, name, is_default, created_at) "
        "VALUES (1, 'Ana Portföy', 1, CURRENT_TIMESTAMP)"
    )

    with op.batch_alter_table("transactions") as batch:
        batch.add_column(sa.Column("portfolio_id", sa.Integer(), nullable=False, server_default="1"))
        batch.create_foreign_key("fk_transactions_portfolio", "portfolios", ["portfolio_id"], ["id"])
        batch.create_index(
            "ix_transactions_portfolio_asset_date_id",
            ["portfolio_id", "asset_id", "date", "id"],
        )
        batch.create_index("ix_transactions_portfolio_date_id", ["portfolio_id", "date", "id"])

    # Eski date UNIQUE kısıtı sürümsüz veritabanlarında isimsizdir. SQLite'ta
    # güvenilir biçimde kaldırmak için tabloyu açıkça yeniden kuruyoruz.
    op.create_table(
        "portfolio_snapshots_v2",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("total_value_try", sa.Numeric(18, 6), nullable=False),
        sa.Column("total_value_usd", sa.Numeric(18, 6), nullable=False),
        sa.Column("total_cost_try", sa.Numeric(18, 6), nullable=False),
        sa.Column("unrealized_pnl_try", sa.Numeric(18, 6), nullable=False),
        sa.Column("cash_balance_try", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("net_external_flow_try", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("calculation_version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("portfolio_id", "date", name="uq_snapshot_portfolio_date"),
    )
    op.execute(
        """
        INSERT INTO portfolio_snapshots_v2
            (id, portfolio_id, date, total_value_try, total_value_usd,
             total_cost_try, unrealized_pnl_try, cash_balance_try,
             net_external_flow_try, calculation_version)
        SELECT id, 1, date, total_value_try, total_value_usd,
               total_cost_try, unrealized_pnl_try, 0, 0, 1
        FROM portfolio_snapshots
        """
    )
    op.drop_index("ix_portfolio_snapshots_id", table_name="portfolio_snapshots")
    op.drop_table("portfolio_snapshots")
    op.rename_table("portfolio_snapshots_v2", "portfolio_snapshots")
    op.create_index("ix_portfolio_snapshots_id", "portfolio_snapshots", ["id"])

    op.create_table(
        "cash_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id"), nullable=False),
        sa.Column(
            "entry_type",
            sa.Enum("DEPOSIT", "WITHDRAWAL", "ADJUSTMENT", name="cashentrytype"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("note", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cash_entries_id", "cash_entries", ["id"])
    op.create_index("ix_cash_entries_portfolio_id", "cash_entries", ["portfolio_id"])

    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id"), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("target_price", sa.Numeric(18, 6)),
        sa.Column("note", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("portfolio_id", "asset_id", name="uq_watchlist_portfolio_asset"),
    )
    op.create_index("ix_watchlist_items_id", "watchlist_items", ["id"])
    op.create_index("ix_watchlist_items_portfolio_id", "watchlist_items", ["portfolio_id"])
    op.create_index("ix_watchlist_items_asset_id", "watchlist_items", ["asset_id"])

    with op.batch_alter_table("settings") as batch:
        batch.alter_column("value", existing_type=sa.String(255), type_=sa.Text())

    _infer_opening_cash(op.get_bind())


def downgrade() -> None:
    op.drop_table("watchlist_items")
    op.drop_table("cash_entries")
    with op.batch_alter_table("portfolio_snapshots") as batch:
        batch.drop_constraint("uq_snapshot_portfolio_date", type_="unique")
        batch.drop_column("calculation_version")
        batch.drop_column("net_external_flow_try")
        batch.drop_column("cash_balance_try")
        batch.drop_column("portfolio_id")
        batch.create_unique_constraint("uq_portfolio_snapshots_date", ["date"])
    with op.batch_alter_table("transactions") as batch:
        batch.drop_index("ix_transactions_portfolio_date_id")
        batch.drop_index("ix_transactions_portfolio_asset_date_id")
        batch.drop_constraint("fk_transactions_portfolio", type_="foreignkey")
        batch.drop_column("portfolio_id")
    op.drop_table("portfolios")

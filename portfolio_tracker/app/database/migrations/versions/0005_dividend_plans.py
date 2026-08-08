"""Temettü planlarını ve bağlı ödeme işlemlerini ekler."""

import sqlalchemy as sa
from alembic import op

revision = "0005_dividend_plans"
down_revision = "0004_remove_secrets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dividend_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id"), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("gross_per_share", sa.Numeric(18, 6), nullable=False),
        sa.Column("expected_quantity", sa.Numeric(18, 6)),
        sa.Column(
            "status",
            sa.Enum("PLANNED", "PAID", "CANCELLED", name="dividendplanstatus"),
            nullable=False,
            server_default="PLANNED",
        ),
        sa.Column("linked_transaction_id", sa.Integer(), sa.ForeignKey("transactions.id")),
        sa.Column("import_batch_id", sa.Integer(), sa.ForeignKey("import_batches.id")),
        sa.Column("note", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("linked_transaction_id", name="uq_dividend_plan_transaction"),
    )
    op.create_index("ix_dividend_plans_id", "dividend_plans", ["id"])
    op.create_index("ix_dividend_plans_portfolio_id", "dividend_plans", ["portfolio_id"])
    op.create_index("ix_dividend_plans_asset_id", "dividend_plans", ["asset_id"])
    op.create_index("ix_dividend_plans_payment_date", "dividend_plans", ["payment_date"])
    op.create_index("ix_dividend_plans_import_batch_id", "dividend_plans", ["import_batch_id"])


def downgrade() -> None:
    op.drop_table("dividend_plans")

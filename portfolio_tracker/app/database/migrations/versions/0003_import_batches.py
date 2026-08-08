"""İçe aktarım batch bağlantıları ve tek adımlı geri alma."""

import sqlalchemy as sa
from alembic import op

revision = "0003_import_batches"
down_revision = "0002_portfolios_cash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id")),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="EXCEL"),
        sa.Column(
            "status",
            sa.Enum("APPLIED", "UNDONE", name="importbatchstatus"),
            nullable=False,
            server_default="APPLIED",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("undone_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_import_batches_id", "import_batches", ["id"])
    op.create_index("ix_import_batches_portfolio_id", "import_batches", ["portfolio_id"])
    for table in ("transactions", "cash_entries", "watchlist_items"):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("import_batch_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                f"fk_{table}_import_batch",
                "import_batches",
                ["import_batch_id"],
                ["id"],
            )
            batch.create_index(f"ix_{table}_import_batch_id", ["import_batch_id"])


def downgrade() -> None:
    for table in ("watchlist_items", "cash_entries", "transactions"):
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_import_batch_id")
            batch.drop_constraint(f"fk_{table}_import_batch", type_="foreignkey")
            batch.drop_column("import_batch_id")
    op.drop_table("import_batches")

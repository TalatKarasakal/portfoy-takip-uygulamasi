CREATE TABLE assets (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    asset_type VARCHAR(10) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'TRY',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_assets_id ON assets (id);
CREATE INDEX ix_assets_code ON assets (code);

CREATE TABLE transactions (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    transaction_type VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    quantity DECIMAL(18, 6) NOT NULL,
    unit_price DECIMAL(18, 6) NOT NULL,
    commission DECIMAL(18, 6) NOT NULL DEFAULT 0,
    tax DECIMAL(18, 6) NOT NULL DEFAULT 0,
    note VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(asset_id) REFERENCES assets (id)
);
CREATE INDEX ix_transactions_id ON transactions (id);

CREATE TABLE price_history (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    date DATE NOT NULL,
    close_price DECIMAL(18, 6) NOT NULL,
    CONSTRAINT uq_asset_date UNIQUE (asset_id, date),
    FOREIGN KEY(asset_id) REFERENCES assets (id)
);
CREATE INDEX ix_price_history_id ON price_history (id);

CREATE TABLE portfolio_snapshots (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,
    total_value_try DECIMAL(18, 6) NOT NULL,
    total_value_usd DECIMAL(18, 6) NOT NULL,
    total_cost_try DECIMAL(18, 6) NOT NULL,
    unrealized_pnl_try DECIMAL(18, 6) NOT NULL
);
CREATE INDEX ix_portfolio_snapshots_id ON portfolio_snapshots (id);

CREATE TABLE alerts (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    alert_type VARCHAR(20) NOT NULL,
    threshold DECIMAL(18, 6) NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    triggered_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(asset_id) REFERENCES assets (id)
);
CREATE INDEX ix_alerts_id ON alerts (id);

CREATE TABLE settings (
    `key` VARCHAR(50) NOT NULL PRIMARY KEY,
    value VARCHAR(255)
);
CREATE INDEX ix_settings_key ON settings (`key`);

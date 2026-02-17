-- ============================================
-- StockPulse v3.2 — Complete Database Schema
-- Run: psql -U stockpulse -d stockpulse -f schema.sql
-- ============================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    kite_user_id VARCHAR(50),
    kite_api_key_encrypted TEXT,
    kite_api_secret_encrypted TEXT,
    is_kite_provider BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    alerts_chat_id BIGINT,
    commands_chat_id BIGINT,
    private_chat_id BIGINT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Trades with idempotency constraint
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(10) DEFAULT 'NSE',
    quantity INTEGER NOT NULL CHECK (quantity > 0 AND quantity < 1000000),
    price DECIMAL(12,2) NOT NULL CHECK (price > 0 AND price < 10000000),
    trade_type VARCHAR(4) NOT NULL CHECK (trade_type IN ('BUY', 'SELL')),
    trade_date DATE DEFAULT CURRENT_DATE,
    source VARCHAR(20) DEFAULT 'telegram' CHECK (source IN ('telegram', 'kite_sync', 'csv_upload', 'manual')),
    telegram_message_id BIGINT,
    kite_order_id VARCHAR(50),
    notes TEXT CHECK (char_length(notes) <= 500),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_trades_user_symbol ON trades(user_id, symbol);
CREATE UNIQUE INDEX IF NOT EXISTS idx_trades_idempotent ON trades(user_id, telegram_message_id) WHERE telegram_message_id IS NOT NULL;

-- Alerts
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(10) DEFAULT 'NSE',
    lower_bound DECIMAL(12,2),
    upper_bound DECIMAL(12,2),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active','triggered_upper','triggered_lower','approaching','cancelled','cooldown')),
    triggered_at TIMESTAMP,
    triggered_price DECIMAL(12,2),
    trigger_count INTEGER DEFAULT 0,
    last_triggered_at TIMESTAMP,
    cooldown_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    CHECK (lower_bound IS NOT NULL OR upper_bound IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(status) WHERE status = 'active';

-- Kite sessions
CREATE TABLE IF NOT EXISTS kite_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    access_token_encrypted TEXT NOT NULL,
    token_expiry TIMESTAMP,
    last_login_at TIMESTAMP DEFAULT NOW()
);

-- Conversation context (with memory support)
CREATE TABLE IF NOT EXISTS conversation_context (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL CHECK (char_length(message) <= 2000),
    role VARCHAR(10) NOT NULL CHECK (role IN ('user', 'bot')),
    parsed_intent JSONB,
    bot_response_summary TEXT CHECK (char_length(bot_response_summary) <= 500),
    telegram_message_id BIGINT,
    chat_id BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_context_user_recent ON conversation_context(user_id, created_at DESC);

-- Predictions
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    target_price DECIMAL(12,2) NOT NULL,
    current_price_at_prediction DECIMAL(12,2),
    direction VARCHAR(4) CHECK (direction IN ('UP', 'DOWN')),
    predicted_probability DECIMAL(5,2),
    predicted_timeframe_min INTEGER,
    predicted_timeframe_max INTEGER,
    scenario_data JSONB,
    actual_hit BOOLEAN,
    actual_hit_date TIMESTAMP,
    actual_sessions_taken INTEGER,
    accuracy_score DECIMAL(5,2),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','hit','missed','expired','cancelled')),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_predictions_pending ON predictions(status) WHERE status = 'pending';

-- Staging data (shared market data, not user-specific)
CREATE TABLE IF NOT EXISTS staging_data (
    id SERIAL PRIMARY KEY,
    data_date DATE NOT NULL,
    data_type VARCHAR(30) NOT NULL,
    symbol VARCHAR(20) DEFAULT '_MARKET_',
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(data_date, data_type, symbol)
);

-- Daily snapshots
CREATE TABLE IF NOT EXISTS daily_snapshots (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    portfolio_value DECIMAL(14,2),
    total_pnl DECIMAL(14,2),
    day_pnl DECIMAL(14,2),
    holdings_detail JSONB,
    UNIQUE(user_id, snapshot_date)
);

-- Pattern alerts log (deduplication)
CREATE TABLE IF NOT EXISTS pattern_alerts_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    pattern_type VARCHAR(30) NOT NULL,
    alert_date DATE NOT NULL,
    detail JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, symbol, pattern_type, alert_date)
);

-- Market holidays (pre-populate for NSE 2026)
CREATE TABLE IF NOT EXISTS market_holidays (
    id SERIAL PRIMARY KEY,
    holiday_date DATE UNIQUE NOT NULL,
    description VARCHAR(200),
    exchange VARCHAR(10) DEFAULT 'NSE'
);

-- Audit log
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    details JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id, created_at DESC);

-- Holdings view (computed from trades)
CREATE OR REPLACE VIEW holdings AS
SELECT
    user_id,
    symbol,
    SUM(CASE WHEN trade_type = 'BUY' THEN quantity ELSE -quantity END) AS net_quantity,
    CASE
        WHEN SUM(CASE WHEN trade_type = 'BUY' THEN quantity ELSE 0 END) > 0
        THEN ROUND(
            SUM(CASE WHEN trade_type = 'BUY' THEN quantity * price ELSE 0 END)::NUMERIC
            / SUM(CASE WHEN trade_type = 'BUY' THEN quantity ELSE 0 END)::NUMERIC,
        2)
        ELSE 0
    END AS avg_buy_price,
    SUM(CASE WHEN trade_type = 'BUY' THEN quantity * price ELSE 0 END) AS total_invested
FROM trades
GROUP BY user_id, symbol
HAVING SUM(CASE WHEN trade_type = 'BUY' THEN quantity ELSE -quantity END) > 0;

-- ============================================
-- NSE 2026 Holidays (partial — update as needed)
-- ============================================
INSERT INTO market_holidays (holiday_date, description) VALUES
    ('2026-01-26', 'Republic Day'),
    ('2026-03-10', 'Maha Shivaratri'),
    ('2026-03-17', 'Holi'),
    ('2026-03-30', 'Id-Ul-Fitr'),
    ('2026-04-02', 'Ram Navami'),
    ('2026-04-03', 'Mahavir Jayanti'),
    ('2026-04-06', 'Good Friday'),
    ('2026-04-14', 'Dr. Ambedkar Jayanti'),
    ('2026-05-01', 'Maharashtra Day'),
    ('2026-06-06', 'Bakri Id'),
    ('2026-07-06', 'Muharram'),
    ('2026-08-15', 'Independence Day'),
    ('2026-08-26', 'Janmashtami'),
    ('2026-10-02', 'Mahatma Gandhi Jayanti'),
    ('2026-10-20', 'Dussehra'),
    ('2026-11-09', 'Diwali (Laxmi Puja)'),
    ('2026-11-10', 'Diwali Balipratipada'),
    ('2026-11-19', 'Guru Nanak Jayanti'),
    ('2026-12-25', 'Christmas')
ON CONFLICT (holiday_date) DO NOTHING;

-- ============================================
-- Cleanup function (called by WF5 EOD)
-- ============================================
CREATE OR REPLACE FUNCTION cleanup_old_data() RETURNS void AS $$
BEGIN
    DELETE FROM staging_data WHERE data_date < CURRENT_DATE - INTERVAL '7 days';
    DELETE FROM conversation_context WHERE created_at < NOW() - INTERVAL '30 days';
    DELETE FROM audit_log WHERE created_at < NOW() - INTERVAL '90 days';
    DELETE FROM predictions WHERE status != 'pending' AND created_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

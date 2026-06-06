CREATE TABLE IF NOT EXISTS settlement_records (
  id SERIAL PRIMARY KEY,
  settlement_no VARCHAR(64) UNIQUE NOT NULL,
  batch_no VARCHAR(64) NOT NULL,
  insured_id VARCHAR(32) NOT NULL,
  total_amount NUMERIC(12, 2) NOT NULL,
  reimbursed_amount NUMERIC(12, 2) NOT NULL,
  self_pay_amount NUMERIC(12, 2) NOT NULL,
  status VARCHAR(32) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settlement_items (
  id SERIAL PRIMARY KEY,
  settlement_no VARCHAR(64) NOT NULL REFERENCES settlement_records(settlement_no) ON DELETE CASCADE,
  item_code VARCHAR(32) NOT NULL,
  name VARCHAR(128) NOT NULL,
  category VARCHAR(32) NOT NULL,
  catalog_class VARCHAR(8) NOT NULL,
  unit_price NUMERIC(12, 2) NOT NULL,
  quantity NUMERIC(10, 4) NOT NULL,
  amount NUMERIC(12, 2) NOT NULL,
  self_pay_ratio NUMERIC(5, 4) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_settlement_items_settlement_no ON settlement_items(settlement_no);

CREATE TABLE IF NOT EXISTS audit_logs (
  id SERIAL PRIMARY KEY,
  client_id VARCHAR(64) NOT NULL,
  path VARCHAR(255) NOT NULL,
  action VARCHAR(64) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

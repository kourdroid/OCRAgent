-- ============================================================
-- 003_erp_tables.sql
-- ERP Master Data tables for 3-Way Match reconciliation
-- Run against live Supabase after 002_add_multi_layout_support.sql
-- ============================================================

-- 1. Purchase Orders (header)
CREATE TABLE IF NOT EXISTS erp_purchase_orders (
    po_number VARCHAR(100) PRIMARY KEY,
    vendor_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'OPEN'
);

-- 2. PO Line Items (what the client ordered)
CREATE TABLE IF NOT EXISTS erp_po_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    po_number VARCHAR(100) REFERENCES erp_purchase_orders(po_number),
    item_description TEXT,
    expected_qty NUMERIC(10, 2),
    expected_unit_price NUMERIC(10, 2)
);

-- 3. Goods Receipts (what the warehouse actually received)
CREATE TABLE IF NOT EXISTS erp_goods_receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    po_number VARCHAR(100) REFERENCES erp_purchase_orders(po_number),
    item_description TEXT,
    actual_received_qty NUMERIC(10, 2)
);

-- ============================================================
-- SEED: LABEL TECH test data
-- Intentional QUANTITY_SHORTAGE on the A3 item (40 received vs 44 ordered)
-- ============================================================

INSERT INTO erp_purchase_orders (po_number, vendor_name)
VALUES ('CO2109-0171', 'LABEL TECH')
ON CONFLICT (po_number) DO NOTHING;

INSERT INTO erp_po_lines (po_number, item_description, expected_qty, expected_unit_price) VALUES
('CO2109-0171', 'P_PA3-0001 Pictogramme Adhésif A3.', 44, 11.67),
('CO2109-0171', 'P_PA4-0002 Pictogramme Adhésif A4.', 23, 7.50)
ON CONFLICT DO NOTHING;

INSERT INTO erp_goods_receipts (po_number, item_description, actual_received_qty) VALUES
('CO2109-0171', 'P_PA3-0001 Pictogramme Adhésif A3.', 40),
('CO2109-0171', 'P_PA4-0002 Pictogramme Adhésif A4.', 23)
ON CONFLICT DO NOTHING;

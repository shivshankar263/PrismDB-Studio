-- Export: test_export_safety | Collection: dummy | Wed Feb 18 14:58:02 2026
BEGIN;

-- Table: dummy
CREATE TABLE IF NOT EXISTS "dummy" (
    "item" TEXT,
    "price" BIGINT
);
INSERT INTO "dummy" ("item", "price") VALUES
('A', '10'),
('B', '20'),
('C', '30') ON CONFLICT DO NOTHING;

COMMIT;

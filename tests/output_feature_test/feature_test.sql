-- Export: test_export_features | Collection: feature_test | Thu Feb 19 11:54:18 2026
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
BEGIN;

-- Table: feature_test
CREATE TABLE IF NOT EXISTS "feature_test" (
    "id" SERIAL PRIMARY KEY,
    "item" TEXT,
    "details" JSONB,
    "tags" JSONB
);
INSERT INTO "feature_test" ("id", "item", "details", "tags") VALUES
(1, 'Item A', '{"color": "red", "size": 10}', '["a", "b"]'),
(2, 'Item B', '{"color": "blue", "size": 20}', '["c"]') ON CONFLICT DO NOTHING;

COMMIT;

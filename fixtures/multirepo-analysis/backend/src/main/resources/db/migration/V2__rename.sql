ALTER TABLE exposure RENAME COLUMN old_decline TO decline;
ALTER TABLE exposure DROP COLUMN obsolete;

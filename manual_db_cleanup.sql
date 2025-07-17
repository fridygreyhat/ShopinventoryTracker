
-- Manual database cleanup commands
-- Run these in psql or your PostgreSQL client

-- Connect to postgres database first
\c postgres

-- Terminate all connections to inventory_db
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'inventory_db' AND pid <> pg_backend_pid();

-- Drop the database completely
DROP DATABASE IF EXISTS inventory_db;

-- Recreate the database
CREATE DATABASE inventory_db;

-- Grant privileges (replace 'postgres' with your username if different)
GRANT ALL PRIVILEGES ON DATABASE inventory_db TO postgres;

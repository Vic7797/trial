#!/bin/bash
set -e

# Create databases if they don't exist
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
    -- Create databases if they don't exist
    SELECT 'CREATE DATABASE keycloak' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak');
    SELECT 'CREATE DATABASE customer_support' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'customer_support');
EOSQL

# Create extensions in customer_support database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname customer_support <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";
    CREATE EXTENSION IF NOT EXISTS "hstore";
EOSQL

echo "Database initialization completed successfully"

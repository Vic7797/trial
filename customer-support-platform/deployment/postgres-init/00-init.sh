#!/bin/bash
set -e

# Create databases
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create Keycloak database
    CREATE DATABASE keycloak;
    
    -- Create application user with password
    CREATE USER app_user WITH PASSWORD 'app_password';
    GRANT ALL PRIVILEGES ON DATABASE customer_support TO app_user;
    GRANT ALL PRIVILEGES ON DATABASE keycloak TO app_user;
    
    -- Grant privileges to the application user on the customer_support database
    \c customer_support
    GRANT ALL ON SCHEMA public TO app_user;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;
    
    -- Allow app_user to create tables in the future
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO app_user;
EOSQL

echo "PostgreSQL databases and users initialized successfully"

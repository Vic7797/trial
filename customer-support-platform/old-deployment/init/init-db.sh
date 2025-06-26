#!/bin/bash
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE customer_support;
    CREATE DATABASE keycloak;
EOSQL
# Enable extensions in customer_support DB
echo "\n-- Enabling extensions in customer_support DB"
psql -U "$POSTGRES_USER" -d customer_support <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";
    CREATE EXTENSION IF NOT EXISTS hstore;
EOSQL

#!/bin/sh
set -e

# Wait for MinIO to be ready
until (mc alias set minio http://minio:9000 minio minio123) do echo '...waiting...' && sleep 1; done

# Create buckets
mc mb -p minio/customer-uploads
mc mb -p minio/attachments
mc mb -p minio/backups

# Set bucket policies
mc anonymous set download minio/customer-uploads
mc anonymous set download minio/attachments

# Create service account for application
mc admin user svcacct add \
    --access-key "app_minio_key" \
    --secret-key "app_minio_secret" \
    minio minio

# Set policies for service account
mc admin policy add minio readwrite customer-uploads,attachments,backups
mc admin policy set minio readwrite user="app_minio_key"

echo "MinIO initialization completed"

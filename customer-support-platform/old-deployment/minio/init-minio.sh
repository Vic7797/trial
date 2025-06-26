#!/bin/sh
set -e

# Wait for MinIO to be ready
until (mc alias set minio http://minio:9000 minioadmin minioadmin) do sleep 1; done

# Create buckets if they don't exist
for bucket in documents uploads; do
    mc mb minio/$bucket --ignore-existing
    mc policy set public minio/$bucket
    echo "Bucket $bucket is ready"
done

echo "MinIO initialization completed successfully"

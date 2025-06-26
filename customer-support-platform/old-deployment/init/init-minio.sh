#!/bin/bash
set -e
mc alias set local http://minio:9000 minioadmin minioadmin
mc mb -p local/documents
mc policy set public local/documents

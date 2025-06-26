#!/bin/bash
set -e

if [ "$SERVICE" = "worker" ]; then
    echo "Starting Celery worker..."
    exec celery -A app.worker:celery_app worker --loglevel=info
elif [ "$SERVICE" = "beat" ]; then
    echo "Starting Celery beat..."
    exec celery -A app.worker:celery_app beat --loglevel=info
else
    echo "Starting FastAPI app..."
    exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload
fi

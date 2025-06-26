"""Sentry integration for error tracking and monitoring."""
from typing import Optional
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging

from app.config import settings


def init_sentry() -> None:
    """Initialize Sentry SDK with all integrations."""
    if not settings.SENTRY_DSN:
        return

    # Configure logging integration
    logging_integration = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )

    # Initialize Sentry SDK
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
        send_default_pii=settings.SENTRY_SEND_DEFAULT_PII,
        max_breadcrumbs=settings.SENTRY_MAX_BREADCRUMBS,
        attach_stacktrace=settings.SENTRY_ATTACH_STACKTRACE,
        request_bodies=settings.SENTRY_REQUEST_BODIES,
        
        # Enable all relevant integrations
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
            CeleryIntegration(),
            logging_integration
        ],
        
        # Configure additional settings
        before_send=before_send,
        before_breadcrumb=before_breadcrumb
    )


def before_send(event: dict, hint: Optional[dict]) -> Optional[dict]:
    """Filter and modify events before sending to Sentry."""
    # Don't send events from development/testing
    if settings.ENV in ['development', 'testing']:
        return None

    # Filter out sensitive information
    if 'request' in event and 'headers' in event['request']:
        # Remove sensitive headers
        sensitive_headers = ['authorization', 'cookie', 'x-api-key']
        event['request']['headers'] = {
            k: v for k, v in event['request']['headers'].items()
            if k.lower() not in sensitive_headers
        }

    return event


def before_breadcrumb(crumb: Optional[dict], hint: Optional[dict]) -> Optional[dict]:
    """Filter and modify breadcrumbs before adding them to the event."""
    if not crumb:
        return None

    # Filter out noise from breadcrumbs
    if crumb.get('category') == 'httplib':
        return None

    # Don't record SQL queries in breadcrumbs
    if crumb.get('category') == 'query':
        return None

    return crumb

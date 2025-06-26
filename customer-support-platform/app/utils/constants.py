# Cache timeouts (in seconds)
USER_CACHE_TIMEOUT = 3600  # 1 hour
TICKET_CACHE_TIMEOUT = 1800  # 30 minutes
CATEGORY_CACHE_TIMEOUT = 7200  # 2 hours
DOCUMENT_CACHE_TIMEOUT = 3600  # 1 hour

# Rate limits
API_RATE_LIMIT = 100  # requests per minute
AUTH_RATE_LIMIT = 5  # requests per minute

# File limitations
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = [
    "text/plain",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
]

# Pagination defaults
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100

# Queue names
CLASSIFICATION_QUEUE = "classification"
PROCESSING_QUEUE = "processing"
NOTIFICATION_QUEUE = "notifications"
ANALYTICS_QUEUE = "analytics"

# Dead letter exchange
DLX_EXCHANGE = "dlx"
DLX_QUEUE = "dead_letters"

# Redis key prefixes
USER_CACHE_PREFIX = "user:"
TICKET_CACHE_PREFIX = "ticket:"
CATEGORY_CACHE_PREFIX = "category:"
DOCUMENT_CACHE_PREFIX = "document:"
TOKEN_CACHE_PREFIX = "token:"

# MinIO bucket names
DOCUMENT_BUCKET = "documents"
AVATAR_BUCKET = "avatars"

# Task retry settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
RETRY_BACKOFF = 2  # exponential backoff multiplier
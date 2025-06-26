import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote_plus
from app.core.logging import logger
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import hvac

@lru_cache(maxsize=1)  # Cache the secrets loading
def load_secrets() -> Dict[str, Any]:
    """Load secrets from Vault with proper error handling and fallback."""
    vault_addr = os.getenv("VAULT_ADDR")
    vault_token = os.getenv("VAULT_TOKEN") or os.getenv("VAULT_DEV_ROOT_TOKEN")
    
    if not vault_addr or not vault_token:
        logger.warning("Vault credentials not found, falling back to environment variables")
        return {}
    
    try:
        client = hvac.Client(
            url=vault_addr,
            token=vault_token,
            timeout=10
        )
        
        # Verify Vault connection
        if not client.is_authenticated():
            logger.error("Failed to authenticate with Vault")
            return {}
        
        response = client.secrets.kv.v2.read_secret_version(
            mount_point="secret",
            path="app/config"
        )
        logger.info("Successfully loaded secrets from Vault")
        return response["data"]["data"]
        
    except Exception as e:
        logger.error(f"Error loading secrets from Vault: {e}")
        return {}

class Settings(BaseSettings):
    """Application settings with Vault integration and environment fallback."""
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        extra="ignore",
        case_sensitive=True
    )

    def __init__(self, **kwargs):
        # Load secrets from Vault first
        self._vault_secrets = load_secrets()
        super().__init__(**kwargs)

    def _get_secret(self, key: str, default: Any = None, env_key: str = None) -> Any:
        """Get value from Vault secrets first, then environment, then default."""
        # Try Vault first
        if self._vault_secrets and key in self._vault_secrets:
            return self._vault_secrets[key]
        
        # Try environment variable (use env_key if provided, otherwise use key)
        env_value = os.getenv(env_key or key)
        if env_value is not None:
            return env_value
            
        # Return default
        return default

    # Server Settings
    @property
    def SERVER_HOST(self) -> str:
        return self._get_secret("SERVER_HOST", "0.0.0.0")
    
    @property
    def SERVER_PORT(self) -> int:
        return int(self._get_secret("SERVER_PORT", 8000))
    
    @property
    def WORKERS_COUNT(self) -> int:
        return int(self._get_secret("WORKERS_COUNT", 4))
    
    @property
    def RELOAD(self) -> bool:
        return str(self._get_secret("RELOAD", "True")).lower() in ("true", "1", "yes")

    # API Information
    API_V1_PREFIX: str = Field(default="/api/v1")
    PROJECT_NAME: str = Field(default="Customer Support Platform")
    VERSION: str = Field(default="1.0.0")
    DESCRIPTION: str = Field(
        default=(
            "🚀 Customer Support Platform API with AI-powered "
            "ticket management and analytics."
        ),
    )

    # Environment
    @property
    def ENV(self) -> str:
        return self._get_secret("ENV", "development")
    
    @property
    def DEBUG(self) -> bool:
        return str(self._get_secret("DEBUG", "True")).lower() in ("true", "1", "yes")
    
    TESTING: bool = False

    # Security - These should come from Vault in production
    @property
    def SECRET_KEY(self) -> str:
        return self._get_secret("SECRET_KEY", "your-super-secret-key-here")
    
    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        return int(self._get_secret("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    
    @property
    def ALGORITHM(self) -> str:
        return self._get_secret("ALGORITHM", "HS256")

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://localhost:8000"
    ]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]

    # AI Configuration
    @property
    def LLM_PROVIDER(self) -> str:
        return self._get_secret("LLM_PROVIDER", "openai")
    
    @property
    def LLM_MODEL(self) -> str:
        return self._get_secret("LLM_MODEL", "gpt-3.5-turbo")
    
    @property
    def EMBEDDING_MODEL(self) -> str:
        return self._get_secret("EMBEDDING_MODEL", "text-embedding-3-small")
    
    @property
    def OPENAI_API_KEY(self) -> str:
        return self._get_secret("OPENAI_API_KEY", "")
    
    @property
    def GROQ_API_KEY(self) -> str:
        return self._get_secret("GROQ_API_KEY", "")

    # Vector Database - ChromaDB Configuration
    @property
    def CHROMA_DB_HOST(self) -> str:
        return self._get_secret("CHROMA_DB_HOST", "localhost")
    
    @property
    def CHROMA_DB_PORT(self) -> int:
        return int(self._get_secret("CHROMA_DB_PORT", 8000))
    
    @property
    def CHROMA_DB_SSL(self) -> bool:
        return str(self._get_secret("CHROMA_DB_SSL", "False")).lower() in ("true", "1", "yes")
    
    CHROMA_DB_PATH: str = "./chroma_db"

    # Enhanced Reranking Configuration
    @property
    def RERANKER_MODEL(self) -> str:
        return self._get_secret("RERANKER_MODEL", "ms-marco-MultiBEF-v2.1")
    
    @property
    def TOP_K_RESULTS(self) -> int:
        return int(self._get_secret("TOP_K_RESULTS", 3))

    # Temperature Settings for AI Responses
    @property
    def DEFAULT_TEMPERATURE(self) -> float:
        return float(self._get_secret("DEFAULT_TEMPERATURE", 0.2))
    
    SOLUTION_TEMPERATURES: list[float] = [0.2, 0.5, 0.7]
    
    # Web Search Configuration
    ENABLE_WEB_SEARCH: bool = True
    MAX_WEB_RESULTS: int = 3

    # RabbitMQ Configuration
    @property
    def RABBITMQ_HOST(self) -> str:
        return self._get_secret("RABBITMQ_HOST", "localhost")
    
    @property
    def RABBITMQ_PORT(self) -> int:
        return int(self._get_secret("RABBITMQ_PORT", 5672))
    
    @property
    def RABBITMQ_USER(self) -> str:
        return self._get_secret("RABBITMQ_USER", "guest")
    
    @property
    def RABBITMQ_PASSWORD(self) -> str:
        return self._get_secret("RABBITMQ_PASSWORD", "guest")
    
    @property
    def RABBITMQ_VHOST(self) -> str:
        return self._get_secret("RABBITMQ_VHOST", "/")
    
    RABBITMQ_CONNECTION_TIMEOUT: int = 30
    RABBITMQ_HEARTBEAT: int = 60
    RABBITMQ_CONNECTION_RETRY: bool = True
    RABBITMQ_CONNECTION_MAX_RETRIES: int = 3
    RABBITMQ_CONNECTION_RETRY_DELAY: int = 5
    
    # Redis Configuration
    @property
    def REDIS_HOST(self) -> str:
        return self._get_secret("REDIS_HOST", "localhost")
    
    @property
    def REDIS_PORT(self) -> int:
        return int(self._get_secret("REDIS_PORT", 6379))
    
    @property
    def REDIS_PASSWORD(self) -> Optional[str]:
        password = self._get_secret("REDIS_PASSWORD")
        return password if password else None
    
    @property
    def REDIS_DB(self) -> int:
        return int(self._get_secret("REDIS_DB", 0))
    
    @property
    def REDIS_SSL(self) -> bool:
        return str(self._get_secret("REDIS_SSL", "False")).lower() in ("true", "1", "yes")
    
    REDIS_TIMEOUT: int = 5
    
    @property
    def REDIS_URL(self) -> str:
        """Generate Redis connection URL with password if provided."""
        password = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        protocol = "rediss" if self.REDIS_SSL else "redis"
        return f"{protocol}://{password}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # Rate Limiting Configuration
    @property
    def RATE_LIMIT_ENABLED(self) -> bool:
        return str(self._get_secret("RATE_LIMIT_ENABLED", "True")).lower() in ("true", "1", "yes")
    
    RATE_LIMIT_STORAGE_URI: Optional[str] = None
    RATE_LIMITS: Dict[str, Dict[str, int]] = {
        "default": {
            "requests": 100,
            "window_seconds": 3600
        },
        "ticket_creation": {
            "requests": 60,
            "window_seconds": 3600
        },
        "api_endpoints": {
            "requests": 50,
            "window_seconds": 300
        },
        "auth": {
            "requests": 5,
            "window_seconds": 300
        }
    }
    
    # Organization Limits
    MAX_ADMINS_PER_ORG: int = 2
    MAX_ANALYSTS_PER_ORG: int = 2
    
    # Enhanced Sentry Configuration
    @property
    def SENTRY_DSN(self) -> Optional[str]:
        return self._get_secret("SENTRY_DSN")
    
    @property
    def SENTRY_ENVIRONMENT(self) -> str:
        return self._get_secret("SENTRY_ENVIRONMENT", "development")
    
    SENTRY_TRACES_SAMPLE_RATE: float = 1.0
    SENTRY_PROFILES_SAMPLE_RATE: float = 1.0
    SENTRY_SEND_DEFAULT_PII: bool = False
    SENTRY_MAX_BREADCRUMBS: int = 100
    SENTRY_ATTACH_STACKTRACE: bool = True
    SENTRY_REQUEST_BODIES: str = "medium"

    # Enhanced Logging Configuration
    @property
    def LOG_LEVEL(self) -> str:
        return self._get_secret("LOG_LEVEL", "INFO")
    
    @property
    def LOG_FORMAT(self) -> str:
        return self._get_secret("LOG_FORMAT", "json")
    
    @property
    def LOG_FILE_PATH(self) -> str:
        return self._get_secret("LOG_FILE_PATH", "logs/app.log")
    
    @property
    def LOG_ERROR_PATH(self) -> str:
        return self._get_secret("LOG_ERROR_PATH", "logs/error.log")
    
    @property
    def LOG_ACCESS_PATH(self) -> str:
        return self._get_secret("LOG_ACCESS_PATH", "logs/access.log")
    
    LOG_ROTATION: str = "1 day"
    LOG_RETENTION: str = "30 days"
    LOG_COMPRESSION: str = "gz"
    LOG_BACKTRACE: bool = True
    LOG_DIAGNOSE: bool = True
    LOG_ENQUEUE: bool = True
    LOG_SERIALIZE: bool = True
    LOG_REQUEST_ID_HEADER: str = "X-Request-ID"

    # Plan Limits Configuration
    PLAN_LIMITS: Dict[str, Dict[str, Any]] = {
        "free": {
            "tickets_per_month": 50,
            "max_agents": 3,
            "storage_limit_mb": 100,
            "custom_categories": 5,
            "price_inr": 0
        },
        "starter": {
            "tickets_per_month": 500,
            "max_agents": 5,
            "storage_limit_mb": 500,
            "custom_categories": 15,
            "price_inr": 2000
        },
        "growth": {
            "tickets_per_month": 3000,
            "max_agents": 15,
            "storage_limit_mb": 2000,
            "custom_categories": 50,
            "price_inr": 9900
        },
        "enterprise": {
            "tickets_per_month": -1,
            "max_agents": -1,
            "storage_limit_mb": -1,
            "custom_categories": -1,
            "price_inr": -1
        }
    }

    # Enhanced Celery Configuration
    @property
    def CELERY_BROKER_URL(self) -> str:
        return self._get_secret("CELERY_BROKER_URL", self.rabbitmq_url)
    
    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return self._get_secret("CELERY_RESULT_BACKEND", self.redis_url)
    
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 3600
    CELERY_TASK_SOFT_TIME_LIMIT: int = 3300
    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = 50
    CELERY_WORKER_MAX_MEMORY_PER_CHILD: int = 400000

    CELERY_TASK_ROUTES: Dict[str, Dict[str, str]] = {
        "app.tasks.email_polling_task.*": {"queue": "polling"},
        "app.tasks.telegram_polling_task.*": {"queue": "polling"},
        "app.tasks.ticket_classification_task.*": {"queue": "classification"},
        "app.tasks.document_processing_task.*": {"queue": "processing"},
        "app.tasks.notification_task.*": {"queue": "notifications"},
        "app.tasks.analytics_task.*": {"queue": "analytics"}
    }

    CELERY_TASK_QUEUES: List[str] = [
        "default", "polling", "classification", 
        "processing", "notifications", "analytics"
    ]
    CELERY_TASK_DEFAULT_QUEUE: str = "default"
    
    # Database Configuration
    @property
    def POSTGRES_SERVER(self) -> str:
        return self._get_secret("POSTGRES_HOST", "localhost")
    
    @property
    def POSTGRES_USER(self) -> str:
        return self._get_secret("POSTGRES_USER", "postgres")
    
    @property
    def POSTGRES_PASSWORD(self) -> str:
        return self._get_secret("POSTGRES_PASSWORD", "postgres")
    
    @property
    def POSTGRES_DB(self) -> str:
        return self._get_secret("POSTGRES_DB", "customer_support")
    
    @property
    def POSTGRES_PORT(self) -> str:
        return self._get_secret("POSTGRES_PORT", "5432")
    
    @property
    def POSTGRES_SSL(self) -> bool:
        return str(self._get_secret("POSTGRES_SSL", "False")).lower() in ("true", "1", "yes")
    
    POSTGRES_POOL_SIZE: int = 20
    POSTGRES_MAX_OVERFLOW: int = 10
    POSTGRES_POOL_RECYCLE: int = 300
    POSTGRES_POOL_TIMEOUT: int = 30
    POSTGRES_ECHO: bool = False

    @property
    def POSTGRES_HOST(self) -> str:
        return self.POSTGRES_SERVER

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Generate the database URI with credentials from Vault/environment."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:"
            f"{quote_plus(self.POSTGRES_PASSWORD)}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        """Assemble Redis URL from components."""
        password_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def rabbitmq_url(self) -> str:
        """Assemble RabbitMQ URL from components."""
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{self.RABBITMQ_VHOST}"

    # Keycloak Configuration
    @property
    def KEYCLOAK_URL(self) -> str:
        return self._get_secret("KEYCLOAK_URL", "http://localhost:8080")
    
    @property
    def KEYCLOAK_REALM(self) -> str:
        return self._get_secret("KEYCLOAK_REALM", "customer-support")
    
    @property
    def KEYCLOAK_CLIENT_ID(self) -> str:
        return self._get_secret("KEYCLOAK_CLIENT_ID", "customer-support-client")
    
    @property
    def KEYCLOAK_CLIENT_SECRET(self) -> str:
        return self._get_secret("KEYCLOAK_CLIENT_SECRET", "")
    
    @property
    def KEYCLOAK_ADMIN_CLIENT_SECRET(self) -> str:
        return self._get_secret("KEYCLOAK_ADMIN_CLIENT_SECRET", "")
    
    @property
    def KEYCLOAK_CALLBACK_URI(self) -> str:
        return self._get_secret("KEYCLOAK_CALLBACK_URI", "http://localhost:8000/auth/callback")

    # Email Configuration
    @property
    def SMTP_HOST(self) -> str:
        return self._get_secret("SMTP_HOST", "smtp.gmail.com")
    
    @property
    def SMTP_PORT(self) -> int:
        return int(self._get_secret("SMTP_PORT", 587))
    
    @property
    def SMTP_USER(self) -> str:
        return self._get_secret("SMTP_USER", "")
    
    @property
    def SMTP_PASSWORD(self) -> str:
        return self._get_secret("SMTP_PASSWORD", "")
    
    @property
    def SMTP_FROM_EMAIL(self) -> str:
        return self._get_secret("SMTP_FROM_EMAIL", "support@example.com")
    
    @property
    def SMTP_FROM_NAME(self) -> str:
        return self._get_secret("SMTP_FROM_NAME", "Customer Support")
    
    @property
    def SMTP_TLS(self) -> bool:
        return str(self._get_secret("SMTP_TLS", "True")).lower() in ("true", "1", "yes")
    
    @property
    def SMTP_SSL(self) -> bool:
        return str(self._get_secret("SMTP_SSL", "False")).lower() in ("true", "1", "yes")

    # Telegram Configuration
    @property
    def TELEGRAM_BOT_TOKEN(self) -> str:
        return self._get_secret("TELEGRAM_BOT_TOKEN", "")
    
    @property
    def TELEGRAM_POLLING_TIMEOUT(self) -> int:
        return int(self._get_secret("TELEGRAM_POLLING_TIMEOUT", 30))

    # Razorpay Configuration
    @property
    def RAZORPAY_KEY_ID(self) -> str:
        return self._get_secret("RAZORPAY_KEY_ID", "")
    
    @property
    def RAZORPAY_KEY_SECRET(self) -> str:
        return self._get_secret("RAZORPAY_KEY_SECRET", "")
    
    @property
    def RAZORPAY_TEST_MODE(self) -> bool:
        return str(self._get_secret("RAZORPAY_TEST_MODE", "True")).lower() in ("true", "1", "yes")
    
    # Email Templates Configuration
    EMAIL_TEMPLATES_DIR: str = "app/templates/email"
    EMAIL_TEST_USER: str = "test@example.com"
    
    # Storage Configuration for Email Attachments
    MAX_ATTACHMENT_SIZE: int = 10 * 1024 * 1024  # 10MB

    # MinIO Configuration
    @property
    def MINIO_ENDPOINT(self) -> str:
        return self._get_secret("MINIO_ENDPOINT", "localhost:9000")
    
    @property
    def MINIO_ACCESS_KEY(self) -> str:
        return self._get_secret("MINIO_ACCESS_KEY", "minioadmin")
    
    @property
    def MINIO_SECRET_KEY(self) -> str:
        return self._get_secret("MINIO_SECRET_KEY", "minioadmin")
    
    @property
    def MINIO_SECURE(self) -> bool:
        return str(self._get_secret("MINIO_SECURE", "False")).lower() in ("true", "1", "yes")
    
    @property
    def MINIO_BUCKET_NAME(self) -> str:
        return self._get_secret("MINIO_BUCKET_NAME", "documents")
    
    @property
    def MINIO_REGION(self) -> str:
        return self._get_secret("MINIO_REGION", "us-east-1")
    
    # Document Processing
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_MIME_TYPES: List[str] = [
        "application/pdf",
        "text/plain",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    
    # Storage Paths
    STORAGE_PATH: str = "storage"
    DOCUMENT_STORAGE_PATH: str = f"{STORAGE_PATH}/documents"
    TEMP_STORAGE_PATH: str = f"{STORAGE_PATH}/temp"

# Create settings instance
settings = Settings()
from enum import Enum

class TicketStatus(str, Enum):
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class TicketSource(str, Enum):
    EMAIL = "email"
    TELEGRAM = "telegram"
    WEB = "web"
    API = "api"

class TicketCriticality(str, Enum):
    LOW = "low"
    HIGH = "high"

class UserRole(str, Enum):
    ADMIN = "admin"
    AGENT = "agent"
    ANALYST = "analyst"

class Plan(str, Enum):
    FREE = "free"
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"

class DocumentStatus(str, Enum):
    PROCESSING = "processing"
    ACTIVE = "active"
    ERROR = "error"
    DELETED = "deleted"
# Customer Support Platform

An AI-powered customer support platform with multi-channel support, automated ticket routing, and analytics.

## Features

- **Multi-Channel Support**
  - Email Integration
  - Telegram Bot Integration

- **AI-Powered Support**
  - Automatic Ticket Classification
  - AI-Assisted Response Generation
  - Document-based Knowledge Base
  - CrewAI Integration with Multiple Specialized Crews
    - Crew1: Ticket Assessment & Classification
    - Crew2: Solution Retrieval from Vector DB
    - Crew3: Response Enhancement
    - Crew4: Ticket Analysis & Summarization

- **Role-Based Access Control**
  - Admin Role
  - Agent Role
  - Analyst Role

- **Organization Management**
  - Multiple Subscription Plans
  - User Management
  - Category Management
  - Document Management

- **Analytics & Reporting**
  - Ticket Statistics
  - Agent Performance
  - Category Analysis
  - Response Time Analytics

## Tech Stack

- **Backend Framework**: FastAPI
- **Database**: PostgreSQL
- **Authentication**: Keycloak
- **Message Queue**: RabbitMQ + Celery
- **Caching & Rate Limiting**: Redis
- **Vector Database**: ChromaDB
- **Payment Integration**: Razorpay
- **Error Tracking**: Sentry
- **Storage**: MinIO

## Vault Integration

This project uses HashiCorp Vault for secure secret management. All sensitive configuration is stored in Vault and loaded at runtime.

### Setup Vault

1. Start Vault server (if not using an existing one):
   ```bash
   docker run --cap-add=IPC_LOCK -d --name=dev-vault vault
   ```

2. Initialize Vault and get the unseal keys and root token:
   ```bash
   docker exec -it dev-vault vault operator init
   ```

3. Unseal Vault using the unseal keys from the previous step:
   ```bash
   docker exec -it dev-vault vault operator unseal [UNSEAL_KEY_1]
   docker exec -it dev-vault vault operator unseal [UNSEAL_KEY_2]
   docker exec -it dev-vault vault operator unseal [UNSEAL_KEY_3]
   ```

4. Set Vault environment variables:
   ```bash
   export VAULT_ADDR='http://localhost:8200'
   export VAULT_TOKEN='your-root-token'
   ```

### Populate Vault with Secrets

1. Copy `.env.example` to `.env` and fill in your secrets
2. Run the Vault population script:
   ```bash
   python scripts/populate_vault.py
   ```

This will read all non-VAULT_* environment variables from your `.env` file and store them in Vault at the path `secret/app/config`.

### Using Secrets in the Application

Secrets are automatically loaded from Vault when the application starts. Access them through the `settings` object:

```python
from app.config import settings

# Access a secret
db_password = settings.DATABASE_PASSWORD
```

## Prerequisites

- Python 3.9+
- PostgreSQL
- Redis
- RabbitMQ
- Keycloak
- MinIO

## Subscription Plans

1. **Free Plan**
   - 50 tickets/month
   - 3 agents
   - 100MB storage
   - 5 custom categories

2. **Starter Plan** ($20/month)
   - 500 tickets/month
   - 5 agents
   - 500MB storage
   - 15 custom categories

3. **Growth Plan** ($99/month)
   - 3000 tickets/month
   - 15 agents
   - 2GB storage
   - 50 custom categories

4. **Enterprise Plan**
   - Custom limits
   - Custom pricing
   - Priority support

## Project Structure

```
customer-support-platform/
├── alembic/                  # Database migrations
├── app/
│   ├── ai/                  # AI components and crews
│   ├── api/                 # API endpoints
│   ├── core/               # Core functionality
│   ├── crud/               # Database operations
│   ├── models/             # Database models
│   ├── schemas/            # Pydantic schemas
│   ├── services/           # Business logic
│   └── tasks/              # Celery tasks
├── deployment/             # Deployment configurations
├── docs/                  # Documentation
├── scripts/               # Utility scripts
└── tests/                # Test suites
```


## Logging

- Application logs: `logs/app.log`
- Error logs: `logs/error.log`
- Access logs: `logs/access.log`

## Monitoring

- Sentry for error tracking
- Prometheus metrics endpoint: `/metrics`
- Celery Flower dashboard for task monitoring

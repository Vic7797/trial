# Customer Support Platform

An AI-powered customer support platform that automates ticket resolution using CrewAI, with seamless integration for email and Telegram support channels.

## ✨ Key Features

- **Smart Ticket Routing**: AI classifies and routes tickets based on criticality
- **Auto-Resolution**: AI resolves low-criticality tickets automatically
- **Multi-Channel Support**: Email and Telegram integration
- **Human-in-the-Loop**: Seamless handoff to human agents when needed
- **Knowledge Base**: Vector-based document storage for AI reference

## 🚀 Quick Start

1. **Prerequisites**
   - Docker & Docker Compose
   - Python 3.9+
   - Redis
   - PostgreSQL

2. **Setup**
   ```bash
   # Clone the repository
   git clone https://github.com/yourusername/customer-support-platform.git
   cd customer-support-platform
   
   # Copy environment variables
   cp .env.example .env
   
   # Start services
   docker-compose up -d
   
   # Run migrations
   alembic upgrade head
   ```

3. **Running Locally**
   ```bash
   # Start backend
   uvicorn app.main:app --reload
   
   # Start worker
   celery -A app.worker worker --loglevel=info
   ```

## 📚 Documentation

- [API Documentation](./api_documentation.md)
- [Database Schema](./database_schema.md)
- [AI Crew Setup](./ai_crew_setup.md)
- [Deployment Guide](./deployment.md)
- [Development Setup](./development_setup.md)

## 🛠 Tech Stack

- **Backend**: FastAPI
- **Database**: PostgreSQL
- **AI/ML**: CrewAI, OpenAI
- **Caching**: Redis
- **Message Queue**: Celery + RabbitMQ
- **Vector Store**: Chroma
- **Auth**: Keycloak
- **Storage**: MinIO
- **Monitoring**: Sentry

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
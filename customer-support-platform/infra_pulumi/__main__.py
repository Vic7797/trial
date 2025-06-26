import pulumi
import pulumi_docker as docker
import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Network
network = docker.Network("app-network")

# Volumes
pgdata = docker.Volume("pgdata")
redisdata = docker.Volume("redisdata")
minio_data = docker.Volume("minio_data")
chromadb_data = docker.Volume("chromadb_data")
esdata = docker.Volume("esdata")
grafana_data = docker.Volume("grafana_data")
vault_data = docker.Volume("vault_data")
pgadmin_data = docker.Volume("pgadmin_data")  # Named volume for pgAdmin

# Postgres
postgres = docker.Container(
    "postgres",
    image="postgres:16-alpine",
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    envs=[
        f"POSTGRES_USER={os.getenv('POSTGRES_USER', 'postgres')}",
        f"POSTGRES_PASSWORD={os.getenv('POSTGRES_PASSWORD', 'postgres')}",
        f"POSTGRES_DB={os.getenv('POSTGRES_DB', 'customer_support')}"
    ],
    ports=[docker.ContainerPortArgs(internal=5432, external=5432)],
    volumes=[
        docker.ContainerVolumeArgs(container_path="/var/lib/postgresql/data", volume_name=pgdata.name),
        docker.ContainerVolumeArgs(container_path="/docker-entrypoint-initdb.d", host_path="../assets/postgres-init")
    ],
    healthcheck=docker.ContainerHealthcheckArgs(
        test=["CMD-SHELL", "pg_isready -U $${POSTGRES_USER}"],
        interval="10s", timeout="5s", retries=5
    )
)

# Redis
redis = docker.Container(
    "redis",
    image="redis:7-alpine",
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    ports=[docker.ContainerPortArgs(internal=6379, external=6379)],
    volumes=[docker.ContainerVolumeArgs(container_path="/data", volume_name=redisdata.name)],
    healthcheck=docker.ContainerHealthcheckArgs(
        test=["CMD", "redis-cli", "ping"],
        interval="10s", timeout="5s", retries=5
    )
)

# RabbitMQ
rabbitmq = docker.Container(
    "rabbitmq",
    image="rabbitmq:3-management-alpine",
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    envs=["RABBITMQ_DEFAULT_USER=guest", "RABBITMQ_DEFAULT_PASS=guest"],
    ports=[
        docker.ContainerPortArgs(internal=5672, external=5672),
        docker.ContainerPortArgs(internal=15672, external=15672)
    ],
    healthcheck=docker.ContainerHealthcheckArgs(
        test=["CMD", "rabbitmqctl", "status"],
        interval="10s", timeout="5s", retries=5
    )
)

# MinIO
minio = docker.Container(
    "minio",
    image="minio/minio:latest",
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    envs=["MINIO_ROOT_USER=minio", "MINIO_ROOT_PASSWORD=minio123"],
    command=["server", "/data", "--console-address", ":9001"],
    ports=[
        docker.ContainerPortArgs(internal=9000, external=9000),
        docker.ContainerPortArgs(internal=9001, external=9001)
    ],
    volumes=[docker.ContainerVolumeArgs(container_path="/data", volume_name=minio_data.name)],
    healthcheck=docker.ContainerHealthcheckArgs(
        test=["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"],
        interval="30s", timeout="10s", retries=3
    )
)

# ChromaDB
chromadb = docker.Container(
    "chromadb",
    image="chromadb/chroma:latest",
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    ports=[docker.ContainerPortArgs(internal=8000, external=8000)],
    volumes=[docker.ContainerVolumeArgs(container_path="/chroma/chroma", volume_name=chromadb_data.name)],
    healthcheck=docker.ContainerHealthcheckArgs(
        test=["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8000/api/v2"],
        interval="30s", timeout="10s", retries=3
    )
)

# Elasticsearch
elasticsearch = docker.Container(
    "elasticsearch",
    image="docker.elastic.co/elasticsearch/elasticsearch:8.15.0",
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    envs=[
        "discovery.type=single-node",
        "ES_JAVA_OPTS=-Xms512m -Xmx512m",
        "cluster.routing.allocation.disk.threshold_enabled=false",
        "bootstrap.memory_lock=true",
        "xpack.security.enabled=false"
    ],
    ports=[docker.ContainerPortArgs(internal=9200, external=9200)],
    volumes=[docker.ContainerVolumeArgs(container_path="/usr/share/elasticsearch/data", volume_name=esdata.name)],
    healthcheck=docker.ContainerHealthcheckArgs(
        test=["CMD-SHELL", "curl -s http://localhost:9200/_cluster/health | grep -q 'yellow\\|green' || exit 1"],
        interval="30s", timeout="10s", retries=5
    )
)

# Grafana
# Mount dashboards and provisioning from assets/grafana/
grafana = docker.Container(
    "grafana",
    image="grafana/grafana:latest",
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    ports=[docker.ContainerPortArgs(internal=3000, external=3000)],
    volumes=[
        docker.ContainerVolumeArgs(container_path="/var/lib/grafana", volume_name=grafana_data.name),
        docker.ContainerVolumeArgs(container_path="/etc/grafana/provisioning", host_path="../assets/grafana/provisioning"),
        docker.ContainerVolumeArgs(container_path="/var/lib/grafana/dashboards", host_path="../assets/grafana/dashboards")
    ]
)

# Prometheus
prometheus = docker.Container(
    "prometheus",
    image="prom/prometheus:latest",
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    ports=[docker.ContainerPortArgs(internal=9090, external=9090)],
    volumes=[docker.ContainerVolumeArgs(container_path="/etc/prometheus/prometheus.yml", host_path="../assets/prometheus.yml")]
)

# Logstash
logstash = docker.Container(
    "logstash",
    image="docker.elastic.co/logstash/logstash:8.15.0",
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    ports=[
        docker.ContainerPortArgs(internal=5044, external=5044),
        docker.ContainerPortArgs(internal=5000, external=5001)
    ],
    volumes=[
        docker.ContainerVolumeArgs(container_path="/app/logs", host_path="../logs"),
        docker.ContainerVolumeArgs(container_path="/usr/share/logstash/pipeline/logstash.conf", host_path="../assets/logstash.conf")
    ]
)

# Vault
vault = docker.Container(
    "vault",
    image="vault:latest",
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    ports=[docker.ContainerPortArgs(internal=8200, external=8200)],
    envs=[
        "VAULT_DEV_ROOT_TOKEN_ID=root-token",
        "VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200"
    ],
    cap_adds=["IPC_LOCK"],
    volumes=[docker.ContainerVolumeArgs(container_path="/vault/file", volume_name=vault_data.name)]
)

# Keycloak
keycloak = docker.Container(
    "keycloak",
    image="quay.io/keycloak/keycloak:26.0",
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    command=["start-dev"],
    envs=["KEYCLOAK_ADMIN=admin", "KEYCLOAK_ADMIN_PASSWORD=admin"],
    ports=[docker.ContainerPortArgs(internal=8080, external=8080)]
)

# API
api = docker.Container(
    "api",
    image="my-api-image",  # Build with pulumi_docker.Image if needed
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    envs=[
        "ENV=development",
        f"POSTGRES_USER={os.getenv('POSTGRES_USER', 'postgres')}",
        f"POSTGRES_PASSWORD={os.getenv('POSTGRES_PASSWORD', 'postgres')}",
        f"POSTGRES_DB={os.getenv('POSTGRES_DB', 'customer_support')}",
        "POSTGRES_HOST=postgres",
        "POSTGRES_PORT=5432",
        "REDIS_HOST=redis",
        "REDIS_PORT=6379",
        "SERVER_HOST=0.0.0.0",
        "SERVER_PORT=8005",
        "CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//",
        "CELERY_RESULT_BACKEND=redis://redis:6379/0",
        "CELERY_METRICS_PORT=9809",
        "ENABLE_METRICS=true",
        "MINIO_ENDPOINT=minio:9000",
        "MINIO_ACCESS_KEY=minio",
        "MINIO_SECRET_KEY=minio123",
        "CHROMA_HOST=chromadb",
        "CHROMA_PORT=8000",
        "KEYCLOAK_URL=http://keycloak:8080"
    ],
    ports=[docker.ContainerPortArgs(internal=8005, external=8005)],
    volumes=[
        docker.ContainerVolumeArgs(
            container_path="/app/logs",
            host_path="../logs"
        ),
        docker.ContainerVolumeArgs(
            container_path="/app/storage",
            host_path="../storage"
        ),
        docker.ContainerVolumeArgs(
            container_path="/app/migrations",
            host_path="../migrations"
        )
    ]
)

# Celery Worker
celery_worker = docker.Container(
    "celery-worker",
    image="my-api-image",  # Use the same image as API
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    envs=[
        "ENV=development",
        f"POSTGRES_USER={os.getenv('POSTGRES_USER', 'postgres')}",
        f"POSTGRES_PASSWORD={os.getenv('POSTGRES_PASSWORD', 'postgres')}",
        f"POSTGRES_DB={os.getenv('POSTGRES_DB', 'customer_support')}",
        "POSTGRES_HOST=postgres",
        "POSTGRES_PORT=5432",
        "REDIS_HOST=redis",
        "REDIS_PORT=6379",
        "CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//",
        "CELERY_RESULT_BACKEND=redis://redis:6379/0",
        "CELERY_METRICS_PORT=9809",
        "ENABLE_METRICS=true",
        "MINIO_ENDPOINT=minio:9000",
        "MINIO_ACCESS_KEY=minio",
        "MINIO_SECRET_KEY=minio123",
        "CHROMA_HOST=chromadb",
        "CHROMA_PORT=8000",
        "SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://postgres:postgres@postgres:5432/customer_support"
    ],
    volumes=[
        docker.ContainerVolumeArgs(container_path="/app/logs", host_path="../logs"),
        docker.ContainerVolumeArgs(container_path="/app/storage", host_path="../storage"),
        docker.ContainerVolumeArgs(container_path="/app/migrations", host_path="../migrations")
    ],
    command=["celery", "-A", "app.tasks.celery_app", "worker", "--loglevel=info"]
)

# Flower
flower = docker.Container(
    "flower",
    image="mher/flower:latest",
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    command=["--broker=amqp://guest:guest@rabbitmq:5672//", "--port=5555"],
    ports=[docker.ContainerPortArgs(internal=5555, external=5555)]
)

# pgAdmin
pgadmin = docker.Container(
    "pgadmin",
    image="dpage/pgadmin4",
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    envs=[
        "PGADMIN_DEFAULT_EMAIL=admin@example.com",
        "PGADMIN_DEFAULT_PASSWORD=admin",
    ],
    ports=[docker.ContainerPortArgs(internal=80, external=5050)],
    volumes=[
        docker.ContainerVolumeArgs(
            container_path="/var/lib/pgadmin",
            volume_name=pgadmin_data.name
        )
    ],
    healthcheck=docker.ContainerHealthcheckArgs(
        test=["CMD", "curl", "-f", "http://localhost:80/login"],
        interval="10s",
        timeout="5s",
        retries=5
    )
)

# Kibana
kibana = docker.Container(
    "kibana",
    image="docker.elastic.co/kibana/kibana:8.10.0",
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    ports=[docker.ContainerPortArgs(internal=5601, external=5601)],
    envs=["ELASTICSEARCH_HOSTS=http://elasticsearch:9200"],
    depends_on=[docker.ContainerDependsOnArgs(name=elasticsearch.name, condition="healthy")]
)

# Outputs
pulumi.export("api_url", "http://localhost:8005")
pulumi.export("grafana_url", "http://localhost:3000")
pulumi.export("vault_url", "http://localhost:8200")
pulumi.export("postgres_url", "postgresql://postgres:postgres@localhost:5432/customer_support")
pulumi.export("pgadmin_url", "http://localhost:5050")
pulumi.export("pgadmin_creds", "admin@example.com / admin")
# Service URLs
pulumi.export("rabbitmq_management_url", "http://localhost:15672")
pulumi.export("minio_console_url", "http://localhost:9001")
pulumi.export("keycloak_admin_url", "http://localhost:8080/admin")
pulumi.export("flower_url", "http://localhost:5555")
pulumi.export("kibana_url", "http://localhost:5601")
pulumi.export("prometheus_url", "http://localhost:9090")

# Default Credentials
pulumi.export("minio_creds", "minio / minio123")
pulumi.export("rabbitmq_creds", "guest / guest")
pulumi.export("keycloak_admin_creds", "admin / admin")
pulumi.export("vault_token", "root-token")

# Database Connections
pulumi.export("redis_url", "redis://localhost:6379/0")
pulumi.export("chromadb_url", "http://localhost:8000")
pulumi.export("elasticsearch_url", "http://localhost:9200")
pulumi.export("postgres_connection_string", "postgresql://postgres:postgres@localhost:5432/customer_support")

# Health Checks
pulumi.export("health_check_endpoints", {
    "api_health": "http://localhost:8005/health",
    "prometheus_metrics": "http://localhost:9090/-/healthy",
    "elasticsearch_health": "http://localhost:9200/_cluster/health",
    "minio_health": "http://localhost:9000/minio/health/live"
})

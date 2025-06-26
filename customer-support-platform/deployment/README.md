# Deployment Configuration

This directory contains configuration files for deploying the Customer Support Platform.

## Directory Structure

- `postgres-init/`: PostgreSQL initialization scripts
- `minio/`: MinIO initialization scripts
- `elk/`: ELK Stack configuration
- `prometheus/`: Prometheus configuration
- `grafana/`: Grafana configuration

## Services Configuration

### PostgreSQL
- **Database**: `customer_support`
- **User**: `app_user` (password: `app_password`)
- **Admin User**: `postgres` (password: `postgres`)
- **Keycloak Database**: `keycloak`

### MinIO
- **Access Key**: `minio`
- **Secret Key**: `minio123`
- **Buckets**:
  - `customer-uploads`: For customer file uploads
  - `attachments`: For email attachments
  - `backups`: For system backups

### Monitoring
- **Prometheus**: Available at http://localhost:9090
- **Grafana**: Available at http://localhost:3000
  - Default credentials: admin/admin

### Logging
- **ELK Stack**:
  - Elasticsearch: http://localhost:9200
  - Kibana: http://localhost:5601
  - Logstash: Configured to process application logs

## Initial Setup

1. Start the services:
   ```bash
   docker-compose up -d
   ```

2. Access the services:
   - Application: http://localhost:8005
   - Keycloak Admin: http://localhost:8080
   - MinIO Console: http://localhost:9001
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000
   - Kibana: http://localhost:5601

## Backup and Restore

### PostgreSQL Backup
```bash
docker exec -t postgres pg_dump -U postgres customer_support > backup.sql
```

### MinIO Backup
```bash
mc mirror -w minio/customer-uploads ./backups/customer-uploads
```

## Monitoring

Grafana is pre-configured with Prometheus as a data source. Import the following dashboards:
- Node Exporter Full
- PostgreSQL Overview
- Redis Dashboard
- RabbitMQ Overview
- MinIO Cluster Dashboard

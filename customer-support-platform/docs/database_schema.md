# Database Schema

This document describes the database structure and relationships for the Customer Support Platform.

## Tables

### Organizations
Core entity representing companies using the platform.

```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(20) NOT NULL DEFAULT 'free',
    monthly_ticket_limit INTEGER NOT NULL DEFAULT 50,
    agent_limit INTEGER NOT NULL DEFAULT 3,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
```

### Users
Platform users with different roles (admin, agent, analyst).

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    last_assigned_at TIMESTAMPTZ,
    current_ticket_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
```

### Categories
Ticket categories used for classification.

```sql
CREATE TABLE categories (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    response_sla_minutes INTEGER DEFAULT 60,
    resolution_sla_minutes INTEGER DEFAULT 480,
    priority_level INTEGER DEFAULT 3,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
```

### Tickets
Support tickets created by customers.

```sql
CREATE TABLE tickets (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id),
    assigned_agent_id UUID REFERENCES users(id),
    customer_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    priority INTEGER NOT NULL,
    criticality VARCHAR(20) DEFAULT 'low',
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
```

### Messages
Conversation messages within tickets.

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    ticket_id UUID REFERENCES tickets(id) ON DELETE CASCADE,
    sender_id UUID REFERENCES users(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT false,
    is_auto_response BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL
);
```

### Documents
Knowledge base documents for AI reference.

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
```

### Document Categories
Many-to-many relationship between documents and categories.

```sql
CREATE TABLE document_categories (
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (document_id, category_id)
);
```

## Indexes

```sql
-- Performance optimizations
CREATE INDEX idx_tickets_organization_status ON tickets(organization_id, status);
CREATE INDEX idx_tickets_assigned_agent ON tickets(assigned_agent_id) WHERE assigned_agent_id IS NOT NULL;
CREATE INDEX idx_messages_ticket_created ON messages(ticket_id, created_at);
CREATE INDEX idx_users_organization_role ON users(organization_id, role);
```

## Relationships

1. **Organization** has many **Users** (1:N)
2. **Organization** has many **Tickets** (1:N)
3. **Organization** has many **Categories** (1:N)
4. **User** has many **Tickets** assigned (1:N)
5. **Category** has many **Tickets** (1:N)
6. **Ticket** has many **Messages** (1:N)
7. **Document** belongs to many **Categories** (M:N)

## Data Retention

- Tickets: 2 years
- Messages: 2 years
- Audit logs: 1 year
- Deleted records: 30 days in archive

## Backup Strategy

- Daily full backups
- Transaction log backups every 15 minutes
- 30-day retention period
- Encrypted at rest and in transit

## Maintenance

- Weekly VACUUM ANALYZE
- Monthly index rebuild
- Quarterly statistics update
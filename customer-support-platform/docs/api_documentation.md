# API Documentation

This document outlines the RESTful API endpoints for the Customer Support Platform.

## Base URL
```
https://api.yourdomain.com/v1
```

## Authentication
All endpoints require authentication using JWT tokens.

```http
Authorization: Bearer <your_jwt_token>
```

## Rate Limiting
- 100 requests per minute per user
- 1000 requests per minute per organization

## Endpoints

### Tickets

#### List Tickets
```http
GET /tickets
```

**Query Parameters**
- `status` - Filter by status (open, in_progress, resolved)
- `category` - Filter by category ID
- `priority` - Filter by priority (low, medium, high)
- `page` - Page number (default: 1)
- `limit` - Items per page (default: 20, max: 100)

**Response**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Login issues",
      "status": "open",
      "priority": "high",
      "created_at": "2023-01-01T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "pages": 1
}
```

#### Create Ticket
```http
POST /tickets
```

**Request Body**
```json
{
  "title": "Can't login to account",
  "description": "Getting invalid credentials error",
  "category_id": "category-uuid",
  "priority": "high"
}
```

### Messages

#### Send Message
```http
POST /tickets/{ticket_id}/messages
```

**Request Body**
```json
{
  "content": "Have you tried resetting your password?",
  "is_internal": false
}
```

### Categories

#### List Categories
```http
GET /categories
```

**Response**
```json
[
  {
    "id": "uuid",
    "name": "Billing",
    "description": "Billing and payment issues"
  }
]
```

## WebSocket API

### Ticket Updates
```
ws://api.yourdomain.com/ws/tickets/{ticket_id}
```

**Events**
- `ticket.updated` - Ticket status or details changed
- `message.received` - New message received

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions"
}

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

## Webhooks

### Incoming Webhook
```
POST /webhooks/incoming
```

**Headers**
- `X-Signature` - HMAC signature for verification

**Supported Events**
- `ticket.created`
- `ticket.updated`
- `message.created`

## Rate Limit Headers
- `X-RateLimit-Limit` - Request limit
- `X-RateLimit-Remaining` - Remaining requests
- `X-RateLimit-Reset` - Timestamp when limit resets
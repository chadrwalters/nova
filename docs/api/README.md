# API Documentation

## Overview

Nova's API provides endpoints for monitoring system health, managing alerts, and accessing metrics data. This documentation covers available endpoints, request/response formats, and usage examples.

## Authentication

All API requests require authentication using an API key:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.example.com/v1/health
```

## Endpoints

### Service Health

#### Get Health Status

```http
GET /v1/health
```

Returns overall system health status and component details.

**Response:**
```json
{
  "health_score": 98.5,
  "component_status": {
    "api": {
      "status": "healthy",
      "uptime_percentage": 99.9,
      "last_error": null
    },
    "database": {
      "status": "degraded",
      "uptime_percentage": 95.5,
      "last_error": "Connection timeout"
    }
  },
  "uptime_history": {
    "timestamps": ["2024-01-01T00:00:00Z", "2024-01-01T00:01:00Z"],
    "values": [100, 98.5]
  }
}
```

#### Get Component Health

```http
GET /v1/health/components/{component_id}
```

Returns detailed health information for a specific component.

**Response:**
```json
{
  "component_id": "api",
  "status": "healthy",
  "uptime_percentage": 99.9,
  "last_check": "2024-01-01T00:00:00Z",
  "metrics": {
    "response_time": 150,
    "error_rate": 0.1
  }
}
```

### Error Metrics

#### Get Error Statistics

```http
GET /v1/errors/stats
```

Returns error statistics and trends.

**Parameters:**
- `start_time`: Start of time range (ISO 8601)
- `end_time`: End of time range (ISO 8601)
- `categories`: Comma-separated list of error categories
- `severity`: Comma-separated list of severity levels

**Response:**
```json
{
  "total_errors": 150,
  "error_rate": 2.5,
  "by_category": {
    "API": 50,
    "Database": 30,
    "Network": 70
  },
  "by_severity": {
    "CRITICAL": 10,
    "WARNING": 40,
    "INFO": 100
  },
  "error_rate_history": {
    "timestamps": ["2024-01-01T00:00:00Z", "2024-01-01T00:01:00Z"],
    "values": [2.1, 2.5]
  }
}
```

### Alerts

#### Get Active Alerts

```http
GET /v1/alerts
```

Returns list of active alerts.

**Parameters:**
- `status`: Filter by alert status (active, acknowledged, resolved)
- `severity`: Filter by severity level
- `component`: Filter by component
- `page`: Page number for pagination
- `limit`: Number of alerts per page

**Response:**
```json
{
  "total": 25,
  "page": 1,
  "limit": 10,
  "alerts": [
    {
      "alert_id": "alert-123",
      "severity": "CRITICAL",
      "type": "HighErrorRate",
      "component": "api",
      "message": "Error rate exceeded threshold",
      "created_at": "2024-01-01T00:00:00Z",
      "status": "ACTIVE"
    }
  ]
}
```

#### Update Alert Status

```http
POST /v1/alerts/{alert_id}/status
```

Update the status of an alert.

**Request:**
```json
{
  "status": "ACKNOWLEDGED",
  "comment": "Investigating the issue"
}
```

**Response:**
```json
{
  "alert_id": "alert-123",
  "status": "ACKNOWLEDGED",
  "updated_at": "2024-01-01T00:01:00Z"
}
```

## WebSocket API

### Real-time Updates

Connect to WebSocket for real-time updates:

```javascript
const ws = new WebSocket('wss://api.example.com/v1/ws');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Received update:', update);
};
```

**Update Types:**
- Health status changes
- New alerts
- Error rate changes
- Component status updates

## Rate Limiting

API requests are rate limited:

- 100 requests per minute per IP
- 1000 requests per hour per API key
- WebSocket connections limited to 5 per API key

## Error Responses

Standard error response format:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "details": {
      "limit": 100,
      "reset_at": "2024-01-01T00:01:00Z"
    }
  }
}
```

Common error codes:
- `UNAUTHORIZED`: Invalid or missing API key
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INVALID_PARAMETERS`: Invalid request parameters
- `NOT_FOUND`: Resource not found
- `INTERNAL_ERROR`: Server error

## Best Practices

### Optimization

1. **Batch Requests**
   - Use pagination for large datasets
   - Combine related requests
   - Cache responses when appropriate

2. **Error Handling**
   - Implement exponential backoff
   - Handle rate limiting gracefully
   - Log API errors for debugging

3. **Real-time Updates**
   - Use WebSocket for real-time data
   - Implement reconnection logic
   - Handle connection failures

### Security

1. **API Key Management**
   - Rotate keys regularly
   - Use separate keys per environment
   - Never expose keys in client-side code

2. **Request Validation**
   - Validate input parameters
   - Sanitize request data
   - Use HTTPS for all requests 
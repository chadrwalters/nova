# Nova Deployment Guide

## Local Development Setup

### Prerequisites
- Python 3.10+
- Poetry
- Anthropic API key
- Bear.app (for data export)

### Installation Steps

1. Clone the repository
```bash
git clone https://github.com/your-org/nova.git
cd nova
```

2. Install dependencies
```bash
poetry install
```

3. Configure environment
```bash
# Create .env file
cat > .env << EOL
ANTHROPIC_API_KEY=your_key_here
NOVA_ENV=development
EOL
```

4. Run tests
```bash
poetry run pytest
```

5. Start Nova
```bash
poetry run nova
```

## Configuration

### Basic Configuration
Create `nova.yaml` in your project root:

```yaml
ingestion:
  chunk_size: 500
  heading_weight: 1.5
  
embedding:
  model: "all-MiniLM-L6-v2"
  dimension: 384
  
vector_store:
  engine: "faiss"
  
rag:
  top_k: 5
  
llm:
  model: "claude-2"
  max_tokens: 1000
  
security:
  ephemeral_ttl: 300
```

### Environment-specific Configuration
```yaml
# config/development.yaml
debug: true
log_level: DEBUG

# config/production.yaml
debug: false
log_level: INFO
```

## Cloud Deployment (Optional)

### Prerequisites
- Cloud provider account (AWS/GCP/Azure)
- SSL certificate
- Domain name (optional)

### Setup Steps

1. Install cloud dependencies
```bash
poetry install --extras cloud
```

2. Configure cloud environment
```bash
# Create cloud config
cat > config/cloud.yaml << EOL
cloud:
  provider: aws
  region: us-west-2
  instance_type: t3.medium

security:
  auth_token: your_token_here
  tls_cert: /path/to/cert
  tls_key: /path/to/key
EOL
```

3. Deploy
```bash
poetry run nova deploy --cloud
```

## Security Considerations

### API Key Management
- Store API keys in environment variables
- Use secret management service in cloud
- Rotate keys regularly

### Data Privacy
- Enable TLS for all traffic
- Implement token-based auth
- Use ephemeral storage for sensitive data
- Regular security audits

### Logging
- Avoid logging sensitive data
- Implement log rotation
- Use structured logging

## Monitoring

### Health Checks
```python
from nova.monitoring import health_check

# Basic health check
status = health_check()
```

### Metrics
- Query latency
- Embedding generation time
- Vector search performance
- Memory usage
- API rate limits

### Alerting
- Set up alerts for:
  - High latency
  - Error rates
  - Memory usage
  - API quota usage

## Backup & Recovery

### Vector Store Backup
```bash
# Backup FAISS index
poetry run nova backup-vectors

# Restore from backup
poetry run nova restore-vectors --backup-file vectors.backup
```

### Configuration Backup
- Regular backups of:
  - Configuration files
  - API keys
  - TLS certificates
  - Custom scripts

## Troubleshooting

### Common Issues

1. Conversion Failures
```python
from nova.utils import diagnose_conversion

# Check conversion issues
issues = diagnose_conversion(file_path)
```

2. Embedding Errors
```python
from nova.utils import validate_embeddings

# Validate embeddings
validation = validate_embeddings(chunks)
```

3. API Issues
```python
from nova.utils import check_api_health

# Check API status
api_status = check_api_health()
```

### Debug Mode
```bash
# Enable debug mode
poetry run nova --debug

# View debug logs
tail -f logs/nova-debug.log
```

## Maintenance

### Regular Tasks
1. Update dependencies
```bash
poetry update
```

2. Clean old data
```bash
poetry run nova cleanup --older-than 30d
```

3. Optimize vector store
```bash
poetry run nova optimize-vectors
```

### Performance Tuning
- Adjust chunk sizes
- Configure embedding batch size
- Optimize vector store parameters
- Monitor and adjust cache sizes

## Migration Guide

### Version Updates
```bash
# Check current version
poetry run nova version

# Update to latest
poetry update nova
```

### Data Migration
```bash
# Export data
poetry run nova export-data

# Import to new version
poetry run nova import-data --file export.json
``` 
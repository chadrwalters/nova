# Nova Deployment Guide

## Prerequisites

1. Python 3.9+
2. Poetry
3. OpenAI API key (for default configuration)
4. Anthropic API key (optional, for Claude)

## Local Deployment

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/nova.git
   cd nova
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Set up environment variables:
   ```bash
   # Required for default configuration
   export OPENAI_API_KEY="your-openai-key-here"
   
   # Optional for Claude
   export ANTHROPIC_API_KEY="your-anthropic-key-here"
   ```

4. Create configuration:
   ```bash
   cp config/nova.yaml.template config/nova.yaml
   ```

5. Run Nova:
   ```bash
   poetry run nova query "Your question here?"
   ```

## Configuration

The default configuration uses OpenAI's gpt-3.5-turbo-16k for optimal cost/performance:

```yaml
llm:
  provider: "openai"
  api_key: "${OPENAI_API_KEY}"
  model: "gpt-3.5-turbo-16k"
  max_tokens: 1000
  temperature: 0.7
```

For specialized use cases, you can switch to Claude:

```yaml
llm:
  provider: "claude"
  api_key: "${ANTHROPIC_API_KEY}"
  model: "claude-2"
  max_tokens: 1000
  temperature: 0.7
```

## Production Deployment

For production deployments:

1. Set up monitoring:
   ```yaml
   monitoring:
     enabled: true
     metrics_port: 9090
     memory_update_interval: 60
     vector_store_update_interval: 300
     alerting:
       max_query_latency: 5.0
       max_error_rate: 0.01
       max_memory_usage: 4_000_000_000  # 4GB
       max_vector_store_size: 1_000_000
       rate_limit_warning_threshold: 0.2
   ```

2. Configure logging:
   ```yaml
   logging:
     level: "INFO"
     file: "logs/nova.log"
     format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
   ```

3. Set up security:
   ```yaml
   security:
     ephemeral_ttl: 300
     rate_limit:
       requests_per_minute: 60
     tls:
       cert_file: "/path/to/cert.pem"
       key_file: "/path/to/key.pem"
   ```

## Health Checks

Monitor these metrics:

1. Query Performance:
   - Average latency < 5s
   - P95 latency < 10s
   - Error rate < 1%

2. Resource Usage:
   - Memory usage < 4GB
   - Vector store size < 1M vectors
   - API rate limits > 20%

3. System Health:
   - Process uptime
   - CPU usage
   - Disk space

## Backup and Restore

1. Backup command:
   ```bash
   poetry run nova backup create
   ```

2. Restore command:
   ```bash
   poetry run nova backup restore --backup-dir data/backup/latest
   ```

## Troubleshooting

Common issues and solutions:

1. API Rate Limits:
   - Implement exponential backoff
   - Monitor rate limit metrics
   - Consider upgrading API tier

2. Memory Usage:
   - Monitor with Prometheus
   - Set up alerts
   - Consider scaling vertically

3. Performance Issues:
   - Check vector store size
   - Monitor query latency
   - Review context window usage

## Updates and Maintenance

1. Update dependencies:
   ```bash
   poetry update
   ```

2. Run tests:
   ```bash
   poetry run pytest
   ```

3. Check types:
   ```bash
   poetry run mypy .
   ```

4. Run pre-commit:
   ```bash
   poetry run pre-commit run --all-files
   ``` 
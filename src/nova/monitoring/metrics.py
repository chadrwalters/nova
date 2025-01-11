"""Nova monitoring metrics."""

from prometheus_client import Counter, Histogram, Gauge, start_http_server, CollectorRegistry
from functools import wraps
import time
import asyncio

# Create a custom registry
REGISTRY = CollectorRegistry()

# Query metrics
QUERY_LATENCY = Histogram(
    'query_latency_seconds',
    'Query latency in seconds',
    ['query_type'],
    registry=REGISTRY
)

QUERY_REQUESTS = Counter(
    'query_requests_total',
    'Total number of query requests',
    ['query_type'],
    registry=REGISTRY
)

QUERY_ERRORS = Counter(
    'query_errors_total',
    'Number of query errors',
    ['error_type'],
    registry=REGISTRY
)

# API metrics
API_REQUESTS = Counter(
    'api_requests_total',
    'Number of API requests',
    ['service'],
    registry=REGISTRY
)

API_ERRORS = Counter(
    'api_errors_total',
    'Number of API errors',
    ['service', 'error_type'],
    registry=REGISTRY
)

# Resource metrics
MEMORY_USAGE = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes',
    registry=REGISTRY
)

# Memory Pressure Alerts
MEMORY_PRESSURE_ALERTS = Counter(
    'memory_pressure_alerts_total',
    'Number of memory pressure alerts',
    ['severity', 'component'],
    registry=REGISTRY
)

# Vector store metrics
VECTOR_STORE_VECTORS = Gauge(
    'vector_store_vectors_total',
    'Total number of vectors in store',
    ['store_type'],
    registry=REGISTRY
)

VECTOR_STORE_MEMORY = Gauge(
    'vector_store_memory_bytes',
    'Memory usage of vector store in bytes',
    ['store_type'],
    registry=REGISTRY
)

VECTOR_STORE_SIZE = Gauge(
    'vector_store_size_bytes',
    'Size of vector store index in bytes',
    ['store_type'],
    registry=REGISTRY
)

VECTOR_SEARCH_LATENCY = Histogram(
    'vector_search_latency_seconds',
    'Vector search latency in seconds',
    ['store_type'],
    registry=REGISTRY
)

# Embedding metrics
EMBEDDING_GENERATION_TIME = Histogram(
    'embedding_generation_seconds',
    'Time spent generating embeddings',
    ['model'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0),
    registry=REGISTRY
)

EMBEDDING_BATCH_SIZE = Gauge(
    'embedding_batch_size',
    'Size of current embedding batch',
    ['model'],
    registry=REGISTRY
)

EMBEDDING_QUEUE_SIZE = Gauge(
    'embedding_queue_size',
    'Number of items waiting for embedding',
    ['model'],
    registry=REGISTRY
)

# Rate limit metrics
RATE_LIMITS_REMAINING = Gauge(
    'rate_limits_remaining',
    'Number of API requests remaining',
    ['service'],
    registry=REGISTRY
)

RATE_LIMIT_RESETS = Gauge(
    'rate_limit_resets',
    'Time until rate limit resets',
    ['service'],
    registry=REGISTRY
)

def init_metrics():
    """Initialize metrics with default labels."""
    # Initialize vector store metrics
    for store_type in ['faiss_cpu', 'faiss_gpu', 'test']:
        VECTOR_STORE_VECTORS.labels(store_type=store_type)
        VECTOR_STORE_MEMORY.labels(store_type=store_type)
        VECTOR_STORE_SIZE.labels(store_type=store_type)
        VECTOR_SEARCH_LATENCY.labels(store_type=store_type)
    
    # Initialize query metrics
    for query_type in ['test', 'search', 'update']:
        QUERY_LATENCY.labels(query_type=query_type)
        QUERY_REQUESTS.labels(query_type=query_type)
    
    # Initialize error metrics
    for error_type in ['test', 'timeout', 'connection', 'validation']:
        QUERY_ERRORS.labels(error_type=error_type)
    
    # Initialize API metrics
    for service in ['test', 'openai', 'anthropic']:
        API_REQUESTS.labels(service=service)
        API_ERRORS.labels(service=service, error_type='test')
        RATE_LIMITS_REMAINING.labels(service=service)
        RATE_LIMIT_RESETS.labels(service=service)
    
    # Initialize embedding metrics
    for model in ['all-MiniLM-L6-v2', 'test']:
        EMBEDDING_GENERATION_TIME.labels(model=model)
        EMBEDDING_BATCH_SIZE.labels(model=model)
        EMBEDDING_QUEUE_SIZE.labels(model=model)
    
    # Initialize memory pressure alerts
    for severity in ['critical', 'warning']:
        for component in ['system', 'gpu0', 'gpu1', 'test']:
            MEMORY_PRESSURE_ALERTS.labels(severity=severity, component=component)

def track_time(metric: Histogram):
    """Decorator to track function execution time."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                metric.observe(time.time() - start)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                metric.observe(time.time() - start)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def update_memory_usage(memory_bytes: int) -> None:
    """Update memory usage metric."""
    MEMORY_USAGE.set(memory_bytes)

def update_vector_store_metrics(total_vectors: int, memory_usage: int, index_size: int) -> None:
    """Update vector store metrics."""
    store_type = 'test'  # Use test label for metrics
    VECTOR_STORE_VECTORS.labels(store_type=store_type).set(total_vectors)
    VECTOR_STORE_MEMORY.labels(store_type=store_type).set(memory_usage)
    VECTOR_STORE_SIZE.labels(store_type=store_type).set(index_size)

def record_api_request(service: str) -> None:
    """Record an API request."""
    API_REQUESTS.labels(service=service).inc()

def record_api_error(service: str, error_type: str) -> None:
    """Record an API error."""
    API_ERRORS.labels(service=service, error_type=error_type).inc()

def update_rate_limits(service: str, remaining: int, reset_time: int) -> None:
    """Update rate limit metrics."""
    RATE_LIMITS_REMAINING.labels(service=service).set(remaining)
    RATE_LIMIT_RESETS.labels(service=service).set(reset_time)

def update_embedding_metrics(model: str, batch_size: int, queue_size: int) -> None:
    """Update embedding metrics."""
    EMBEDDING_BATCH_SIZE.labels(model=model).set(batch_size)
    EMBEDDING_QUEUE_SIZE.labels(model=model).set(queue_size)

def get_metric(name: str):
    """Get a metric by name."""
    metrics = {
        'query_latency': QUERY_LATENCY,
        'query_requests': QUERY_REQUESTS,
        'query_errors': QUERY_ERRORS,
        'api_requests': API_REQUESTS,
        'api_errors': API_ERRORS,
        'memory_usage': MEMORY_USAGE,
        'memory_pressure_alerts': MEMORY_PRESSURE_ALERTS,
        'vector_store_size': VECTOR_STORE_SIZE,
        'vector_store_memory': VECTOR_STORE_MEMORY,
        'vector_store_vectors': VECTOR_STORE_VECTORS,
        'vector_search_latency': VECTOR_SEARCH_LATENCY,
        'embedding_generation_time': EMBEDDING_GENERATION_TIME,
        'embedding_batch_size': EMBEDDING_BATCH_SIZE,
        'embedding_queue_size': EMBEDDING_QUEUE_SIZE,
        'rate_limits_remaining': RATE_LIMITS_REMAINING,
        'rate_limit_resets': RATE_LIMIT_RESETS
    }
    return metrics.get(name)

def record_query_latency(query_type: str, duration: float) -> None:
    """Record query latency."""
    QUERY_LATENCY.labels(query_type=query_type).observe(duration)

def record_query_error(error_type: str) -> None:
    """Record a query error."""
    QUERY_ERRORS.labels(error_type=error_type).inc()

def record_query_request(query_type: str) -> None:
    """Record a query request."""
    QUERY_REQUESTS.labels(query_type=query_type).inc()

def start_metrics_server(port: int = 8000, host: str = "localhost") -> None:
    """Start the metrics server."""
    start_http_server(port, host, registry=REGISTRY) 
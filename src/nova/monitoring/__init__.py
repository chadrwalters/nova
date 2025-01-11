"""Nova monitoring package."""

from .config import MonitoringConfig, AlertingConfig, MetricsConfig
from .metrics import (
    QUERY_LATENCY,
    QUERY_ERRORS,
    QUERY_REQUESTS,
    API_REQUESTS,
    API_ERRORS,
    MEMORY_USAGE,
    VECTOR_STORE_SIZE,
    VECTOR_STORE_MEMORY,
    RATE_LIMITS_REMAINING,
    RATE_LIMIT_RESETS,
    EMBEDDING_GENERATION_TIME,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_QUEUE_SIZE,
    VECTOR_SEARCH_LATENCY,
    init_metrics,
    get_metric,
    record_query_latency,
    record_query_error,
    record_query_request,
    update_memory_usage,
    update_vector_store_metrics,
    update_rate_limits,
    update_embedding_metrics,
    track_time,
    start_metrics_server
)
from .alerts import AlertManager, AlertSeverity, Alert
from .service import MonitoringService
from .vector_store import (
    VectorStoreMetrics,
    MonitoredVectorStore,
    VectorStoreMonitor,
    MonitoredFAISS
)
from .claude import MonitoredClaudeClient
from .rag import RAGMetrics, MonitoredRAGOrchestrator


__all__ = [
    # Config
    'MonitoringConfig',
    'AlertingConfig',
    'MetricsConfig',
    
    # Metrics
    'start_metrics_server',
    'update_memory_usage',
    'update_vector_store_metrics',
    'QUERY_LATENCY',
    'QUERY_ERRORS',
    'EMBEDDING_GENERATION_TIME',
    'EMBEDDING_BATCH_SIZE',
    'VECTOR_SEARCH_LATENCY',
    'VECTOR_STORE_SIZE',
    'MEMORY_USAGE',
    'API_REQUESTS',
    'API_ERRORS',
    'RATE_LIMITS_REMAINING',
    'RATE_LIMIT_RESETS',
    
    # Alerts
    'AlertManager',
    'AlertSeverity',
    'Alert',
    
    # Service
    'MonitoringService',
    
    # Vector Store
    'VectorStoreMetrics',
    'MonitoredVectorStore',
    'VectorStoreMonitor',
    'MonitoredFAISS',
    
    # Claude
    'MonitoredClaudeClient',
    
    # RAG
    'RAGMetrics',
    'MonitoredRAGOrchestrator'
] 
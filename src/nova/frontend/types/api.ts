export enum AlertSeverity {
  CRITICAL = 'critical',
  WARNING = 'warning',
  INFO = 'info',
}

export enum AlertStatus {
  ACTIVE = 'active',
  ACKNOWLEDGED = 'acknowledged',
  RESOLVED = 'resolved',
}

export interface Alert {
  alert_id: string;
  severity: AlertSeverity;
  type: string;
  component: string;
  message: string;
  created_at: string;
  status: AlertStatus;
}

export interface AlertSummary {
  total_alerts: number;
  active_alerts: number;
  acknowledged_alerts: number;
  resolved_alerts: number;
}

export interface AlertGroup {
  group_id: string;
  alert_type: string;
  severity: AlertSeverity;
  component: string;
  alerts: Alert[];
}

export interface AlertTrend {
  alert_type: string;
  component: string;
  alert_count: number;
  rate_of_change: number;
}

export interface MemorySummary {
  system_memory_total: number;
  system_memory_used: number;
  gpu_memory_total: number;
  gpu_memory_used: number;
}

export interface MemoryPressureData {
  timestamps: string[];
  system_pressure: number[];
  gpu_pressure: number[];
}

export interface IndexMemoryData {
  [index: string]: number;
}

export interface VectorStoreMetrics {
  store_size: number;
  search_latency: number;
  search_count: number;
  timestamps: string[];
  store_size_history: number[];
  growth_rate: number;
}

export interface VectorStorePerformance {
  search_latency: number;
  search_count: number;
  timestamps: string[];
  latency_history: number[];
  p95_latency_history: number[];
}

export interface ServiceMetrics {
  rate_limits: {
    current: number;
    limit: number;
    reset_at: string;
  };
  rate_limits_remaining: number;
  rate_limits_history: number[];
  errors: {
    count: number;
    rate: number;
    severity: 'low' | 'medium' | 'high' | 'critical';
  }[];
  api_errors: number;
  error_count: number[];
  error_count_history: number[];
  error_rate_history: number[];
  timestamps: string[];
}

export interface ServiceHealth {
  status: 'healthy' | 'warning' | 'error';
  uptime: number;
  components: Array<{
    name: string;
    status: 'healthy' | 'warning' | 'error';
  }>;
}

export interface ErrorMetrics {
  total_errors: number;
  error_rate: number;
  categories: Array<{
    name: string;
    count: number;
  }>;
}

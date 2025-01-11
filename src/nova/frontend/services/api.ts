import axios from 'axios';
import type {
  Alert,
  AlertSummary,
  AlertGroup,
  AlertTrend,
  MemorySummary,
  VectorStoreMetrics,
  ServiceMetrics
} from '../types/api';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const alertsApi = {
  getCurrentAlerts: () => 
    api.get<Alert[]>('/alerts/current').then(res => res.data),
    
  getAlertHistory: () => 
    api.get<Alert[]>('/alerts/history').then(res => res.data),
    
  getAlertSummary: () => 
    api.get<AlertSummary>('/alerts/summary').then(res => res.data),
    
  acknowledgeAlert: (alertId: string) => 
    api.post<{ success: boolean; message: string }>(`/alerts/${alertId}/acknowledge`).then(res => res.data),
    
  resolveAlert: (alertId: string) => 
    api.post<{ success: boolean; message: string }>(`/alerts/${alertId}/resolve`).then(res => res.data),
    
  getAlertGroups: () => 
    api.get<AlertGroup[]>('/alerts/groups').then(res => res.data),
    
  getComponentCorrelations: () => 
    api.get<Record<string, string[]>>('/alerts/correlations').then(res => res.data),
    
  getAlertTrends: () => 
    api.get<Record<string, AlertTrend[]>>('/alerts/trends').then(res => res.data),
};

export const monitoringApi = {
  getMemorySummary: () => 
    api.get<MemorySummary>('/memory/summary').then(res => res.data),
    
  getMemoryPressure: () => 
    api.get<{ memory_pressure: boolean }>('/memory/pressure').then(res => res.data),
    
  getIndexMemory: () => 
    api.get<Record<string, number>>('/memory/indices').then(res => res.data),
};

export const metricsApi = {
  getVectorStoreMetrics: () => 
    api.get<VectorStoreMetrics>('/vectorstore/metrics').then(res => res.data),
    
  getVectorStorePerformance: () => 
    api.get<Record<string, number>>('/vectorstore/performance').then(res => res.data),
    
  getRateLimits: () => 
    api.get<ServiceMetrics['rate_limits']>('/rate_limits').then(res => res.data),
    
  getServiceErrors: () => 
    api.get<ServiceMetrics['errors']>('/errors').then(res => res.data),
}; 
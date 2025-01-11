import { Alert, AlertSeverity, AlertStatus } from '../types/api';

const mockAlerts: Alert[] = [
  {
    alert_id: '1',
    severity: AlertSeverity.CRITICAL,
    type: 'System',
    component: 'CPU',
    message: 'High CPU usage detected',
    created_at: new Date().toISOString(),
    status: AlertStatus.ACTIVE,
  },
  {
    alert_id: '2',
    severity: AlertSeverity.WARNING,
    type: 'Memory',
    component: 'RAM',
    message: 'Memory usage above 80%',
    created_at: new Date().toISOString(),
    status: AlertStatus.ACKNOWLEDGED,
  },
];

export async function fetchCurrentAlerts(): Promise<Alert[]> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 500));
  return mockAlerts;
}

export async function fetchServiceHealth() {
  await new Promise(resolve => setTimeout(resolve, 500));
  return {
    status: 'healthy',
    uptime: 99.9,
    components: [
      { name: 'API', status: 'healthy' },
      { name: 'Database', status: 'healthy' },
      { name: 'Cache', status: 'warning' },
    ],
  };
}

export async function fetchErrorMetrics() {
  await new Promise(resolve => setTimeout(resolve, 500));
  return {
    total_errors: 150,
    error_rate: 0.5,
    categories: [
      { name: 'API', count: 50 },
      { name: 'Database', count: 30 },
      { name: 'Cache', count: 70 },
    ],
  };
}

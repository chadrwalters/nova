import { useState, useEffect } from 'react';

export interface LayoutConfig {
  [key: string]: {
    x: number;
    y: number;
    w: number;
    h: number;
    visible: boolean;
  };
}

export interface TimeRangeConfig {
  defaultRange: string;
  customRanges: {
    name: string;
    start: string;
    end: string;
  }[];
}

export interface AlertThreshold {
  metric: string;
  warning: number;
  critical: number;
  enabled: boolean;
}

export interface MetricGroup {
  id: string;
  name: string;
  metrics: string[];
  color?: string;
}

export interface UserPreferences {
  layout: LayoutConfig;
  timeRange: TimeRangeConfig;
  alertThresholds: AlertThreshold[];
  metricGroups: MetricGroup[];
}

const defaultPreferences: UserPreferences = {
  layout: {
    serviceHealth: { x: 0, y: 0, w: 12, h: 6, visible: true },
    errorMetrics: { x: 0, y: 6, w: 6, h: 4, visible: true },
    rateLimits: { x: 6, y: 6, w: 6, h: 4, visible: true },
    alerts: { x: 0, y: 10, w: 12, h: 6, visible: true },
  },
  timeRange: {
    defaultRange: '24h',
    customRanges: [],
  },
  alertThresholds: [
    { metric: 'error_rate', warning: 5, critical: 10, enabled: true },
    { metric: 'memory_usage', warning: 80, critical: 90, enabled: true },
    { metric: 'api_latency', warning: 1000, critical: 2000, enabled: true },
  ],
  metricGroups: [],
};

export function usePreferences() {
  const [preferences, setPreferences] = useState<UserPreferences>(() => {
    const saved = localStorage.getItem('userPreferences');
    if (saved) {
      return { ...defaultPreferences, ...JSON.parse(saved) };
    }
    return defaultPreferences;
  });

  useEffect(() => {
    localStorage.setItem('userPreferences', JSON.stringify(preferences));
  }, [preferences]);

  const updateLayout = (newLayout: Partial<Record<keyof LayoutConfig, Partial<LayoutConfig[string]>>>) => {
    setPreferences(prev => ({
      ...prev,
      layout: Object.entries(prev.layout).reduce((acc, [key, value]) => ({
        ...acc,
        [key]: {
          ...value,
          ...(newLayout[key] || {}),
        },
      }), {} as LayoutConfig),
    }));
  };

  const updateTimeRange = (newConfig: Partial<TimeRangeConfig>) => {
    setPreferences(prev => ({
      ...prev,
      timeRange: { ...prev.timeRange, ...newConfig },
    }));
  };

  const updateAlertThresholds = (thresholds: AlertThreshold[]) => {
    setPreferences(prev => ({
      ...prev,
      alertThresholds: thresholds,
    }));
  };

  const updateMetricGroups = (groups: MetricGroup[]) => {
    setPreferences(prev => ({
      ...prev,
      metricGroups: groups,
    }));
  };

  const resetPreferences = () => {
    setPreferences(defaultPreferences);
  };

  return {
    preferences,
    updateLayout,
    updateTimeRange,
    updateAlertThresholds,
    updateMetricGroups,
    resetPreferences,
  };
} 
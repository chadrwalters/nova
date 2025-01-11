import { useState, useCallback } from 'react';
import { TimeRange } from '../components/common/TimeRangeSelector';

export function useTimeRange(defaultRange: TimeRange = '24h') {
  const [timeRange, setTimeRange] = useState<TimeRange>(defaultRange);

  const getTimeRangeInSeconds = useCallback((range: TimeRange): number => {
    switch (range) {
      case '1h':
        return 3600;
      case '6h':
        return 21600;
      case '24h':
        return 86400;
      case '7d':
        return 604800;
      case '30d':
        return 2592000;
      default:
        return 86400; // Default to 24h
    }
  }, []);

  const filterDataByTimeRange = useCallback((
    timestamps: string[],
    metrics: { [key: string]: number[] }
  ): { timestamps: string[]; metrics: { [key: string]: number[] } } => {
    const now = Date.now();
    const rangeInSeconds = getTimeRangeInSeconds(timeRange);
    const cutoffTime = now - rangeInSeconds * 1000;

    const filteredIndexes = timestamps.reduce<number[]>((acc, timestamp, index) => {
      if (new Date(timestamp).getTime() >= cutoffTime) {
        acc.push(index);
      }
      return acc;
    }, []);

    const filteredTimestamps = filteredIndexes.map(i => timestamps[i]);
    const filteredMetrics: { [key: string]: number[] } = {};

    Object.entries(metrics).forEach(([key, values]) => {
      filteredMetrics[key] = filteredIndexes.map(i => values[i]);
    });

    return {
      timestamps: filteredTimestamps,
      metrics: filteredMetrics
    };
  }, [timeRange, getTimeRangeInSeconds]);

  return {
    timeRange,
    setTimeRange,
    getTimeRangeInSeconds,
    filterDataByTimeRange
  };
} 
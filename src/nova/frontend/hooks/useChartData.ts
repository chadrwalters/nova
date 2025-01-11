import { useMemo } from 'react';
import { Chart as ChartJS, ChartOptions } from 'chart.js';
import { decimateData } from '../utils/dataDecimation';

export interface TimeSeriesPoint {
  timestamp: number;
  value: number;
}

export interface ChartDataOptions {
  maxPoints?: number;
  progressive?: boolean;
  initialPoints?: number;
  chunkSize?: number;
  aggregation?: 'LTTB' | 'min-max' | 'average';
}

export interface UseChartDataResult {
  data: {
    datasets: {
      data: TimeSeriesPoint[];
      label: string;
      borderColor: string;
      backgroundColor: string;
      fill: boolean;
    }[];
  };
  options: ChartOptions;
  isLoading: boolean;
  hasMoreData: boolean;
  loadNextChunk: () => void;
}

export function useChartData(
  data: TimeSeriesPoint[],
  label: string,
  options: ChartDataOptions = {}
): UseChartDataResult {
  const {
    maxPoints = 1000,
    progressive = false,
    initialPoints = 100,
    chunkSize = 200,
    aggregation = 'LTTB',
  } = options;

  const [displayData, remainingData] = useMemo(() => {
    if (!progressive || data.length <= initialPoints) {
      return [decimateData(data, { maxPoints, aggregation }), []];
    }

    const initial = data.slice(0, initialPoints);
    const remaining = data.slice(initialPoints);
    return [decimateData(initial, { maxPoints, aggregation }), remaining];
  }, [data, maxPoints, progressive, initialPoints, aggregation]);

  const chartOptions = useMemo<ChartOptions>(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      decimation: {
        enabled: true,
      },
    },
    scales: {
      x: {
        type: 'time',
        ticks: {
          maxTicksLimit: 10,
        },
      },
      y: {
        ticks: {
          maxTicksLimit: 8,
        },
      },
    },
  }), []);

  const loadNextChunk = () => {
    if (!remainingData.length) return;
    
    const nextChunk = remainingData.slice(0, chunkSize);
    const newData = [...displayData, ...nextChunk];
    return decimateData(newData, { maxPoints, aggregation });
  };

  return {
    data: {
      datasets: [{
        data: displayData,
        label,
        borderColor: '#646cff',
        backgroundColor: 'rgba(100, 108, 255, 0.1)',
        fill: true,
      }],
    },
    options: chartOptions,
    isLoading: false,
    hasMoreData: remainingData.length > 0,
    loadNextChunk,
  };
} 
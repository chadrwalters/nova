/// <reference types="jest" />
import '@testing-library/jest-dom/extend-expect';
import React from 'react';
import { renderHook, act } from '@testing-library/react-hooks';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useChartData, type TimeSeriesPoint } from '../useChartData';

// Mock data generator
const generateTestData = (count: number): TimeSeriesPoint[] => {
  const data: TimeSeriesPoint[] = [];
  for (let i = 0; i < count; i++) {
    data.push({
      timestamp: i * 1000,
      value: Math.sin(i * 0.1) * 100 + Math.random() * 10,
    });
  }
  return data;
};

describe('useChartData', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );

  it('should handle empty data', () => {
    const { result } = renderHook(() => useChartData([], 'Test Data'), { wrapper });

    expect(result.current.data.datasets[0].data).toHaveLength(0);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.hasMoreData).toBe(false);
  });

  it('should decimate data when length exceeds maxPoints', () => {
    const rawData = generateTestData(2000);
    const maxPoints = 1000;

    const { result } = renderHook(
      () => useChartData(rawData, 'Test Data', { maxPoints }),
      { wrapper }
    );

    expect(result.current.data.datasets[0].data.length).toBeLessThanOrEqual(maxPoints);
  });

  it('should handle progressive loading', async () => {
    const rawData = generateTestData(1000);
    const initialPoints = 100;
    const chunkSize = 200;

    const { result } = renderHook(
      () => useChartData(rawData, 'Test Data', {
        progressive: true,
        initialPoints,
        chunkSize,
      }),
      { wrapper }
    );

    // Check initial load
    expect(result.current.data.datasets[0].data.length).toBeLessThanOrEqual(initialPoints);
    expect(result.current.hasMoreData).toBe(true);

    // Load next chunk
    await act(async () => {
      result.current.loadNextChunk();
    });

    // Check after loading chunk
    expect(result.current.data.datasets[0].data.length).toBeGreaterThan(initialPoints);
  });

  it('should apply correct chart options', () => {
    const { result } = renderHook(
      () => useChartData(generateTestData(100), 'Test Data'),
      { wrapper }
    );

    const options = result.current.options;

    expect(options.responsive).toBe(true);
    expect(options.maintainAspectRatio).toBe(false);
    expect(options.plugins?.decimation?.enabled).toBe(true);
    expect(options.scales?.x?.ticks?.maxTicksLimit).toBe(10);
    expect(options.scales?.y?.ticks?.maxTicksLimit).toBe(8);
  });

  it('should handle different aggregation methods', () => {
    const rawData = generateTestData(1000);

    // Test LTTB aggregation
    const { result: resultLTTB } = renderHook(
      () => useChartData(rawData, 'Test Data', { aggregation: 'LTTB' }),
      { wrapper }
    );
    expect(resultLTTB.current.data.datasets[0].data.length).toBeLessThanOrEqual(1000);

    // Test min-max aggregation
    const { result: resultMinMax } = renderHook(
      () => useChartData(rawData, 'Test Data', { aggregation: 'min-max' }),
      { wrapper }
    );
    expect(resultMinMax.current.data.datasets[0].data.length).toBeLessThanOrEqual(1000);

    // Test average aggregation
    const { result: resultAvg } = renderHook(
      () => useChartData(rawData, 'Test Data', { aggregation: 'average' }),
      { wrapper }
    );
    expect(resultAvg.current.data.datasets[0].data.length).toBeLessThanOrEqual(1000);
  });

  it('should update when data changes', () => {
    const { result, rerender } = renderHook(
      ({ data }: { data: TimeSeriesPoint[] }) => useChartData(data, 'Test Data'),
      {
        wrapper,
        initialProps: { data: generateTestData(100) },
      }
    );

    const initialLength = result.current.data.datasets[0].data.length;

    // Update with new data
    rerender({ data: generateTestData(200) });

    expect(result.current.data.datasets[0].data.length).not.toBe(initialLength);
  });
}); 
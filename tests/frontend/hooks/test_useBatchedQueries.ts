import { renderHook, act } from '@testing-library/react-hooks';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useBatchedQueries, createBatchedQueryHook } from '../../../src/nova/frontend/src/hooks/useBatchedQueries';

// Mock data
interface TestData {
  id: string;
  value: string;
}

const mockData: TestData[] = [
  { id: '1', value: 'test1' },
  { id: '2', value: 'test2' },
  { id: '3', value: 'test3' },
];

// Mock query function
const mockQueryFn = jest.fn().mockImplementation(async ({ queryKey }) => {
  const ids = queryKey.map(key => key.split(':')[1]);
  return ids.map(id => mockData.find(item => item.id === id));
});

describe('useBatchedQueries', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    jest.useFakeTimers();
    mockQueryFn.mockClear();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should batch multiple queries together', async () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result, waitFor } = renderHook(
      () => useBatchedQueries<TestData>(
        ['1', '2', '3'].map(id => `test:${id}`),
        mockQueryFn,
        { batchDelay: 50 }
      ),
      { wrapper }
    );

    // Initial state should be loading
    expect(result.current.every(query => query.isLoading)).toBe(true);

    // Wait for batch delay
    await act(async () => {
      jest.advanceTimersByTime(60);
    });

    // Wait for queries to complete
    await waitFor(() => {
      return result.current.every(query => !query.isLoading);
    });

    // Should have made only one batch call
    expect(mockQueryFn).toHaveBeenCalledTimes(1);

    // Should have correct data
    expect(result.current[0].data).toEqual(mockData[0]);
    expect(result.current[1].data).toEqual(mockData[1]);
    expect(result.current[2].data).toEqual(mockData[2]);
  });

  it('should handle errors gracefully', async () => {
    const errorQueryFn = jest.fn().mockRejectedValue(new Error('Test error'));

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result, waitFor } = renderHook(
      () => useBatchedQueries<TestData>(
        ['1'].map(id => `test:${id}`),
        errorQueryFn,
        { batchDelay: 50 }
      ),
      { wrapper }
    );

    // Wait for batch delay
    await act(async () => {
      jest.advanceTimersByTime(60);
    });

    // Wait for query to error
    await waitFor(() => {
      return result.current[0].isError;
    });

    expect(result.current[0].error).toBeTruthy();
  });
});

describe('createBatchedQueryHook', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    jest.useFakeTimers();
    mockQueryFn.mockClear();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should create a working batched query hook', async () => {
    const useTestQueries = createBatchedQueryHook<TestData>(
      'test',
      mockQueryFn,
      { batchDelay: 50 }
    );

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result, waitFor } = renderHook(
      () => useTestQueries(['1', '2']),
      { wrapper }
    );

    // Initial state should be loading
    expect(result.current.every(query => query.isLoading)).toBe(true);

    // Wait for batch delay
    await act(async () => {
      jest.advanceTimersByTime(60);
    });

    // Wait for queries to complete
    await waitFor(() => {
      return result.current.every(query => !query.isLoading);
    });

    // Should have made only one batch call
    expect(mockQueryFn).toHaveBeenCalledTimes(1);

    // Should have correct data
    expect(result.current[0].data).toEqual(mockData[0]);
    expect(result.current[1].data).toEqual(mockData[1]);
  });
}); 
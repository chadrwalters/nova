import { useQueries, UseQueryOptions, QueryFunction, QueryKey } from '@tanstack/react-query';
import { useCallback, useEffect, useRef } from 'react';

interface BatchOptions {
  batchSize?: number;
  batchDelay?: number;
}

type QueryConfig<TData> = Omit<UseQueryOptions<TData, Error>, 'queryKey' | 'queryFn'>;

interface QueryFunctionContext {
  queryKey: QueryKey;
  signal: AbortSignal;
  meta: Record<string, unknown> | undefined;
}

/**
 * Custom hook for batching multiple queries together.
 * This helps reduce the number of simultaneous API calls by grouping them into batches.
 * 
 * @param queryKeys - Array of query keys
 * @param queryFn - Query function that accepts a batch of keys and returns a Promise
 * @param options - Batching options (size and delay)
 * @param queryConfig - Additional React Query configuration
 * @returns Array of query results
 */
export function useBatchedQueries<TData>(
  queryKeys: string[],
  queryFn: QueryFunction<TData[]>,
  { batchSize = 10, batchDelay = 50 }: BatchOptions = {},
  queryConfig?: QueryConfig<TData>
) {
  const batchTimerRef = useRef<NodeJS.Timeout>();
  const pendingKeysRef = useRef<Set<string>>(new Set());
  const abortControllerRef = useRef<AbortController>(new AbortController());

  // Function to execute batched query
  const executeBatch = useCallback(async () => {
    const keys = Array.from(pendingKeysRef.current);
    if (keys.length === 0) return;

    // Clear pending keys
    pendingKeysRef.current.clear();

    // Execute query for batch
    try {
      await queryFn({
        queryKey: keys,
        signal: abortControllerRef.current.signal,
        meta: undefined
      });
    } catch (error) {
      console.error('Batch query error:', error);
    }
  }, [queryFn]);

  // Schedule batch execution
  const scheduleBatch = useCallback(() => {
    if (batchTimerRef.current) {
      clearTimeout(batchTimerRef.current);
    }

    batchTimerRef.current = setTimeout(executeBatch, batchDelay);
  }, [executeBatch, batchDelay]);

  // Add key to pending batch
  const addToBatch = useCallback((key: string) => {
    pendingKeysRef.current.add(key);
    scheduleBatch();
  }, [scheduleBatch]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (batchTimerRef.current) {
        clearTimeout(batchTimerRef.current);
      }
      abortControllerRef.current.abort();
    };
  }, []);

  // Create batched queries
  const queries = useQueries({
    queries: queryKeys.map((key) => ({
      queryKey: [key],
      queryFn: async (context: QueryFunctionContext) => {
        addToBatch(key);
        // Wait for batch execution
        return new Promise<TData>((resolve, reject) => {
          setTimeout(async () => {
            try {
              const results = await queryFn({
                queryKey: [key],
                signal: context.signal,
                meta: undefined
              });
              resolve(results[0]);
            } catch (error) {
              reject(error);
            }
          }, batchDelay + 10); // Wait slightly longer than batch delay
        });
      },
      ...queryConfig,
    })),
  });

  return queries;
}

/**
 * Helper hook for creating a batched query for a specific resource type
 */
export function createBatchedQueryHook<TData>(
  resourceType: string,
  queryFn: QueryFunction<TData[]>,
  defaultOptions: BatchOptions = {}
) {
  return function useBatchedResourceQuery(
    ids: string[],
    queryConfig?: QueryConfig<TData>
  ) {
    return useBatchedQueries<TData>(
      ids.map(id => `${resourceType}:${id}`),
      queryFn,
      defaultOptions,
      queryConfig
    );
  };
}

// Example usage:
// const useVectorQueries = createBatchedQueryHook<Vector>(
//   'vector',
//   async ({ queryKey }) => {
//     const ids = queryKey.map(key => key.split(':')[1]);
//     return fetchVectorsByIds(ids);
//   },
//   { batchSize: 50, batchDelay: 100 }
// ); 
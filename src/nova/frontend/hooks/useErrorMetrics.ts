import { useQuery } from '@tanstack/react-query';
import { fetchErrorMetrics } from '../services/mockApi';
import { ErrorMetrics } from '../types/api';

export function useErrorMetrics() {
  const { data: metrics, isLoading, error } = useQuery<ErrorMetrics>({
    queryKey: ['errorMetrics'],
    queryFn: fetchErrorMetrics,
  });

  return {
    metrics,
    isLoading,
    error,
  };
}

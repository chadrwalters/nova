import { useQuery } from '@tanstack/react-query';
import { fetchServiceHealth } from '../services/mockApi';
import { ServiceHealth } from '../types/api';

export function useServiceHealth() {
  const { data: health, isLoading, error } = useQuery<ServiceHealth>({
    queryKey: ['serviceHealth'],
    queryFn: fetchServiceHealth,
  });

  return {
    health,
    isLoading,
    error,
  };
}

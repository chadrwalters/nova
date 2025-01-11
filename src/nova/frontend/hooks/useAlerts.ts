import { useQuery } from '@tanstack/react-query';
import { fetchCurrentAlerts } from '../services/mockApi';
import { Alert } from '../types/api';

export function useAlerts() {
  const { data: alerts, isLoading, error } = useQuery<Alert[]>({
    queryKey: ['alerts'],
    queryFn: fetchCurrentAlerts,
  });

  return {
    alerts,
    isLoading,
    error,
  };
}

import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import {
  MemorySummary,
  MemoryPressureData,
  IndexMemoryData,
  VectorStoreMetrics,
  VectorStorePerformance,
  ServiceMetrics,
  ServiceHealth,
} from '../types/api';

const BASE_URL = '/api';

async function fetchMemorySummary(): Promise<MemorySummary> {
  const response = await axios.get(`${BASE_URL}/memory/summary`);
  return response.data;
}

async function fetchMemoryPressure(): Promise<MemoryPressureData> {
  const response = await axios.get(`${BASE_URL}/memory/pressure`);
  return response.data;
}

async function fetchIndexMemory(): Promise<IndexMemoryData> {
  const response = await axios.get(`${BASE_URL}/memory/index`);
  return response.data;
}

async function fetchVectorStoreMetrics(): Promise<VectorStoreMetrics> {
  const response = await axios.get(`${BASE_URL}/vectorstore/metrics`);
  return response.data;
}

async function fetchVectorStorePerformance(): Promise<VectorStorePerformance> {
  const response = await axios.get(`${BASE_URL}/vectorstore/performance`);
  return response.data;
}

async function fetchRateLimits(): Promise<ServiceMetrics> {
  const response = await axios.get(`${BASE_URL}/services/rate-limits`);
  return response.data;
}

async function fetchServiceErrors(): Promise<ServiceMetrics> {
  const response = await axios.get(`${BASE_URL}/services/errors`);
  return response.data;
}

async function fetchServiceHealth(): Promise<ServiceHealth> {
  const response = await axios.get(`${BASE_URL}/services/health`);
  return response.data;
}

export function useMonitoring() {
  const memorySummary = useQuery({
    queryKey: ['memory', 'summary'],
    queryFn: fetchMemorySummary,
    refetchInterval: 15000,
  });

  const memoryPressure = useQuery({
    queryKey: ['memory', 'pressure'],
    queryFn: fetchMemoryPressure,
    refetchInterval: 15000,
  });

  const indexMemory = useQuery({
    queryKey: ['memory', 'index'],
    queryFn: fetchIndexMemory,
    refetchInterval: 30000,
  });

  const vectorStoreMetrics = useQuery({
    queryKey: ['vectorstore', 'metrics'],
    queryFn: fetchVectorStoreMetrics,
    refetchInterval: 30000,
  });

  const vectorStorePerformance = useQuery({
    queryKey: ['vectorstore', 'performance'],
    queryFn: fetchVectorStorePerformance,
    refetchInterval: 30000,
  });

  const rateLimits = useQuery({
    queryKey: ['services', 'rate-limits'],
    queryFn: fetchRateLimits,
    refetchInterval: 60000,
  });

  const serviceErrors = useQuery({
    queryKey: ['services', 'errors'],
    queryFn: fetchServiceErrors,
    refetchInterval: 60000,
  });

  const serviceHealth = useQuery({
    queryKey: ['services', 'health'],
    queryFn: fetchServiceHealth,
    refetchInterval: 60000,
  });

  return {
    memorySummary,
    memoryPressure,
    indexMemory,
    vectorStoreMetrics,
    vectorStorePerformance,
    rateLimits,
    serviceErrors,
    serviceHealth,
  };
} 
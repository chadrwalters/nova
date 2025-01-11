import { useState, useEffect } from 'react';
import { AlertSeverity, AlertStatus } from '../types/api';

export interface FilterState {
  serviceHealth: {
    statusFilter: string;
    searchQuery: string;
  };
  errorMetrics: {
    selectedCategories: string[];
    selectedSeverities: AlertSeverity[];
  };
  alerts: {
    searchQuery: string;
    severities: AlertSeverity[];
    statuses: AlertStatus[];
    components: string[];
    types: string[];
  };
}

const defaultFilterState: FilterState = {
  serviceHealth: {
    statusFilter: 'all',
    searchQuery: '',
  },
  errorMetrics: {
    selectedCategories: [],
    selectedSeverities: [],
  },
  alerts: {
    searchQuery: '',
    severities: [],
    statuses: [],
    components: [],
    types: [],
  },
};

export function useFilterState<K extends keyof FilterState>(componentKey: K) {
  // Initialize state from localStorage or default
  const [filterState, setFilterState] = useState<FilterState[K]>(() => {
    const saved = localStorage.getItem('filterState');
    if (saved) {
      const parsed = JSON.parse(saved);
      return parsed[componentKey] || defaultFilterState[componentKey];
    }
    return defaultFilterState[componentKey];
  });

  // Save to localStorage whenever state changes
  useEffect(() => {
    const saved = localStorage.getItem('filterState');
    const fullState = saved ? JSON.parse(saved) : defaultFilterState;
    
    const newState = {
      ...fullState,
      [componentKey]: filterState,
    };
    
    localStorage.setItem('filterState', JSON.stringify(newState));
  }, [filterState, componentKey]);

  const updateFilter = (updates: Partial<FilterState[K]>) => {
    setFilterState(current => ({
      ...current,
      ...updates,
    }));
  };

  const resetFilters = () => {
    setFilterState(defaultFilterState[componentKey]);
  };

  return {
    filters: filterState,
    updateFilter,
    resetFilters,
  };
} 
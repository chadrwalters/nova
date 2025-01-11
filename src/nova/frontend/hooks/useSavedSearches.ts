import { useState, useEffect } from 'react';
import { FilterState } from './useFilterState';

export interface SavedSearch {
  id: string;
  name: string;
  componentKey: keyof FilterState;
  filters: FilterState[keyof FilterState];
  createdAt: string;
}

export function useSavedSearches(componentKey: keyof FilterState) {
  // Initialize state from localStorage
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>(() => {
    const saved = localStorage.getItem('savedSearches');
    if (saved) {
      const parsed = JSON.parse(saved);
      // Filter searches for this component
      return parsed.filter((search: SavedSearch) => search.componentKey === componentKey);
    }
    return [];
  });

  // Save to localStorage whenever state changes
  useEffect(() => {
    const saved = localStorage.getItem('savedSearches');
    const allSearches = saved ? JSON.parse(saved) : [];
    
    // Replace searches for this component while keeping others
    const otherSearches = allSearches.filter(
      (search: SavedSearch) => search.componentKey !== componentKey
    );
    
    const newSearches = [...otherSearches, ...savedSearches];
    localStorage.setItem('savedSearches', JSON.stringify(newSearches));
  }, [savedSearches, componentKey]);

  const saveSearch = (name: string, filters: FilterState[keyof FilterState]) => {
    const newSearch: SavedSearch = {
      id: Date.now().toString(),
      name,
      componentKey,
      filters,
      createdAt: new Date().toISOString(),
    };

    setSavedSearches(current => [...current, newSearch]);
  };

  const deleteSearch = (searchId: string) => {
    setSavedSearches(current => current.filter(search => search.id !== searchId));
  };

  const updateSearch = (searchId: string, updates: Partial<SavedSearch>) => {
    setSavedSearches(current =>
      current.map(search =>
        search.id === searchId
          ? { ...search, ...updates }
          : search
      )
    );
  };

  return {
    savedSearches,
    saveSearch,
    deleteSearch,
    updateSearch,
  };
} 
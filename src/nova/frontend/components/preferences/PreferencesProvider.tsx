import { ReactNode, createContext, useContext } from 'react';
import { usePreferences, UserPreferences } from '../../hooks/usePreferences';

interface PreferencesContextType {
  preferences: UserPreferences;
  updateLayout: ReturnType<typeof usePreferences>['updateLayout'];
  updateTimeRange: ReturnType<typeof usePreferences>['updateTimeRange'];
  updateAlertThresholds: ReturnType<typeof usePreferences>['updateAlertThresholds'];
  updateMetricGroups: ReturnType<typeof usePreferences>['updateMetricGroups'];
  resetPreferences: ReturnType<typeof usePreferences>['resetPreferences'];
}

export const PreferencesContext = createContext<PreferencesContextType | undefined>(undefined);

interface PreferencesProviderProps {
  children: ReactNode;
}

export function usePreferencesContext() {
  const context = useContext(PreferencesContext);
  if (!context) {
    throw new Error('usePreferencesContext must be used within a PreferencesProvider');
  }
  return context;
}

export default function PreferencesProvider({ children }: PreferencesProviderProps) {
  const preferencesContext = usePreferences();

  return (
    <PreferencesContext.Provider value={preferencesContext}>
      {children}
    </PreferencesContext.Provider>
  );
} 
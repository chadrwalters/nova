import { useState, useMemo } from 'react';
import { Typography, Grid, Paper } from '@mui/material';
import AlertStatus from '../components/alerts/AlertStatus';
import AlertTable from '../components/alerts/AlertTable';
import AlertSearch, { AlertFilters } from '../components/alerts/AlertSearch';
import { useAlerts } from '../hooks/useAlerts';
import { Alert } from '../types/api';

interface SavedSearch {
  id: string;
  name: string;
  filters: AlertFilters;
}

export default function AlertsPage() {
  const { currentAlerts, alertHistory, alertGroups, alertTrends } = useAlerts();
  const [filters, setFilters] = useState<AlertFilters>({
    searchQuery: '',
    severities: [],
    statuses: [],
    components: [],
    types: [],
  });
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>(() => {
    const saved = localStorage.getItem('savedAlertSearches');
    return saved ? JSON.parse(saved) : [];
  });

  const filterAlerts = (alerts: Alert[]) => {
    return alerts.filter(alert => {
      const matchesQuery = !filters.searchQuery || 
        alert.message.toLowerCase().includes(filters.searchQuery.toLowerCase()) ||
        alert.component.toLowerCase().includes(filters.searchQuery.toLowerCase()) ||
        alert.type.toLowerCase().includes(filters.searchQuery.toLowerCase());

      const matchesSeverity = filters.severities.length === 0 || 
        filters.severities.includes(alert.severity);

      const matchesStatus = filters.statuses.length === 0 || 
        filters.statuses.includes(alert.status);

      const matchesComponent = filters.components.length === 0 || 
        filters.components.includes(alert.component);

      const matchesType = filters.types.length === 0 || 
        filters.types.includes(alert.type);

      return matchesQuery && matchesSeverity && matchesStatus && matchesComponent && matchesType;
    });
  };

  const filteredCurrentAlerts = useMemo(() => 
    currentAlerts.data ? filterAlerts(currentAlerts.data) : [],
    [currentAlerts.data, filters]
  );

  const filteredAlertHistory = useMemo(() => 
    alertHistory.data ? filterAlerts(alertHistory.data) : [],
    [alertHistory.data, filters]
  );

  const handleSearch = (newFilters: AlertFilters) => {
    setFilters(newFilters);
  };

  const handleSaveSearch = (search: SavedSearch) => {
    const newSavedSearches = [...savedSearches, search];
    setSavedSearches(newSavedSearches);
    localStorage.setItem('savedAlertSearches', JSON.stringify(newSavedSearches));
  };

  const handleDeleteSearch = (searchId: string) => {
    const newSavedSearches = savedSearches.filter(search => search.id !== searchId);
    setSavedSearches(newSavedSearches);
    localStorage.setItem('savedAlertSearches', JSON.stringify(newSavedSearches));
  };

  return (
    <div>
      <Typography variant="h4" gutterBottom>
        Alert Management
      </Typography>

      <Paper sx={{ p: 2, mb: 3 }}>
        <AlertSearch
          onSearch={handleSearch}
          savedSearches={savedSearches}
          onSaveSearch={handleSaveSearch}
          onDeleteSearch={handleDeleteSearch}
        />
      </Paper>

      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Current Alerts</Typography>
            {currentAlerts.data && (
              <AlertTable alerts={filteredCurrentAlerts} />
            )}
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Alert Groups</Typography>
            {alertGroups.data && (
              <div>
                {alertGroups.data.map(group => (
                  <div key={group.group_id}>
                    <Typography variant="subtitle1">
                      {group.alert_type} - {group.component}
                    </Typography>
                    <AlertTable
                      alerts={filterAlerts(group.alerts)}
                      showActions={false}
                    />
                  </div>
                ))}
              </div>
            )}
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Alert Trends</Typography>
            {alertTrends.data && (
              <div>
                {alertTrends.data.map(trend => (
                  <div key={`${trend.alert_type}-${trend.component}`}>
                    <Typography variant="body2" color="text.secondary">
                      {trend.alert_type} ({trend.component})
                      <br />
                      Count: {trend.alert_count}
                      <br />
                      Rate of Change: {trend.rate_of_change > 0 ? '+' : ''}{trend.rate_of_change}%
                    </Typography>
                  </div>
                ))}
              </div>
            )}
          </Paper>
        </Grid>
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Alert History</Typography>
            {alertHistory.data && (
              <AlertTable
                alerts={filteredAlertHistory}
                showActions={false}
              />
            )}
          </Paper>
        </Grid>
      </Grid>
    </div>
  );
} 
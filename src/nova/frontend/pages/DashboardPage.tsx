import { Typography, Grid, Paper } from '@mui/material';
import AlertStatus from '../components/alerts/AlertStatus';
import MemoryUsage from '../components/memory/MemoryUsage';
import { useAlerts } from '../hooks/useAlerts';
import { useMonitoring } from '../hooks/useMonitoring';

export default function DashboardPage() {
  const { currentAlerts } = useAlerts();
  const { vectorStoreMetrics, serviceErrors } = useMonitoring();

  return (
    <div>
      <Typography variant="h4" gutterBottom>
        Dashboard Overview
      </Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6} lg={3}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Alert Status</Typography>
            <AlertStatus />
          </Paper>
        </Grid>
        <Grid item xs={12} md={6} lg={3}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Memory Usage</Typography>
            <MemoryUsage />
          </Paper>
        </Grid>
        <Grid item xs={12} md={6} lg={3}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Vector Store</Typography>
            {vectorStoreMetrics.data && (
              <Typography variant="body2" color="text.secondary">
                Store Size: {vectorStoreMetrics.data.store_size.toLocaleString()} vectors
                <br />
                Search Latency: {vectorStoreMetrics.data.search_latency.toFixed(2)}ms
                <br />
                Search Count: {vectorStoreMetrics.data.search_count.toLocaleString()}
              </Typography>
            )}
          </Paper>
        </Grid>
        <Grid item xs={12} md={6} lg={3}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Service Health</Typography>
            {serviceErrors.data && (
              <Typography variant="body2" color="text.secondary">
                API Errors: {serviceErrors.data.api_errors}
                <br />
                Rate Limits Remaining: {serviceErrors.data.rate_limits_remaining}
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </div>
  );
} 
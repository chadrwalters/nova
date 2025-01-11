import { Box, Typography, Stack, Chip } from '@mui/material';
import { useAlerts } from '../../hooks/useAlerts';

export default function AlertStatus() {
  const { alertSummary } = useAlerts();
  
  if (!alertSummary.data) {
    return (
      <Box>
        <Typography color="text.secondary">Loading alert status...</Typography>
      </Box>
    );
  }

  const { total_alerts, active_alerts, acknowledged_alerts, resolved_alerts } = alertSummary.data;

  return (
    <Box>
      <Stack spacing={1}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="body2" color="text.secondary">Total Alerts</Typography>
          <Chip label={total_alerts} color="default" size="small" />
        </Box>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="body2" color="text.secondary">Active</Typography>
          <Chip label={active_alerts} color="error" size="small" />
        </Box>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="body2" color="text.secondary">Acknowledged</Typography>
          <Chip label={acknowledged_alerts} color="warning" size="small" />
        </Box>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="body2" color="text.secondary">Resolved</Typography>
          <Chip label={resolved_alerts} color="success" size="small" />
        </Box>
      </Stack>
    </Box>
  );
} 
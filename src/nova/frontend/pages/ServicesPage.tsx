import { Box, Typography, Grid, Paper } from '@mui/material';
import RateLimits from '../components/services/RateLimits';
import ErrorMetrics from '../components/services/ErrorMetrics';
import ServiceHealth from '../components/services/ServiceHealth';

export default function ServicesPage() {
  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Service Monitoring
      </Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Rate Limits
            </Typography>
            <RateLimits />
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Service Errors
            </Typography>
            <ErrorMetrics />
          </Paper>
        </Grid>
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Service Health
            </Typography>
            <ServiceHealth />
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
} 
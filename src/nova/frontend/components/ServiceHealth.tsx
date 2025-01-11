import { Box, Card, CardContent, FormControl, InputLabel, MenuItem, Select, Typography } from '@mui/material';
import { useEffect, useState } from 'react';

export function ServiceHealth() {
  const [status, setStatus] = useState('all');
  const [isLoading, setIsLoading] = useState(true);

  // Simulate data loading
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  return (
    <Card data-testid="service-health" tabIndex={0} role="region" aria-label="Service Health Status">
      <CardContent>
        <Typography variant="h6" gutterBottom component="h2">
          Service Health Status
        </Typography>

        {isLoading ? (
          <Box sx={{ py: 2 }}>Loading service health data...</Box>
        ) : (
          <>
            <FormControl fullWidth margin="normal" data-testid="status-filter">
              <InputLabel id="status-filter-label">Filter by Status</InputLabel>
              <Select
                labelId="status-filter-label"
                id="status-filter"
                value={status}
                label="Filter by Status"
                onChange={(e) => setStatus(e.target.value)}
                aria-label="Filter services by status"
              >
                <MenuItem value="all">All Services</MenuItem>
                <MenuItem value="healthy">Healthy</MenuItem>
                <MenuItem value="warning">Warning</MenuItem>
                <MenuItem value="error">Error</MenuItem>
              </Select>
            </FormControl>

            <Box sx={{ mt: 2 }}>
              <Typography variant="body1" color="text.secondary" data-testid="uptime-value">
                Overall Uptime: 99.9%
              </Typography>
            </Box>
          </>
        )}
      </CardContent>
    </Card>
  );
}

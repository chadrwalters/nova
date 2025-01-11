import { Box, Card, CardContent, FormControl, InputLabel, MenuItem, Select, Typography } from '@mui/material';
import { useEffect, useState } from 'react';

export function ErrorMetrics() {
  const [severity, setStatus] = useState('all');
  const [isLoading, setIsLoading] = useState(true);

  // Simulate data loading
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  return (
    <Card data-testid="error-metrics" tabIndex={0} role="region" aria-label="Error Metrics">
      <CardContent>
        <Typography variant="h6" gutterBottom component="h2">
          Error Metrics
        </Typography>

        {isLoading ? (
          <Box sx={{ py: 2 }}>Loading error metrics...</Box>
        ) : (
          <>
            <FormControl fullWidth margin="normal" data-testid="severity-filter">
              <InputLabel id="severity-filter-label">Filter by Severity</InputLabel>
              <Select
                labelId="severity-filter-label"
                id="severity-filter"
                value={severity}
                label="Filter by Severity"
                onChange={(e) => setStatus(e.target.value)}
                aria-label="Filter errors by severity"
              >
                <MenuItem value="all">All Severities</MenuItem>
                <MenuItem value="low">Low</MenuItem>
                <MenuItem value="medium">Medium</MenuItem>
                <MenuItem value="high">High</MenuItem>
                <MenuItem value="critical">Critical</MenuItem>
              </Select>
            </FormControl>

            <Box sx={{ mt: 2 }}>
              <Typography variant="body1" color="text.secondary" data-testid="error-rate">
                Error Rate: 0.1%
              </Typography>
            </Box>
          </>
        )}
      </CardContent>
    </Card>
  );
}

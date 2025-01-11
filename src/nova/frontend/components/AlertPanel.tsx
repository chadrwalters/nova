import { Box, Card, CardContent, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from '@mui/material';
import { useEffect, useState } from 'react';

export function AlertPanel() {
  const [isLoading, setIsLoading] = useState(true);

  // Simulate data loading
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  return (
    <Card data-testid="alert-table" tabIndex={0} role="region" aria-label="Recent Alerts">
      <CardContent>
        <Typography variant="h6" gutterBottom component="h2">
          Recent Alerts
        </Typography>

        {isLoading ? (
          <Box sx={{ py: 2 }}>Loading alerts...</Box>
        ) : (
          <TableContainer>
            <Table aria-label="alerts table">
              <TableHead>
                <TableRow>
                  <TableCell>Time</TableCell>
                  <TableCell>Severity</TableCell>
                  <TableCell>Message</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow hover>
                  <TableCell data-testid="alert-time">2024-01-20 10:30 AM</TableCell>
                  <TableCell>High</TableCell>
                  <TableCell data-testid="alert-message">CPU usage exceeded threshold</TableCell>
                  <TableCell>Active</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </CardContent>
    </Card>
  );
}

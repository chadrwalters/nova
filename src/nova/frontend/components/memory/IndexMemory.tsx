import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  LinearProgress,
} from '@mui/material';
import { useMonitoring } from '../../hooks/useMonitoring';

function formatBytes(bytes: number) {
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex++;
  }

  return `${value.toFixed(2)} ${units[unitIndex]}`;
}

export default function IndexMemory() {
  const { indexMemory } = useMonitoring();

  if (!indexMemory.data) {
    return (
      <Box>
        <Typography color="text.secondary">Loading index memory usage...</Typography>
      </Box>
    );
  }

  const totalMemory = Object.values(indexMemory.data).reduce((sum, usage) => sum + usage, 0);

  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Index</TableCell>
            <TableCell>Memory Usage</TableCell>
            <TableCell>Percentage</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {Object.entries(indexMemory.data).map(([index, usage]) => {
            const percentage = (usage / totalMemory) * 100;
            return (
              <TableRow key={index}>
                <TableCell>{index}</TableCell>
                <TableCell>{formatBytes(usage)}</TableCell>
                <TableCell sx={{ width: '40%' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <LinearProgress
                      variant="determinate"
                      value={percentage}
                      sx={{ flexGrow: 1 }}
                    />
                    <Typography variant="body2" color="text.secondary">
                      {percentage.toFixed(1)}%
                    </Typography>
                  </Box>
                </TableCell>
              </TableRow>
            );
          })}
          <TableRow>
            <TableCell><strong>Total</strong></TableCell>
            <TableCell colSpan={2}><strong>{formatBytes(totalMemory)}</strong></TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </TableContainer>
  );
} 
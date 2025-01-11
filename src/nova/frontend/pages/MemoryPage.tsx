import { Typography, Grid, Paper } from '@mui/material';
import MemoryUsage from '../components/memory/MemoryUsage';
import IndexMemory from '../components/memory/IndexMemory';
import MemoryPressure from '../components/memory/MemoryPressure';

export default function MemoryPage() {
  return (
    <div>
      <Typography variant="h4" gutterBottom>
        Memory Monitoring
      </Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>System Memory</Typography>
            <MemoryUsage />
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Memory Pressure History</Typography>
            <MemoryPressure />
          </Paper>
        </Grid>
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Index Memory Usage</Typography>
            <IndexMemory />
          </Paper>
        </Grid>
      </Grid>
    </div>
  );
} 
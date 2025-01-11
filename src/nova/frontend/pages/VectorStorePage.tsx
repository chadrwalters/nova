import { Typography, Grid, Paper } from '@mui/material';
import VectorStoreSize from '../components/vectorstore/VectorStoreSize';
import SearchPerformance from '../components/vectorstore/SearchPerformance';
import IndexMemory from '../components/memory/IndexMemory';

export default function VectorStorePage() {
  return (
    <div>
      <Typography variant="h4" gutterBottom>
        Vector Store Monitoring
      </Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Store Size</Typography>
            <VectorStoreSize />
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Search Performance</Typography>
            <SearchPerformance />
          </Paper>
        </Grid>
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Memory Usage</Typography>
            <IndexMemory />
          </Paper>
        </Grid>
      </Grid>
    </div>
  );
} 
import SettingsIcon from '@mui/icons-material/Settings';
import { AppBar, Box, Container, CssBaseline, Dialog, DialogContent, DialogTitle, FormControl, IconButton, InputLabel, MenuItem, Select, SelectChangeEvent, ThemeProvider, Toolbar, Typography } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { AlertPanel } from './components/AlertPanel';
import { ErrorMetrics } from './components/ErrorMetrics';
import { ServiceHealth } from './components/ServiceHealth';
import { theme } from './theme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function Dashboard() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState('30');

  const handleRefreshChange = (
    event: SelectChangeEvent<unknown>,
    child: React.ReactNode
  ) => {
    const value = event.target.value;
    if (typeof value === 'string') {
      setRefreshInterval(value);
    }
  };

  return (
    <>
      <AppBar position="static" sx={{ mb: 2, bgcolor: 'primary.main' }}>
        <Toolbar>
          <Box sx={{ flexGrow: 1 }}>
            <Typography
              variant="h6"
              component="h1"
              sx={{
                color: '#fff',
                fontWeight: 500,
                mb: 0.5
              }}
            >
              Nova Dashboard
            </Typography>
            <Typography
              variant="subtitle1"
              sx={{
                color: '#fff',
                opacity: 0.9,
                fontWeight: 400,
                letterSpacing: '0.5px'
              }}
            >
              Real-time System Monitoring
            </Typography>
          </Box>
          <IconButton
            color="inherit"
            aria-label="open settings"
            onClick={() => setSettingsOpen(true)}
            sx={{ ml: 2 }}
          >
            <SettingsIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Dialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        aria-labelledby="settings-dialog-title"
      >
        <DialogTitle id="settings-dialog-title">Dashboard Settings</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel id="refresh-interval-label">Refresh Interval</InputLabel>
            <Select
              labelId="refresh-interval-label"
              value={refreshInterval}
              label="Refresh Interval"
              onChange={handleRefreshChange}
            >
              <MenuItem value="15">15 seconds</MenuItem>
              <MenuItem value="30">30 seconds</MenuItem>
              <MenuItem value="60">1 minute</MenuItem>
              <MenuItem value="300">5 minutes</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
      </Dialog>

      <Box component="main" sx={{ flexGrow: 1, py: 4 }}>
        <Container maxWidth="lg">
          <Box sx={{ mb: 4, display: 'grid', gap: 4, gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' } }}>
            <ServiceHealth />
            <ErrorMetrics />
          </Box>
          <Box sx={{ mt: 4 }}>
            <AlertPanel />
          </Box>
        </Container>
      </Box>
    </>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Dashboard />
      </ThemeProvider>
    </QueryClientProvider>
  );
}

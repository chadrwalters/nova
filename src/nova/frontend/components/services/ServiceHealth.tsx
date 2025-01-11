import { Box, Typography, Chip, Paper, Grid, TextField, FormControl, InputLabel, Select, MenuItem, LinearProgress } from '@mui/material';
import type { ChipProps, LinearProgressProps } from '@mui/material';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { useMonitoring } from '../../hooks/useMonitoring';
import { useTimeRange } from '../../hooks/useTimeRange';
import { useFilterState } from '../../hooks/useFilterState';
import { useSavedSearches } from '../../hooks/useSavedSearches';
import { ServiceHealth as ServiceHealthType } from '../../types/api';
import ExportButton from '../common/ExportButton';
import TimeRangeSelector from '../common/TimeRangeSelector';
import SavedSearches from '../common/SavedSearches';
import LoadingSkeleton from '../common/LoadingSkeleton';
import { useTheme, useMediaQuery } from '@mui/material';
import HelpTooltip from '../common/HelpTooltip';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

type ComponentStatus = {
  status: 'healthy' | 'degraded' | 'unhealthy';
  last_error?: string;
  uptime_percentage: number;
};

type ChipColor = 'success' | 'warning' | 'error' | 'default';
type ProgressColor = 'success' | 'warning' | 'error' | 'primary';
type StatusColorType = 'chip' | 'progress';

function getChipColor(status: ComponentStatus['status']): ChipProps['color'] {
  switch (status) {
    case 'healthy':
      return 'success';
    case 'degraded':
      return 'warning';
    case 'unhealthy':
      return 'error';
    default:
      return 'default';
  }
}

function getProgressColor(status: ComponentStatus['status']): LinearProgressProps['color'] {
  switch (status) {
    case 'healthy':
      return 'success';
    case 'degraded':
      return 'warning';
    case 'unhealthy':
      return 'error';
    default:
      return 'primary';
  }
}

const options = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top' as const,
    },
    title: {
      display: false,
    },
  },
  scales: {
    y: {
      beginAtZero: true,
      max: 100,
      title: {
        display: true,
        text: 'Uptime %',
      },
    },
  },
};

export default function ServiceHealth() {
  const { serviceHealth } = useMonitoring();
  const { timeRange, setTimeRange, filterDataByTimeRange } = useTimeRange();
  const { filters, updateFilter } = useFilterState('serviceHealth');
  const { savedSearches, saveSearch, deleteSearch, updateSearch } = useSavedSearches('serviceHealth');
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const isTablet = useMediaQuery(theme.breakpoints.down('md'));

  if (!serviceHealth.data) {
    return (
      <Box sx={{ width: '100%' }}>
        <Box sx={{ mb: 3 }}>
          <LoadingSkeleton variant="metrics" height={60} />
        </Box>
        <Box sx={{ mb: 3 }}>
          <Grid container spacing={2}>
            {[...Array(6)].map((_, i) => (
              <Grid item xs={12} sm={6} md={4} key={i}>
                <LoadingSkeleton variant="metrics" height={100} />
              </Grid>
            ))}
          </Grid>
        </Box>
        <LoadingSkeleton variant="chart" />
      </Box>
    );
  }

  const { timestamps, metrics } = filterDataByTimeRange(
    serviceHealth.data.uptime_history.timestamps,
    { uptime: serviceHealth.data.uptime_history.values }
  );

  const data = {
    labels: timestamps,
    datasets: [
      {
        label: 'Overall Uptime',
        data: metrics.uptime,
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
      },
    ],
  };

  const filteredComponents = Object.entries(serviceHealth.data.component_status)
    .filter(([component, status]) => {
      const matchesStatus = filters.statusFilter === 'all' || status.status === filters.statusFilter;
      const matchesSearch = component.toLowerCase().includes(filters.searchQuery.toLowerCase());
      return matchesStatus && matchesSearch;
    });

  return (
    <Box sx={{ width: '100%' }}>
      <Paper sx={{ p: { xs: 2, sm: 3 }, mb: 3 }}>
        <Box 
          sx={{ 
            display: 'flex', 
            flexDirection: { xs: 'column', sm: 'row' },
            justifyContent: 'space-between', 
            alignItems: { xs: 'stretch', sm: 'center' },
            gap: 2,
            mb: 3 
          }}
        >
          <Box>
            <Typography variant="h6" gutterBottom>
              Service Health Overview
              <HelpTooltip
                title="Service Health Overview"
                description="Monitor the health status and uptime of all system components. The health score indicates overall system stability."
              />
            </Typography>
            <Typography variant="body1" color={serviceHealth.data.health_score < 90 ? 'error.main' : 'success.main'}>
              Health Score: {serviceHealth.data.health_score.toFixed(2)}%
              <HelpTooltip
                title="Health Score"
                description="Aggregate score based on component status and uptime. Score below 90% indicates system issues that need attention."
                placement="right"
              />
            </Typography>
          </Box>
          <Box 
            sx={{ 
              display: 'flex', 
              gap: 2,
              flexDirection: { xs: 'column', sm: 'row' },
              alignItems: { xs: 'stretch', sm: 'center' }
            }}
          >
            <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
            <ExportButton
              filename="service_health"
              timestamps={timestamps}
              metrics={{
                uptime: metrics.uptime,
              }}
            />
          </Box>
        </Box>

        <Box 
          sx={{ 
            display: 'flex', 
            flexDirection: { xs: 'column', sm: 'row' },
            gap: 2, 
            mb: 3 
          }}
        >
          <FormControl 
            size="small" 
            sx={{ 
              minWidth: { xs: '100%', sm: 120 },
              flexShrink: 0
            }}
          >
            <InputLabel>Status</InputLabel>
            <Select
              value={filters.statusFilter}
              label="Status"
              onChange={(e) => updateFilter({ statusFilter: e.target.value })}
            >
              <MenuItem value="all">
                All
                <HelpTooltip
                  title="All Components"
                  description="Show components in all states: healthy, degraded, and unhealthy."
                  placement="right"
                />
              </MenuItem>
              <MenuItem value="healthy">
                Healthy
                <HelpTooltip
                  title="Healthy Components"
                  description="Components operating normally with high uptime."
                  placement="right"
                />
              </MenuItem>
              <MenuItem value="degraded">
                Degraded
                <HelpTooltip
                  title="Degraded Components"
                  description="Components experiencing minor issues or reduced performance."
                  placement="right"
                />
              </MenuItem>
              <MenuItem value="unhealthy">
                Unhealthy
                <HelpTooltip
                  title="Unhealthy Components"
                  description="Components with critical issues requiring immediate attention."
                  placement="right"
                />
              </MenuItem>
            </Select>
          </FormControl>
          <TextField
            size="small"
            label="Search components"
            value={filters.searchQuery}
            onChange={(e) => updateFilter({ searchQuery: e.target.value })}
            sx={{ flexGrow: 1 }}
            InputProps={{
              endAdornment: (
                <HelpTooltip
                  title="Component Search"
                  description="Search for specific components by name. The search is case-insensitive and matches partial names."
                />
              ),
            }}
          />
        </Box>

        <Box sx={{ mb: 3, overflowX: 'auto' }}>
          <SavedSearches
            componentKey="serviceHealth"
            currentFilters={filters}
            savedSearches={savedSearches}
            onSave={saveSearch}
            onDelete={deleteSearch}
            onLoad={updateFilter}
            onUpdate={updateSearch}
          />
        </Box>

        <Grid container spacing={2} sx={{ mb: 3 }}>
          {filteredComponents.map(([component, status]) => (
            <Grid item xs={12} sm={6} lg={4} key={component}>
              <Paper 
                elevation={2} 
                sx={{ 
                  p: { xs: 1.5, sm: 2 },
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column'
                }}
              >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography 
                    variant="subtitle2" 
                    sx={{ 
                      wordBreak: 'break-word',
                      mr: 1,
                      fontSize: { xs: '0.875rem', sm: '1rem' }
                    }}
                  >
                    {component}
                    <HelpTooltip
                      title={component}
                      description="View detailed status and uptime information for this component."
                      size="small"
                    />
                  </Typography>
                  <Chip
                    label={status.status}
                    color={getChipColor(status.status)}
                    size={isMobile ? "small" : "medium"}
                    sx={{ flexShrink: 0 }}
                  />
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 'auto' }}>
                  <Box sx={{ flexGrow: 1 }}>
                    <LinearProgress
                      variant="determinate"
                      value={status.uptime_percentage}
                      color={getProgressColor(status.status)}
                      sx={{ 
                        height: { xs: 6, sm: 8 }, 
                        borderRadius: { xs: 3, sm: 4 } 
                      }}
                    />
                  </Box>
                  <Typography 
                    variant="body2" 
                    color="text.secondary"
                    sx={{ flexShrink: 0, minWidth: 45 }}
                  >
                    {status.uptime_percentage.toFixed(1)}%
                    <HelpTooltip
                      title="Uptime Percentage"
                      description="Percentage of time the component has been operational in the selected time range."
                      placement="left"
                      size="small"
                    />
                  </Typography>
                </Box>
                {status.last_error && (
                  <Typography 
                    variant="caption" 
                    color="error.main" 
                    sx={{ 
                      mt: 1, 
                      display: 'block',
                      fontSize: { xs: '0.7rem', sm: '0.75rem' }
                    }}
                  >
                    Last error: {status.last_error}
                  </Typography>
                )}
              </Paper>
            </Grid>
          ))}
        </Grid>

        <Box 
          sx={{ 
            height: { xs: 250, sm: 300 },
            mt: { xs: 2, sm: 3 }
          }}
        >
          <Line options={options} data={data} />
        </Box>
      </Paper>
    </Box>
  );
} 
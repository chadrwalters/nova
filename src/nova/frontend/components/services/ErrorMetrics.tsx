import { Box, Typography, FormControl, InputLabel, Select, MenuItem, Stack, Chip, Paper } from '@mui/material';
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
import ExportButton from '../common/ExportButton';
import TimeRangeSelector from '../common/TimeRangeSelector';
import SavedSearches from '../common/SavedSearches';
import { AlertSeverity } from '../../types/api';
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

const ERROR_CATEGORIES = [
  'API',
  'Database',
  'Network',
  'Authentication',
  'Rate Limit',
  'Validation',
] as const;

type ErrorCategory = typeof ERROR_CATEGORIES[number];

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
      title: {
        display: true,
        text: 'Error Count',
      },
    },
  },
};

function getSeverityColor(severity: AlertSeverity) {
  switch (severity) {
    case AlertSeverity.CRITICAL:
      return 'error';
    case AlertSeverity.WARNING:
      return 'warning';
    case AlertSeverity.INFO:
      return 'info';
    default:
      return 'default';
  }
}

function getErrorCategoryDescription(category: ErrorCategory): string {
  switch (category) {
    case 'API':
      return 'Errors related to API requests and responses.';
    case 'Database':
      return 'Issues with database operations and connectivity.';
    case 'Network':
      return 'Network-related errors and connectivity issues.';
    case 'Authentication':
      return 'User authentication and authorization failures.';
    case 'Rate Limit':
      return 'Errors due to exceeding rate limits or quotas.';
    case 'Validation':
      return 'Input validation failures and data format errors.';
    default:
      return 'General system errors.';
  }
}

function getSeverityDescription(severity: AlertSeverity): string {
  switch (severity) {
    case AlertSeverity.CRITICAL:
      return 'Severe issues requiring immediate attention. System functionality is significantly impacted.';
    case AlertSeverity.WARNING:
      return 'Potential issues that may impact system performance or reliability.';
    case AlertSeverity.INFO:
      return 'Informational alerts about system events or minor issues.';
    default:
      return 'System alerts of varying importance.';
  }
}

export default function ErrorMetrics() {
  const { serviceErrors } = useMonitoring();
  const { timeRange, setTimeRange, filterDataByTimeRange } = useTimeRange();
  const { filters, updateFilter } = useFilterState('errorMetrics');
  const { savedSearches, saveSearch, deleteSearch, updateSearch } = useSavedSearches('errorMetrics');
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const isTablet = useMediaQuery(theme.breakpoints.down('md'));

  if (!serviceErrors.data) {
    return (
      <Box sx={{ width: '100%' }}>
        <Box sx={{ mb: 3 }}>
          <LoadingSkeleton variant="metrics" height={60} />
        </Box>
        <Box sx={{ mb: 3 }}>
          <LoadingSkeleton variant="metrics" height={100} />
        </Box>
        <LoadingSkeleton variant="chart" />
      </Box>
    );
  }

  const { timestamps, metrics } = filterDataByTimeRange(
    serviceErrors.data.timestamps,
    {
      error_count: serviceErrors.data.error_count_history,
      error_rate: serviceErrors.data.error_rate_history
    }
  );

  // Filter metrics based on selected categories and severities
  const filteredMetrics = {
    error_count: metrics.error_count.map((count, index) => {
      if (filters.selectedCategories.length === 0 && filters.selectedSeverities.length === 0) {
        return count;
      }
      // In a real implementation, we would filter based on the actual error categories and severities
      // This is a placeholder that reduces the count by 50% for each filter
      const categoryFactor = filters.selectedCategories.length ? 0.5 : 1;
      const severityFactor = filters.selectedSeverities.length ? 0.5 : 1;
      return Math.round(count * categoryFactor * severityFactor);
    }),
    error_rate: metrics.error_rate
  };

  const data = {
    labels: timestamps,
    datasets: [
      {
        label: 'Error Count',
        data: filteredMetrics.error_count,
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
      },
      {
        label: 'Error Rate (%)',
        data: filteredMetrics.error_rate,
        borderColor: 'rgb(255, 159, 64)',
        backgroundColor: 'rgba(255, 159, 64, 0.5)',
      },
    ],
  };

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
              Error Metrics Overview
              <HelpTooltip
                title="Error Metrics Overview"
                description="Monitor and analyze system errors across different categories and severity levels. Track error rates and identify patterns."
              />
            </Typography>
            <Box 
              sx={{ 
                display: 'flex', 
                flexDirection: { xs: 'column', sm: 'row' },
                gap: { xs: 1, sm: 2 }
              }}
            >
              <Typography
                variant="body1"
                color={serviceErrors.data.error_rate_history.slice(-1)[0] > 5 ? 'error.main' : 'text.secondary'}
              >
                Current Errors: {serviceErrors.data.api_errors}
                <HelpTooltip
                  title="Current Errors"
                  description="Total number of active errors in the system. High error counts may indicate system issues."
                  placement="bottom"
                />
              </Typography>
              <Typography
                variant="body1"
                color={serviceErrors.data.error_rate_history.slice(-1)[0] > 5 ? 'error.main' : 'text.secondary'}
              >
                Error Rate: {serviceErrors.data.error_rate_history.slice(-1)[0].toFixed(2)}%
                <HelpTooltip
                  title="Error Rate"
                  description="Percentage of requests resulting in errors. Rates above 5% indicate significant issues."
                  placement="bottom"
                />
              </Typography>
            </Box>
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
              filename="error_metrics"
              timestamps={timestamps}
              metrics={filteredMetrics}
            />
          </Box>
        </Box>

        <Stack 
          direction={{ xs: 'column', sm: 'row' }} 
          spacing={2} 
          sx={{ mb: 3 }}
        >
          <FormControl 
            size="small" 
            sx={{ 
              minWidth: { xs: '100%', sm: 200 },
              flexShrink: 0
            }}
          >
            <InputLabel>Error Categories</InputLabel>
            <Select
              multiple
              value={filters.selectedCategories}
              onChange={(e) => updateFilter({ selectedCategories: e.target.value as string[] })}
              label="Error Categories"
              renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selected.map((value) => (
                    <Chip key={value} label={value} size={isMobile ? "small" : "medium"} />
                  ))}
                </Box>
              )}
              endAdornment={
                <HelpTooltip
                  title="Error Categories"
                  description="Filter errors by their source or type. Select multiple categories to view combined metrics."
                  placement="bottom"
                />
              }
            >
              {ERROR_CATEGORIES.map((category) => (
                <MenuItem key={category} value={category}>
                  {category}
                  <HelpTooltip
                    title={`${category} Errors`}
                    description={getErrorCategoryDescription(category)}
                    placement="right"
                  />
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl 
            size="small" 
            sx={{ 
              minWidth: { xs: '100%', sm: 200 },
              flexShrink: 0
            }}
          >
            <InputLabel>Severity</InputLabel>
            <Select
              multiple
              value={filters.selectedSeverities}
              onChange={(e) => updateFilter({ selectedSeverities: e.target.value as AlertSeverity[] })}
              label="Severity"
              renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selected.map((value) => (
                    <Chip 
                      key={value} 
                      label={value} 
                      size={isMobile ? "small" : "medium"}
                      color={getSeverityColor(value)}
                    />
                  ))}
                </Box>
              )}
              endAdornment={
                <HelpTooltip
                  title="Error Severity"
                  description="Filter errors by their impact level. Critical errors require immediate attention."
                  placement="bottom"
                />
              }
            >
              {Object.values(AlertSeverity).map((severity) => (
                <MenuItem key={severity} value={severity}>
                  <Chip 
                    label={severity} 
                    size={isMobile ? "small" : "medium"}
                    color={getSeverityColor(severity)}
                    sx={{ mr: 1 }}
                  />
                  {severity}
                  <HelpTooltip
                    title={`${severity} Severity`}
                    description={getSeverityDescription(severity)}
                    placement="right"
                  />
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Stack>

        <Box sx={{ mb: 3, overflowX: 'auto' }}>
          <SavedSearches
            componentKey="errorMetrics"
            currentFilters={filters}
            savedSearches={savedSearches}
            onSave={saveSearch}
            onDelete={deleteSearch}
            onLoad={updateFilter}
            onUpdate={updateSearch}
          />
        </Box>

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
import { Box, Typography, LinearProgress } from '@mui/material';
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
import ExportButton from '../common/ExportButton';
import TimeRangeSelector from '../common/TimeRangeSelector';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

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
        text: 'Rate Limits Remaining',
      },
    },
  },
};

export default function RateLimits() {
  const { rateLimits } = useMonitoring();
  const { timeRange, setTimeRange, filterDataByTimeRange } = useTimeRange();

  if (!rateLimits.data) {
    return (
      <Box>
        <Typography color="text.secondary">Loading rate limit metrics...</Typography>
      </Box>
    );
  }

  const { timestamps, metrics } = filterDataByTimeRange(
    rateLimits.data.timestamps,
    { rate_limits_remaining: rateLimits.data.rate_limits_history }
  );

  const data = {
    labels: timestamps,
    datasets: [
      {
        label: 'Rate Limits Remaining',
        data: metrics.rate_limits_remaining,
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
      },
    ],
  };

  // Calculate percentage of rate limits remaining
  const percentage = (rateLimits.data.rate_limits_remaining / 1000) * 100; // Assuming max limit is 1000
  const isLow = percentage < 20;

  return (
    <Box>
      <Box sx={{ mb: 2 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Current Rate Limits
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            <Typography 
              variant="body2" 
              color={isLow ? 'error.main' : 'text.secondary'}
            >
              {rateLimits.data.rate_limits_remaining} remaining
            </Typography>
            <ExportButton
              filename="rate_limits"
              timestamps={timestamps}
              metrics={metrics}
            />
          </Box>
        </Box>
        <LinearProgress
          variant="determinate"
          value={percentage}
          color={isLow ? 'error' : 'primary'}
        />
        {isLow && (
          <Typography variant="caption" color="error" sx={{ mt: 0.5, display: 'block' }}>
            Rate limits running low
          </Typography>
        )}
      </Box>
      <Box display="flex" justifyContent="flex-end" sx={{ mb: 2 }}>
        <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
      </Box>
      <Box sx={{ height: 300 }}>
        <Line options={options} data={data} />
      </Box>
    </Box>
  );
} 
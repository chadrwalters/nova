import { Box, Typography } from '@mui/material';
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
        text: 'Latency (ms)',
      },
    },
  },
};

export default function SearchPerformance() {
  const { vectorStorePerformance } = useMonitoring();

  if (!vectorStorePerformance.data) {
    return (
      <Box>
        <Typography color="text.secondary">Loading search performance metrics...</Typography>
      </Box>
    );
  }

  const data = {
    labels: vectorStorePerformance.data.timestamps,
    datasets: [
      {
        label: 'Average Latency',
        data: vectorStorePerformance.data.latency_history,
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
      },
      {
        label: 'p95 Latency',
        data: vectorStorePerformance.data.p95_latency_history,
        borderColor: 'rgb(255, 159, 64)',
        backgroundColor: 'rgba(255, 159, 64, 0.5)',
      },
    ],
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Current Latency: {vectorStorePerformance.data.search_latency.toFixed(2)}ms
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Total Searches: {vectorStorePerformance.data.search_count.toLocaleString()}
        </Typography>
      </Box>
      <Box sx={{ height: 300 }}>
        <Line options={options} data={data} />
      </Box>
    </Box>
  );
} 
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
        text: 'Number of Vectors',
      },
    },
  },
};

export default function VectorStoreSize() {
  const { vectorStoreMetrics } = useMonitoring();

  if (!vectorStoreMetrics.data) {
    return (
      <Box>
        <Typography color="text.secondary">Loading vector store metrics...</Typography>
      </Box>
    );
  }

  const data = {
    labels: vectorStoreMetrics.data.timestamps,
    datasets: [
      {
        label: 'Total Vectors',
        data: vectorStoreMetrics.data.store_size_history,
        borderColor: 'rgb(53, 162, 235)',
        backgroundColor: 'rgba(53, 162, 235, 0.5)',
      },
    ],
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Current Size: {vectorStoreMetrics.data.store_size.toLocaleString()} vectors
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Growth Rate: {vectorStoreMetrics.data.growth_rate}%
        </Typography>
      </Box>
      <Box sx={{ height: 300 }}>
        <Line options={options} data={data} />
      </Box>
    </Box>
  );
} 
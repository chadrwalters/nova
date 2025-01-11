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
import { MemoryPressureData } from '../../types/api';

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
      max: 100,
      title: {
        display: true,
        text: 'Memory Pressure (%)',
      },
    },
  },
};

export default function MemoryPressure() {
  const { memoryPressure } = useMonitoring();

  if (!memoryPressure.data) {
    return (
      <Box>
        <Typography color="text.secondary">Loading memory pressure history...</Typography>
      </Box>
    );
  }

  const pressureData = memoryPressure.data as MemoryPressureData;

  const data = {
    labels: pressureData.timestamps.map((ts: string) => 
      new Date(ts).toLocaleTimeString()
    ),
    datasets: [
      {
        label: 'System Memory Pressure',
        data: pressureData.system_pressure,
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
      },
      {
        label: 'GPU Memory Pressure',
        data: pressureData.gpu_pressure,
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
      },
    ],
  };

  return (
    <Box sx={{ height: 300 }}>
      <Line options={options} data={data} />
    </Box>
  );
} 
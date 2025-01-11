import { Box, Typography, LinearProgress } from '@mui/material';
import { useMonitoring } from '../../hooks/useMonitoring';

function MemoryProgressBar({ used, total, label }: { used: number; total: number; label: string }) {
  const percentage = (used / total) * 100;
  const formattedUsed = (used / 1024 / 1024 / 1024).toFixed(2);
  const formattedTotal = (total / 1024 / 1024 / 1024).toFixed(2);

  return (
    <Box sx={{ mb: 2 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {formattedUsed}GB / {formattedTotal}GB
        </Typography>
      </Box>
      <LinearProgress
        variant="determinate"
        value={percentage}
        color={percentage > 90 ? 'error' : percentage > 70 ? 'warning' : 'primary'}
      />
    </Box>
  );
}

export default function MemoryUsage() {
  const { memorySummary } = useMonitoring();

  if (!memorySummary.data) {
    return (
      <Box>
        <Typography color="text.secondary">Loading memory usage...</Typography>
      </Box>
    );
  }

  const { system_memory_total, system_memory_used, gpu_memory_total, gpu_memory_used } = memorySummary.data;

  return (
    <Box>
      <MemoryProgressBar
        used={system_memory_used}
        total={system_memory_total}
        label="System Memory"
      />
      {gpu_memory_total > 0 && (
        <MemoryProgressBar
          used={gpu_memory_used}
          total={gpu_memory_total}
          label="GPU Memory"
        />
      )}
    </Box>
  );
} 
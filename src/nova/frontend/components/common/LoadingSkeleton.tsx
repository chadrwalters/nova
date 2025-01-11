import { Box, Skeleton, Paper } from '@mui/material';

interface LoadingSkeletonProps {
  variant?: 'chart' | 'table' | 'metrics' | 'status';
  height?: number | string;
}

export default function LoadingSkeleton({ variant = 'metrics', height }: LoadingSkeletonProps) {
  switch (variant) {
    case 'chart':
      return (
        <Box sx={{ width: '100%', height: height || 300 }}>
          <Skeleton variant="rectangular" width="100%" height="100%" />
        </Box>
      );

    case 'table':
      return (
        <Paper sx={{ width: '100%', overflow: 'hidden' }}>
          <Skeleton variant="rectangular" height={52} /> {/* Header */}
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} height={52} sx={{ transform: 'none' }} />
          ))}
        </Paper>
      );

    case 'metrics':
      return (
        <Box sx={{ width: '100%' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <Skeleton width={120} height={24} />
            <Skeleton width={80} height={24} />
          </Box>
          <Skeleton variant="rectangular" height={height || 100} />
        </Box>
      );

    case 'status':
      return (
        <Box sx={{ width: '100%' }}>
          {[...Array(4)].map((_, i) => (
            <Box key={i} sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Skeleton width={100} height={24} />
              <Skeleton width={60} height={24} />
            </Box>
          ))}
        </Box>
      );

    default:
      return <Skeleton variant="rectangular" width="100%" height={height || 100} />;
  }
} 
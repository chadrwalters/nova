import { Box, ToggleButton, ToggleButtonGroup, useTheme, useMediaQuery } from '@mui/material';

export type TimeRange = '1h' | '6h' | '24h' | '7d' | '30d';

interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
}

export default function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const handleChange = (_: React.MouseEvent<HTMLElement>, newRange: TimeRange) => {
    if (newRange !== null) {
      onChange(newRange);
    }
  };

  return (
    <Box sx={{ width: { xs: '100%', sm: 'auto' } }}>
      <ToggleButtonGroup
        value={value}
        exclusive
        onChange={handleChange}
        size={isMobile ? "small" : "medium"}
        aria-label="time range"
        sx={{
          width: { xs: '100%', sm: 'auto' },
          '& .MuiToggleButton-root': {
            flex: { xs: 1, sm: 'none' },
            px: { xs: 1, sm: 2 },
            py: { xs: 0.5, sm: 1 },
            fontSize: { xs: '0.75rem', sm: '0.875rem' }
          }
        }}
      >
        <ToggleButton value="1h" aria-label="1 hour">
          1h
        </ToggleButton>
        <ToggleButton value="6h" aria-label="6 hours">
          6h
        </ToggleButton>
        <ToggleButton value="24h" aria-label="24 hours">
          24h
        </ToggleButton>
        <ToggleButton value="7d" aria-label="7 days">
          7d
        </ToggleButton>
        <ToggleButton value="30d" aria-label="30 days">
          30d
        </ToggleButton>
      </ToggleButtonGroup>
    </Box>
  );
} 
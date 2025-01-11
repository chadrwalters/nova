import { Button, useTheme, useMediaQuery } from '@mui/material';
import { Download as DownloadIcon } from '@mui/icons-material';

interface ExportButtonProps {
  filename: string;
  timestamps: string[];
  metrics: Record<string, number[]>;
}

export default function ExportButton({ filename, timestamps, metrics }: ExportButtonProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const handleExport = () => {
    const rows = [
      ['Timestamp', ...Object.keys(metrics)],
      ...timestamps.map((timestamp, index) => [
        timestamp,
        ...Object.values(metrics).map(values => values[index].toString())
      ])
    ];

    const csvContent = rows.map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `${filename}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Button
      variant="outlined"
      onClick={handleExport}
      startIcon={<DownloadIcon />}
      size={isMobile ? "small" : "medium"}
      sx={{
        width: { xs: '100%', sm: 'auto' },
        whiteSpace: 'nowrap',
        minWidth: { xs: 'unset', sm: 100 },
        px: { xs: 1, sm: 2 },
        py: { xs: 0.5, sm: 1 },
        fontSize: { xs: '0.75rem', sm: '0.875rem' }
      }}
    >
      {isMobile ? 'Export' : 'Export CSV'}
    </Button>
  );
} 
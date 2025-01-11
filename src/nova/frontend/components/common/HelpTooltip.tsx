import { Tooltip, IconButton, Typography, Box } from '@mui/material';
import { Help as HelpIcon } from '@mui/icons-material';

interface HelpTooltipProps {
  title: string;
  description?: string;
  placement?: 'top' | 'right' | 'bottom' | 'left';
  size?: 'small' | 'medium';
}

export default function HelpTooltip({ 
  title, 
  description, 
  placement = 'top',
  size = 'small'
}: HelpTooltipProps) {
  return (
    <Tooltip
      title={
        <Box sx={{ maxWidth: 300 }}>
          <Typography variant="subtitle2" component="div" gutterBottom>
            {title}
          </Typography>
          {description && (
            <Typography variant="body2" component="div">
              {description}
            </Typography>
          )}
        </Box>
      }
      placement={placement}
      arrow
    >
      <IconButton
        size={size}
        sx={{
          ml: 0.5,
          color: 'text.secondary',
          '&:hover': {
            color: 'primary.main',
          },
        }}
      >
        <HelpIcon fontSize={size} />
      </IconButton>
    </Tooltip>
  );
} 
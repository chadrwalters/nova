import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Chip,
  Tooltip,
  Box,
} from '@mui/material';
import {
  Check as ResolveIcon,
  Done as AcknowledgeIcon,
  CheckCircleOutline as CheckCircleOutlineIcon,
  Done as DoneIcon,
} from '@mui/icons-material';
import { useAlerts } from '../../hooks/useAlerts';
import { Alert, AlertStatus } from '../../types/api';
import LoadingSkeleton from '../common/LoadingSkeleton';
import HelpTooltip from '../common/HelpTooltip';

const getSeverityColor = (severity: string) => {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'error';
    case 'warning':
      return 'warning';
    case 'info':
      return 'info';
    default:
      return 'default';
  }
};

interface AlertTableProps {
  alerts: Alert[];
  showActions?: boolean;
  isLoading?: boolean;
}

export default function AlertTable({ alerts, showActions = true, isLoading = false }: AlertTableProps) {
  const { acknowledgeAlert, resolveAlert } = useAlerts();

  const handleAcknowledge = (alertId: string) => {
    acknowledgeAlert.mutate(alertId);
  };

  const handleResolve = (alertId: string) => {
    resolveAlert.mutate(alertId);
  };

  if (isLoading) {
    return <LoadingSkeleton variant="table" />;
  }

  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>
              Severity
              <HelpTooltip
                title="Alert Severity"
                description="Indicates the impact level of the alert. Critical alerts require immediate attention."
                placement="bottom"
              />
            </TableCell>
            <TableCell>
              Type
              <HelpTooltip
                title="Alert Type"
                description="Categorizes the alert based on its source or nature."
                placement="bottom"
              />
            </TableCell>
            <TableCell>
              Component
              <HelpTooltip
                title="Affected Component"
                description="The system component or service affected by this alert."
                placement="bottom"
              />
            </TableCell>
            <TableCell>
              Message
              <HelpTooltip
                title="Alert Message"
                description="Detailed description of the alert, including specific error information."
                placement="bottom"
              />
            </TableCell>
            <TableCell>
              Created At
              <HelpTooltip
                title="Creation Time"
                description="When the alert was first detected and created."
                placement="bottom"
              />
            </TableCell>
            <TableCell>
              Status
              <HelpTooltip
                title="Alert Status"
                description="Current state of the alert. Alerts can be active, acknowledged, or resolved."
                placement="bottom"
              />
            </TableCell>
            {showActions && <TableCell width="10%" align="right">Actions</TableCell>}
          </TableRow>
        </TableHead>
        <TableBody>
          {alerts.map((alert) => (
            <TableRow key={alert.alert_id} hover>
              <TableCell>
                <Chip
                  label={alert.severity}
                  color={getSeverityColor(alert.severity)}
                  size="small"
                  sx={{ minWidth: 80 }}
                />
              </TableCell>
              <TableCell>{alert.type}</TableCell>
              <TableCell>{alert.component}</TableCell>
              <TableCell sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {alert.message}
              </TableCell>
              <TableCell>
                {new Date(alert.created_at).toLocaleString()}
              </TableCell>
              <TableCell>
                {alert.status === AlertStatus.ACTIVE ? 'Active' : alert.status === AlertStatus.ACKNOWLEDGED ? 'Acknowledged' : 'Resolved'}
              </TableCell>
              {showActions && (
                <TableCell align="right">
                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                    <Tooltip title="Acknowledge Alert">
                      <span>
                        <IconButton
                          size="small"
                          onClick={() => handleAcknowledge(alert.alert_id)}
                          disabled={alert.status !== AlertStatus.ACTIVE}
                        >
                          <CheckCircleOutlineIcon />
                        </IconButton>
                        <HelpTooltip
                          title="Acknowledge Alert"
                          description="Mark the alert as acknowledged, indicating that someone is investigating the issue."
                          placement="left"
                          size="small"
                        />
                      </span>
                    </Tooltip>
                    <Tooltip title="Resolve Alert">
                      <span>
                        <IconButton
                          size="small"
                          onClick={() => handleResolve(alert.alert_id)}
                          disabled={alert.status === AlertStatus.RESOLVED}
                        >
                          <DoneIcon />
                        </IconButton>
                        <HelpTooltip
                          title="Resolve Alert"
                          description="Mark the alert as resolved, indicating that the issue has been fixed."
                          placement="left"
                          size="small"
                        />
                      </span>
                    </Tooltip>
                  </Box>
                </TableCell>
              )}
            </TableRow>
          ))}
          {alerts.length === 0 && (
            <TableRow>
              <TableCell colSpan={showActions ? 6 : 5} align="center">
                No alerts found
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
} 
import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Tabs,
  Tab,
  Box,
  TextField,
  Switch,
  FormControlLabel,
  Typography,
  Slider,
  Chip,
  IconButton,
  Grid,
  Paper,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  DragIndicator as DragIcon,
} from '@mui/icons-material';
import { usePreferencesContext } from './PreferencesProvider';
import { useTheme } from '../../hooks/useTheme';
import { AlertThreshold, MetricGroup } from '../../hooks/usePreferences';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`preferences-tabpanel-${index}`}
      aria-labelledby={`preferences-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

interface PreferencesDialogProps {
  open: boolean;
  onClose: () => void;
}

export default function PreferencesDialog({ open, onClose }: PreferencesDialogProps) {
  const [activeTab, setActiveTab] = useState(0);
  const { mode, toggleTheme } = useTheme();
  const {
    preferences,
    updateLayout,
    updateTimeRange,
    updateAlertThresholds,
    updateMetricGroups,
    resetPreferences,
  } = usePreferencesContext();

  const [newThreshold, setNewThreshold] = useState<Partial<AlertThreshold>>({
    metric: '',
    warning: 0,
    critical: 0,
    enabled: true,
  });

  const [newGroup, setNewGroup] = useState<Partial<MetricGroup>>({
    name: '',
    metrics: [],
    color: '#1976d2',
  });

  const handleAddThreshold = () => {
    if (newThreshold.metric && typeof newThreshold.warning === 'number' && typeof newThreshold.critical === 'number') {
      updateAlertThresholds([
        ...preferences.alertThresholds,
        {
          metric: newThreshold.metric,
          warning: newThreshold.warning,
          critical: newThreshold.critical,
          enabled: newThreshold.enabled ?? true,
        },
      ]);
      setNewThreshold({ metric: '', warning: 0, critical: 0, enabled: true });
    }
  };

  const handleAddGroup = () => {
    if (newGroup.name && newGroup.metrics) {
      updateMetricGroups([
        ...preferences.metricGroups,
        {
          id: Date.now().toString(),
          name: newGroup.name,
          metrics: newGroup.metrics,
          color: newGroup.color,
        },
      ]);
      setNewGroup({ name: '', metrics: [], color: '#1976d2' });
    }
  };

  const handleDeleteThreshold = (index: number) => {
    const newThresholds = [...preferences.alertThresholds];
    newThresholds.splice(index, 1);
    updateAlertThresholds(newThresholds);
  };

  const handleDeleteGroup = (groupId: string) => {
    updateMetricGroups(preferences.metricGroups.filter(group => group.id !== groupId));
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>User Preferences</DialogTitle>
      <DialogContent>
        <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
          <Tab label="Theme" />
          <Tab label="Layout" />
          <Tab label="Time Range" />
          <Tab label="Alert Thresholds" />
          <Tab label="Metric Groups" />
        </Tabs>

        <TabPanel value={activeTab} index={0}>
          <FormControlLabel
            control={
              <Switch
                checked={mode === 'dark'}
                onChange={toggleTheme}
              />
            }
            label="Dark Mode"
          />
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          <Typography variant="subtitle1" gutterBottom>
            Dashboard Layout
          </Typography>
          <Grid container spacing={2}>
            {Object.entries(preferences.layout).map(([key, config]) => (
              <Grid item xs={12} sm={6} key={key}>
                <Paper sx={{ p: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <DragIcon sx={{ mr: 1 }} />
                    <Typography variant="subtitle2">{key}</Typography>
                  </Box>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.visible}
                        onChange={(e) => updateLayout({ [key]: { visible: e.target.checked } })}
                      />
                    }
                    label="Visible"
                  />
                </Paper>
              </Grid>
            ))}
          </Grid>
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              Default Time Range
            </Typography>
            <TextField
              select
              fullWidth
              value={preferences.timeRange.defaultRange}
              onChange={(e) => updateTimeRange({ defaultRange: e.target.value })}
              SelectProps={{ native: true }}
            >
              <option value="1h">Last Hour</option>
              <option value="6h">Last 6 Hours</option>
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
            </TextField>
          </Box>
        </TabPanel>

        <TabPanel value={activeTab} index={3}>
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              Alert Thresholds
            </Typography>
            {preferences.alertThresholds.map((threshold, index) => (
              <Paper key={threshold.metric} sx={{ p: 2, mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
                    {threshold.metric}
                  </Typography>
                  <IconButton size="small" onClick={() => handleDeleteThreshold(index)}>
                    <DeleteIcon />
                  </IconButton>
                </Box>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <Typography gutterBottom>Warning Threshold</Typography>
                    <Slider
                      value={threshold.warning}
                      onChange={(_, value) => {
                        const newThresholds = [...preferences.alertThresholds];
                        newThresholds[index].warning = value as number;
                        updateAlertThresholds(newThresholds);
                      }}
                      min={0}
                      max={100}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography gutterBottom>Critical Threshold</Typography>
                    <Slider
                      value={threshold.critical}
                      onChange={(_, value) => {
                        const newThresholds = [...preferences.alertThresholds];
                        newThresholds[index].critical = value as number;
                        updateAlertThresholds(newThresholds);
                      }}
                      min={0}
                      max={100}
                    />
                  </Grid>
                </Grid>
                <FormControlLabel
                  control={
                    <Switch
                      checked={threshold.enabled}
                      onChange={(e) => {
                        const newThresholds = [...preferences.alertThresholds];
                        newThresholds[index].enabled = e.target.checked;
                        updateAlertThresholds(newThresholds);
                      }}
                    />
                  }
                  label="Enabled"
                />
              </Paper>
            ))}
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
              <TextField
                label="Metric"
                value={newThreshold.metric}
                onChange={(e) => setNewThreshold({ ...newThreshold, metric: e.target.value })}
              />
              <TextField
                type="number"
                label="Warning"
                value={newThreshold.warning}
                onChange={(e) => setNewThreshold({ ...newThreshold, warning: Number(e.target.value) })}
              />
              <TextField
                type="number"
                label="Critical"
                value={newThreshold.critical}
                onChange={(e) => setNewThreshold({ ...newThreshold, critical: Number(e.target.value) })}
              />
              <Button
                variant="contained"
                onClick={handleAddThreshold}
                disabled={!newThreshold.metric}
                startIcon={<AddIcon />}
              >
                Add Threshold
              </Button>
            </Box>
          </Box>
        </TabPanel>

        <TabPanel value={activeTab} index={4}>
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              Metric Groups
            </Typography>
            {preferences.metricGroups.map((group) => (
              <Paper key={group.id} sx={{ p: 2, mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
                    {group.name}
                  </Typography>
                  <IconButton size="small" onClick={() => handleDeleteGroup(group.id)}>
                    <DeleteIcon />
                  </IconButton>
                </Box>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {group.metrics.map((metric) => (
                    <Chip
                      key={metric}
                      label={metric}
                      onDelete={() => {
                        const newGroups = preferences.metricGroups.map(g =>
                          g.id === group.id
                            ? { ...g, metrics: g.metrics.filter(m => m !== metric) }
                            : g
                        );
                        updateMetricGroups(newGroups);
                      }}
                    />
                  ))}
                </Box>
              </Paper>
            ))}
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
              <TextField
                label="Group Name"
                value={newGroup.name}
                onChange={(e) => setNewGroup({ ...newGroup, name: e.target.value })}
              />
              <TextField
                label="Metrics (comma-separated)"
                value={newGroup.metrics?.join(', ')}
                onChange={(e) => setNewGroup({
                  ...newGroup,
                  metrics: e.target.value.split(',').map(m => m.trim()).filter(Boolean)
                })}
              />
              <Button
                variant="contained"
                onClick={handleAddGroup}
                disabled={!newGroup.name}
                startIcon={<AddIcon />}
              >
                Add Group
              </Button>
            </Box>
          </Box>
        </TabPanel>
      </DialogContent>
      <DialogActions>
        <Button onClick={resetPreferences} color="error">
          Reset All
        </Button>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
} 
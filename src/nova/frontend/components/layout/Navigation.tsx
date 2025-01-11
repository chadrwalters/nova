import { useLocation, useNavigate } from 'react-router-dom';
import {
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  NotificationsActive as AlertsIcon,
  Memory as MemoryIcon,
  Storage as VectorStoreIcon,
  CloudQueue as ServicesIcon,
} from '@mui/icons-material';

const navigationItems = [
  { path: '/', label: 'Dashboard', icon: DashboardIcon },
  { path: '/alerts', label: 'Alerts', icon: AlertsIcon },
  { path: '/memory', label: 'Memory', icon: MemoryIcon },
  { path: '/vectorstore', label: 'Vector Store', icon: VectorStoreIcon },
  { path: '/services', label: 'Services', icon: ServicesIcon },
];

export default function Navigation() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <List>
      {navigationItems.map(({ path, label, icon: Icon }) => (
        <ListItem key={path} disablePadding>
          <ListItemButton
            selected={location.pathname === path}
            onClick={() => navigate(path)}
          >
            <ListItemIcon>
              <Icon />
            </ListItemIcon>
            <ListItemText primary={label} />
          </ListItemButton>
        </ListItem>
      ))}
      <Divider sx={{ my: 1 }} />
    </List>
  );
} 
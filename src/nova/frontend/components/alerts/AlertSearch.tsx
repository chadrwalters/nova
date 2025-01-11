import { useState } from 'react';
import {
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Save as SaveIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { AlertSeverity, AlertStatus, Alert } from '../../types/api';

interface AlertSearchProps {
  onSearch: (filters: AlertFilters) => void;
  savedSearches?: SavedSearch[];
  onSaveSearch?: (search: SavedSearch) => void;
  onDeleteSearch?: (searchId: string) => void;
}

export interface AlertFilters {
  searchQuery: string;
  severities: AlertSeverity[];
  statuses: AlertStatus[];
  components: string[];
  types: string[];
}

interface SavedSearch {
  id: string;
  name: string;
  filters: AlertFilters;
}

export default function AlertSearch({
  onSearch,
  savedSearches = [],
  onSaveSearch,
  onDeleteSearch,
}: AlertSearchProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSeverities, setSelectedSeverities] = useState<AlertSeverity[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<AlertStatus[]>([]);
  const [selectedComponents, setSelectedComponents] = useState<string[]>([]);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);

  const handleSearch = () => {
    onSearch({
      searchQuery,
      severities: selectedSeverities,
      statuses: selectedStatuses,
      components: selectedComponents,
      types: selectedTypes,
    });
  };

  const handleSaveSearch = () => {
    if (onSaveSearch) {
      onSaveSearch({
        id: Date.now().toString(),
        name: searchQuery || 'Unnamed Search',
        filters: {
          searchQuery,
          severities: selectedSeverities,
          statuses: selectedStatuses,
          components: selectedComponents,
          types: selectedTypes,
        },
      });
    }
  };

  const handleDeleteSearch = (searchId: string) => {
    if (onDeleteSearch) {
      onDeleteSearch(searchId);
    }
  };

  const handleLoadSearch = (search: SavedSearch) => {
    setSearchQuery(search.filters.searchQuery);
    setSelectedSeverities(search.filters.severities);
    setSelectedStatuses(search.filters.statuses);
    setSelectedComponents(search.filters.components);
    setSelectedTypes(search.filters.types);
    onSearch(search.filters);
  };

  return (
    <Box>
      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <TextField
          size="small"
          label="Search alerts"
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            handleSearch();
          }}
          sx={{ flexGrow: 1 }}
        />
        
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Severity</InputLabel>
          <Select
            multiple
            value={selectedSeverities}
            onChange={(e) => {
              setSelectedSeverities(e.target.value as AlertSeverity[]);
              handleSearch();
            }}
            label="Severity"
            renderValue={(selected) => (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {selected.map((value) => (
                  <Chip
                    key={value}
                    label={value}
                    size="small"
                    color={value === AlertSeverity.CRITICAL ? 'error' : value === AlertSeverity.WARNING ? 'warning' : 'info'}
                  />
                ))}
              </Box>
            )}
          >
            {Object.values(AlertSeverity).map((severity) => (
              <MenuItem key={severity} value={severity}>
                <Chip
                  label={severity}
                  size="small"
                  color={severity === AlertSeverity.CRITICAL ? 'error' : severity === AlertSeverity.WARNING ? 'warning' : 'info'}
                  sx={{ mr: 1 }}
                />
                {severity}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Status</InputLabel>
          <Select
            multiple
            value={selectedStatuses}
            onChange={(e) => {
              setSelectedStatuses(e.target.value as AlertStatus[]);
              handleSearch();
            }}
            label="Status"
            renderValue={(selected) => (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {selected.map((value) => (
                  <Chip key={value} label={value} size="small" />
                ))}
              </Box>
            )}
          >
            {Object.values(AlertStatus).map((status) => (
              <MenuItem key={status} value={status}>
                {status}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {onSaveSearch && (
          <Tooltip title="Save search">
            <IconButton onClick={handleSaveSearch} size="small">
              <SaveIcon />
            </IconButton>
          </Tooltip>
        )}
      </Stack>

      {savedSearches.length > 0 && (
        <Box sx={{ mb: 2 }}>
          {savedSearches.map((search) => (
            <Chip
              key={search.id}
              label={search.name}
              onClick={() => handleLoadSearch(search)}
              onDelete={() => handleDeleteSearch(search.id)}
              size="small"
              sx={{ mr: 1, mb: 1 }}
            />
          ))}
        </Box>
      )}
    </Box>
  );
} 
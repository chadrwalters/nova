import { useState } from 'react';
import {
  Box,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Chip,
  Typography,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  Save as SaveIcon,
  MoreVert as MoreIcon,
} from '@mui/icons-material';
import { SavedSearch } from '../../hooks/useSavedSearches';
import { FilterState } from '../../hooks/useFilterState';

interface SavedSearchesProps<K extends keyof FilterState> {
  componentKey: K;
  currentFilters: FilterState[K];
  savedSearches: SavedSearch[];
  onSave: (name: string, filters: FilterState[K]) => void;
  onDelete: (searchId: string) => void;
  onLoad: (filters: FilterState[K]) => void;
  onUpdate: (searchId: string, updates: Partial<SavedSearch>) => void;
}

export default function SavedSearches<K extends keyof FilterState>({
  componentKey,
  currentFilters,
  savedSearches,
  onSave,
  onDelete,
  onLoad,
  onUpdate,
}: SavedSearchesProps<K>) {
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [searchName, setSearchName] = useState('');
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [selectedSearch, setSelectedSearch] = useState<SavedSearch | null>(null);
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [newName, setNewName] = useState('');

  const handleSave = () => {
    if (searchName.trim()) {
      onSave(searchName.trim(), currentFilters);
      setSearchName('');
      setSaveDialogOpen(false);
    }
  };

  const handleOpenMenu = (event: React.MouseEvent<HTMLElement>, search: SavedSearch) => {
    setMenuAnchor(event.currentTarget);
    setSelectedSearch(search);
  };

  const handleCloseMenu = () => {
    setMenuAnchor(null);
    setSelectedSearch(null);
  };

  const handleRename = () => {
    if (selectedSearch && newName.trim()) {
      onUpdate(selectedSearch.id, { name: newName.trim() });
      setRenameDialogOpen(false);
      handleCloseMenu();
    }
  };

  const handleDelete = () => {
    if (selectedSearch) {
      onDelete(selectedSearch.id);
      handleCloseMenu();
    }
  };

  return (
    <>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
        <Tooltip title="Save current filters">
          <IconButton size="small" onClick={() => setSaveDialogOpen(true)}>
            <SaveIcon />
          </IconButton>
        </Tooltip>

        {savedSearches.map((search) => (
          <Box key={search.id} sx={{ display: 'flex', alignItems: 'center' }}>
            <Chip
              label={search.name}
              size="small"
              onClick={() => onLoad(search.filters as FilterState[K])}
              onDelete={() => onDelete(search.id)}
              sx={{ mr: 0.5 }}
            />
            <IconButton
              size="small"
              onClick={(e) => handleOpenMenu(e, search)}
              sx={{ padding: 0.5 }}
            >
              <MoreIcon fontSize="small" />
            </IconButton>
          </Box>
        ))}
      </Box>

      {/* Save Dialog */}
      <Dialog open={saveDialogOpen} onClose={() => setSaveDialogOpen(false)}>
        <DialogTitle>Save Search</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Search Name"
            fullWidth
            value={searchName}
            onChange={(e) => setSearchName(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} disabled={!searchName.trim()}>Save</Button>
        </DialogActions>
      </Dialog>

      {/* Search Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleCloseMenu}
      >
        <MenuItem onClick={() => {
          setRenameDialogOpen(true);
          handleCloseMenu();
          if (selectedSearch) {
            setNewName(selectedSearch.name);
          }
        }}>
          Rename
        </MenuItem>
        <MenuItem onClick={handleDelete}>Delete</MenuItem>
      </Menu>

      {/* Rename Dialog */}
      <Dialog open={renameDialogOpen} onClose={() => setRenameDialogOpen(false)}>
        <DialogTitle>Rename Search</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="New Name"
            fullWidth
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenameDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleRename} disabled={!newName.trim()}>Rename</Button>
        </DialogActions>
      </Dialog>
    </>
  );
} 
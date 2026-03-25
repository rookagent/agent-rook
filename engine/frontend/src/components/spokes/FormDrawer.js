/**
 * FormDrawer — slide-in panel for add/edit forms.
 */
import React from 'react';
import { Drawer, Box, Typography, Button, IconButton, CircularProgress } from '@mui/material';
import { Close } from '@mui/icons-material';

export default function FormDrawer({ open, onClose, title, onSave, loading, onDelete, children }) {
  return (
    <Drawer anchor="right" open={open} onClose={onClose}
      PaperProps={{ sx: { width: { xs: '100%', sm: 420 }, p: 3 } }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Typography sx={{ fontWeight: 700, fontSize: '1.1rem', flexGrow: 1 }}>{title}</Typography>
        <IconButton size="small" onClick={onClose}><Close /></IconButton>
      </Box>

      <Box sx={{ flexGrow: 1, overflowY: 'auto', mb: 2 }}>
        {children}
      </Box>

      <Box sx={{ display: 'flex', gap: 1 }}>
        {onDelete && (
          <Button color="error" onClick={onDelete} sx={{ mr: 'auto' }}>Delete</Button>
        )}
        <Button onClick={onClose} sx={{ ml: onDelete ? 0 : 'auto' }}>Cancel</Button>
        <Button variant="contained" onClick={onSave} disabled={loading}>
          {loading ? <CircularProgress size={20} /> : 'Save'}
        </Button>
      </Box>
    </Drawer>
  );
}

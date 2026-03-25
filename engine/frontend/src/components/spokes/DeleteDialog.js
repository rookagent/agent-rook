/**
 * DeleteDialog — confirmation before deleting a record.
 */
import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography } from '@mui/material';

export default function DeleteDialog({ open, onClose, onConfirm, itemName, labelSingular }) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Delete {labelSingular || 'Item'}</DialogTitle>
      <DialogContent>
        <Typography>
          Are you sure you want to delete{itemName ? ` "${itemName}"` : ` this ${(labelSingular || 'item').toLowerCase()}`}?
          This can't be undone.
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button color="error" variant="contained" onClick={onConfirm}>Delete</Button>
      </DialogActions>
    </Dialog>
  );
}

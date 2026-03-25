/**
 * ChecklistsPage — Interactive gear checklists with checkable items.
 * Create checklists for different shoot types, check items off, reuse them.
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Paper, Typography, Checkbox, IconButton, TextField, Button,
  Chip, Snackbar, Alert, MenuItem, LinearProgress,
} from '@mui/material';
import { Add, Delete, Close } from '@mui/icons-material';
import SpokePageShell from '../components/spokes/SpokePageShell';
import FormDrawer from '../components/spokes/FormDrawer';
import DeleteDialog from '../components/spokes/DeleteDialog';
import { checklistsApi } from '../services/spokeApi';

const SHOOT_TYPES = ['Wedding', 'Family', 'Newborn', 'Senior', 'Headshot', 'Mini Session', 'Elopement', 'Pet', 'Event', 'Other'];

export default function ChecklistsPage() {
  const [lists, setLists] = useState([]);
  const [activeList, setActiveList] = useState(null); // currently open checklist
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ title: '', shoot_type: '', notes: '' });
  const [newItem, setNewItem] = useState('');
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [snack, setSnack] = useState({ open: false, message: '', severity: 'success' });

  const fetchLists = useCallback(async () => {
    try {
      const data = await checklistsApi.list();
      setLists(data.items || []);
    } catch (_) {}
  }, []);

  useEffect(() => { fetchLists(); }, [fetchLists]);

  const openCreate = () => {
    setEditing(null);
    setForm({ title: '', shoot_type: '', notes: '' });
    setDrawerOpen(true);
  };

  const openEdit = (list) => {
    setEditing(list);
    setForm({ title: list.title, shoot_type: list.shoot_type || '', notes: list.notes || '' });
    setDrawerOpen(true);
  };

  const handleSave = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      if (editing) {
        await checklistsApi.update(editing.id, { ...form, items: editing.items });
        setSnack({ open: true, message: 'Checklist updated', severity: 'success' });
      } else {
        const created = await checklistsApi.create({ ...form, items: [] });
        setActiveList(created);
        setSnack({ open: true, message: 'Checklist created', severity: 'success' });
      }
      setDrawerOpen(false);
      fetchLists();
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await checklistsApi.delete(deleteTarget.id);
      if (activeList?.id === deleteTarget.id) setActiveList(null);
      setDeleteTarget(null);
      setDrawerOpen(false);
      fetchLists();
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    }
  };

  // Toggle an item's checked state
  const toggleItem = async (listObj, itemIndex) => {
    const items = [...listObj.items];
    items[itemIndex] = { ...items[itemIndex], checked: !items[itemIndex].checked };
    try {
      const updated = await checklistsApi.update(listObj.id, { items });
      setActiveList(updated);
      setLists(prev => prev.map(l => l.id === updated.id ? updated : l));
    } catch (_) {}
  };

  // Add a new item
  const addItem = async () => {
    if (!newItem.trim() || !activeList) return;
    const items = [...activeList.items, { name: newItem.trim(), checked: false }];
    try {
      const updated = await checklistsApi.update(activeList.id, { items });
      setActiveList(updated);
      setLists(prev => prev.map(l => l.id === updated.id ? updated : l));
      setNewItem('');
    } catch (_) {}
  };

  // Remove an item
  const removeItem = async (itemIndex) => {
    if (!activeList) return;
    const items = activeList.items.filter((_, i) => i !== itemIndex);
    try {
      const updated = await checklistsApi.update(activeList.id, { items });
      setActiveList(updated);
      setLists(prev => prev.map(l => l.id === updated.id ? updated : l));
    } catch (_) {}
  };

  const checkedCount = activeList ? activeList.items.filter(i => i.checked).length : 0;
  const totalCount = activeList ? activeList.items.length : 0;
  const progress = totalCount > 0 ? (checkedCount / totalCount) * 100 : 0;

  return (
    <SpokePageShell title="Gear Checklists" color="#B97A5B" onAdd={openCreate}>
      {/* If a checklist is open, show it */}
      {activeList ? (
        <Box>
          {/* Header */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Box sx={{ flexGrow: 1 }}>
              <Typography sx={{ fontWeight: 700, fontSize: '1.1rem' }}>{activeList.title}</Typography>
              {activeList.shoot_type && (
                <Chip label={activeList.shoot_type} size="small" sx={{ fontSize: '0.7rem', height: 22, mt: 0.5 }} />
              )}
            </Box>
            <Button size="small" onClick={() => openEdit(activeList)}>Edit</Button>
            <IconButton size="small" onClick={() => setActiveList(null)}><Close /></IconButton>
          </Box>

          {/* Progress */}
          {totalCount > 0 && (
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography sx={{ fontSize: '0.78rem', color: 'text.secondary' }}>
                  {checkedCount} of {totalCount} packed
                </Typography>
                <Typography sx={{ fontSize: '0.78rem', fontWeight: 600, color: progress === 100 ? '#66BB6A' : '#B97A5B' }}>
                  {Math.round(progress)}%
                </Typography>
              </Box>
              <LinearProgress variant="determinate" value={progress}
                sx={{ height: 6, borderRadius: 3, bgcolor: '#eee',
                  '& .MuiLinearProgress-bar': { bgcolor: progress === 100 ? '#66BB6A' : '#B97A5B', borderRadius: 3 } }} />
            </Box>
          )}

          {/* Items */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {activeList.items.map((item, idx) => (
              <Box key={idx} sx={{
                display: 'flex', alignItems: 'center', gap: 0.5,
                p: 1, borderRadius: 2, bgcolor: item.checked ? '#f5f5f5' : 'white',
                border: '1px solid', borderColor: 'divider',
              }}>
                <Checkbox checked={item.checked} onChange={() => toggleItem(activeList, idx)}
                  sx={{ p: 0.5, color: '#B97A5B', '&.Mui-checked': { color: '#66BB6A' } }} />
                <Typography sx={{
                  flexGrow: 1, fontSize: '0.9rem',
                  textDecoration: item.checked ? 'line-through' : 'none',
                  color: item.checked ? 'text.disabled' : 'text.primary',
                }}>
                  {item.name}
                </Typography>
                <IconButton size="small" onClick={() => removeItem(idx)} sx={{ opacity: 0.3, '&:hover': { opacity: 1 } }}>
                  <Delete sx={{ fontSize: 16 }} />
                </IconButton>
              </Box>
            ))}
          </Box>

          {/* Add item */}
          <Box sx={{ display: 'flex', gap: 1, mt: 1.5 }}>
            <TextField size="small" fullWidth placeholder="Add an item..."
              value={newItem} onChange={(e) => setNewItem(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addItem(); } }}
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }} />
            <IconButton onClick={addItem} disabled={!newItem.trim()}
              sx={{ bgcolor: '#B97A5B', color: 'white', '&:hover': { bgcolor: '#A06A4B' }, '&.Mui-disabled': { bgcolor: '#eee' } }}>
              <Add />
            </IconButton>
          </Box>
        </Box>
      ) : (
        /* List of all checklists */
        <>
          {lists.length === 0 && (
            <Paper elevation={0} sx={{ p: 4, textAlign: 'center', border: '1px dashed', borderColor: 'divider', borderRadius: 3 }}>
              <Typography color="text.secondary">No checklists yet. Create one for your next shoot!</Typography>
            </Paper>
          )}

          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' }, gap: 1.5 }}>
            {lists.map((list) => {
              const checked = list.items.filter(i => i.checked).length;
              const total = list.items.length;
              const pct = total > 0 ? Math.round((checked / total) * 100) : 0;
              return (
                <Paper key={list.id} elevation={0} onClick={() => setActiveList(list)}
                  sx={{
                    p: 2, borderRadius: 3, border: '1px solid', borderColor: 'divider', cursor: 'pointer',
                    position: 'relative',
                    transition: 'all 0.15s', '&:hover': { borderColor: '#B97A5B', transform: 'translateY(-2px)', boxShadow: 2 },
                  }}>
                  <IconButton size="small"
                    onClick={(e) => { e.stopPropagation(); setDeleteTarget(list); }}
                    sx={{ position: 'absolute', top: 8, right: 8, opacity: 0.25, '&:hover': { opacity: 1, color: 'error.main' }, p: 0.5 }}>
                    <Delete sx={{ fontSize: 16 }} />
                  </IconButton>
                  <Typography sx={{ fontWeight: 600, fontSize: '0.95rem', mb: 0.5 }}>{list.title}</Typography>
                  {list.shoot_type && (
                    <Chip label={list.shoot_type} size="small" sx={{ fontSize: '0.68rem', height: 20, mb: 1 }} />
                  )}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <LinearProgress variant="determinate" value={pct}
                      sx={{ flexGrow: 1, height: 4, borderRadius: 2, bgcolor: '#eee',
                        '& .MuiLinearProgress-bar': { bgcolor: pct === 100 ? '#66BB6A' : '#B97A5B', borderRadius: 2 } }} />
                    <Typography sx={{ fontSize: '0.72rem', color: 'text.secondary', fontWeight: 600, minWidth: 40, textAlign: 'right' }}>
                      {checked}/{total}
                    </Typography>
                  </Box>
                </Paper>
              );
            })}
          </Box>
        </>
      )}

      <FormDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)}
        title={editing ? 'Edit Checklist' : 'New Checklist'}
        onSave={handleSave} loading={saving}
        onDelete={editing ? () => setDeleteTarget(editing) : undefined}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField label="Title" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
            helperText="e.g. Wedding Day Kit, Mini Session Bag" />
          <TextField label="Shoot Type" select value={form.shoot_type}
            onChange={(e) => setForm({ ...form, shoot_type: e.target.value })}>
            <MenuItem value="">None</MenuItem>
            {SHOOT_TYPES.map(t => <MenuItem key={t} value={t}>{t}</MenuItem>)}
          </TextField>
          <TextField label="Notes" multiline rows={2} value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </Box>
      </FormDrawer>

      <DeleteDialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete} itemName={deleteTarget?.title} labelSingular="Checklist" />

      <Snackbar open={snack.open} autoHideDuration={3000} onClose={() => setSnack({ ...snack, open: false })}>
        <Alert severity={snack.severity} variant="filled">{snack.message}</Alert>
      </Snackbar>
    </SpokePageShell>
  );
}

/**
 * TasksPage — Todo list with status tabs and priority badges.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Box, Paper, Typography, Chip, IconButton, Checkbox, Snackbar, Alert, TextField, MenuItem } from '@mui/material';
import { Delete } from '@mui/icons-material';
import SpokePageShell from '../components/spokes/SpokePageShell';
import FormDrawer from '../components/spokes/FormDrawer';
import DeleteDialog from '../components/spokes/DeleteDialog';
import { tasksApi } from '../services/spokeApi';
import config from '../agentConfig.json';

const spoke = config.spokes?.tasks || { label: 'Tasks', label_singular: 'Task', color: '#66BB6A' };

const STATUS_TABS = [
  { key: 'pending', label: 'To Do' },
  { key: 'in_progress', label: 'In Progress' },
  { key: 'done', label: 'Done' },
];

const PRIORITY_COLORS = { high: '#E94560', medium: '#FFA726', low: '#90A4AE' };

export default function TasksPage() {
  const [items, setItems] = useState([]);
  const [activeTab, setActiveTab] = useState('pending');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ title: '', description: '', priority: 'medium', due_date: '', status: 'pending' });
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [snack, setSnack] = useState({ open: false, message: '', severity: 'success' });

  const fetchItems = useCallback(async () => {
    try {
      const data = await tasksApi.list({ sort: 'created_at' });
      setItems(data.items || []);
    } catch (_) {}
  }, []);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  const filtered = items.filter(t => t.status === activeTab);

  const openCreate = () => {
    setEditing(null);
    setForm({ title: '', description: '', priority: 'medium', due_date: '', status: 'pending' });
    setDrawerOpen(true);
  };

  const openEdit = (item) => {
    setEditing(item);
    setForm({
      title: item.title || '',
      description: item.description || '',
      priority: item.priority || 'medium',
      due_date: item.due_date || '',
      status: item.status || 'pending',
    });
    setDrawerOpen(true);
  };

  const handleSave = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      const payload = { ...form, due_date: form.due_date || null };
      if (editing) {
        await tasksApi.update(editing.id, payload);
      } else {
        await tasksApi.create(payload);
      }
      setDrawerOpen(false);
      fetchItems();
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const toggleDone = async (item) => {
    try {
      const newStatus = item.status === 'done' ? 'pending' : 'done';
      await tasksApi.update(item.id, { status: newStatus });
      fetchItems();
    } catch (_) {}
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await tasksApi.delete(deleteTarget.id);
      setDeleteTarget(null);
      setDrawerOpen(false);
      fetchItems();
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    }
  };

  return (
    <SpokePageShell title={spoke.label} color={spoke.color} onAdd={openCreate}>
      {/* Status tabs */}
      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        {STATUS_TABS.map((tab) => {
          const count = items.filter(t => t.status === tab.key).length;
          return (
            <Chip key={tab.key} label={`${tab.label} (${count})`}
              onClick={() => setActiveTab(tab.key)}
              sx={{
                fontWeight: 600, fontSize: '0.78rem', cursor: 'pointer',
                bgcolor: activeTab === tab.key ? spoke.color : 'transparent',
                color: activeTab === tab.key ? 'white' : 'text.secondary',
                border: '1px solid', borderColor: activeTab === tab.key ? spoke.color : 'divider',
              }} />
          );
        })}
      </Box>

      {filtered.length === 0 && (
        <Paper elevation={0} sx={{ p: 4, textAlign: 'center', border: '1px dashed', borderColor: 'divider', borderRadius: 3 }}>
          <Typography color="text.secondary">
            {activeTab === 'done' ? 'No completed tasks yet.' : 'Nothing here. Add a task!'}
          </Typography>
        </Paper>
      )}

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {filtered.map((item) => (
          <Paper key={item.id} elevation={0}
            sx={{
              p: 1.5, borderRadius: 2, border: '1px solid', borderColor: 'divider',
              display: 'flex', alignItems: 'center', gap: 1, position: 'relative',
              opacity: item.status === 'done' ? 0.6 : 1,
              '&:hover': { borderColor: spoke.color },
            }}>
            <IconButton size="small"
              onClick={(e) => { e.stopPropagation(); setDeleteTarget(item); }}
              sx={{ position: 'absolute', top: 8, right: 8, opacity: 0.25, '&:hover': { opacity: 1, color: '#E94560' } }}>
              <Delete sx={{ fontSize: 16 }} />
            </IconButton>
            <Checkbox checked={item.status === 'done'} onChange={() => toggleDone(item)}
              sx={{ p: 0.5, color: spoke.color, '&.Mui-checked': { color: spoke.color } }} />
            <Box sx={{ flexGrow: 1, cursor: 'pointer' }} onClick={() => openEdit(item)}>
              <Typography sx={{
                fontWeight: 600, fontSize: '0.9rem',
                textDecoration: item.status === 'done' ? 'line-through' : 'none',
              }}>
                {item.title}
              </Typography>
              {item.due_date && (
                <Typography sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                  Due {item.due_date}
                </Typography>
              )}
            </Box>
            <Box sx={{
              width: 8, height: 8, borderRadius: '50%',
              bgcolor: PRIORITY_COLORS[item.priority] || PRIORITY_COLORS.medium,
            }} title={`${item.priority} priority`} />
          </Paper>
        ))}
      </Box>

      <FormDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)}
        title={editing ? `Edit ${spoke.label_singular}` : `New ${spoke.label_singular}`}
        onSave={handleSave} loading={saving}
        onDelete={editing ? () => setDeleteTarget(editing) : undefined}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField label="Title" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <TextField label="Description" multiline rows={2} value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <TextField label="Priority" select value={form.priority}
            onChange={(e) => setForm({ ...form, priority: e.target.value })}>
            <MenuItem value="low">Low</MenuItem>
            <MenuItem value="medium">Medium</MenuItem>
            <MenuItem value="high">High</MenuItem>
          </TextField>
          <TextField label="Status" select value={form.status}
            onChange={(e) => setForm({ ...form, status: e.target.value })}>
            <MenuItem value="pending">To Do</MenuItem>
            <MenuItem value="in_progress">In Progress</MenuItem>
            <MenuItem value="done">Done</MenuItem>
          </TextField>
          <TextField label="Due Date" type="date" value={form.due_date}
            onChange={(e) => setForm({ ...form, due_date: e.target.value })}
            InputLabelProps={{ shrink: true }} />
        </Box>
      </FormDrawer>

      <DeleteDialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete} itemName={deleteTarget?.title} labelSingular={spoke.label_singular} />

      <Snackbar open={snack.open} autoHideDuration={3000} onClose={() => setSnack({ ...snack, open: false })}>
        <Alert severity={snack.severity} variant="filled">{snack.message}</Alert>
      </Snackbar>
    </SpokePageShell>
  );
}

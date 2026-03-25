/**
 * ClientsPage — Session/shoot tracker. Reuses the clients model but
 * configured as "Shoots" for photographers. Tracks client name, session type,
 * date, location, status, notes, tags.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Box, Paper, Typography, Chip, IconButton, Snackbar, Alert, TextField, MenuItem } from '@mui/material';
import { Delete } from '@mui/icons-material';
import SpokePageShell from '../components/spokes/SpokePageShell';
import FormDrawer from '../components/spokes/FormDrawer';
import DeleteDialog from '../components/spokes/DeleteDialog';
import { clientsApi } from '../services/spokeApi';
import config from '../agentConfig.json';

const spoke = config.spokes?.clients || { label: 'Shoots', label_singular: 'Shoot', color: '#E94560' };

const SESSION_TYPES = ['Wedding', 'Engagement', 'Family', 'Newborn', 'Baby Milestone', 'Senior', 'Headshot', 'Pet', 'Mini Session', 'Elopement', 'Maternity', 'Event', 'Other'];

export default function ClientsPage() {
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: '', email: '', phone: '', notes: '', tags: '' });
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [snack, setSnack] = useState({ open: false, message: '', severity: 'success' });

  const fetchItems = useCallback(async () => {
    try {
      const data = await clientsApi.list({ q: search, sort: 'created_at', order: 'desc' });
      setItems(data.items || []);
    } catch (_) {}
  }, [search]);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  const openCreate = () => {
    setEditing(null);
    setForm({ name: '', email: '', phone: '', notes: '', tags: '' });
    setDrawerOpen(true);
  };

  const openEdit = (item) => {
    setEditing(item);
    setForm({
      name: item.name || '',
      email: item.email || '',
      phone: item.phone || '',
      notes: item.notes || '',
      tags: (item.tags || []).join(', '),
    });
    setDrawerOpen(true);
  };

  const handleSave = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      const payload = {
        name: form.name,
        email: form.email,
        phone: form.phone,
        notes: form.notes,
        tags: form.tags ? form.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
      };
      if (editing) {
        await clientsApi.update(editing.id, payload);
        setSnack({ open: true, message: `${spoke.label_singular} updated`, severity: 'success' });
      } else {
        await clientsApi.create(payload);
        setSnack({ open: true, message: `${spoke.label_singular} added`, severity: 'success' });
      }
      setDrawerOpen(false);
      fetchItems();
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await clientsApi.delete(deleteTarget.id);
      setSnack({ open: true, message: `${spoke.label_singular} deleted`, severity: 'success' });
      setDeleteTarget(null);
      setDrawerOpen(false);
      fetchItems();
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    }
  };

  // Parse tags to extract session type for display
  const getSessionType = (item) => {
    const tags = item.tags || [];
    return tags.find(t => SESSION_TYPES.includes(t)) || null;
  };

  return (
    <SpokePageShell title={spoke.label} color={spoke.color} onAdd={openCreate}
      searchValue={search} onSearchChange={setSearch}>

      {items.length === 0 && (
        <Paper elevation={0} sx={{ p: 4, textAlign: 'center', border: '1px dashed', borderColor: 'divider', borderRadius: 3 }}>
          <Typography color="text.secondary">No {spoke.label.toLowerCase()} yet. Book your first one!</Typography>
        </Paper>
      )}

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {items.map((item) => {
          const sessionType = getSessionType(item);
          const otherTags = (item.tags || []).filter(t => t !== sessionType);
          return (
            <Paper key={item.id} elevation={0} onClick={() => openEdit(item)}
              sx={{
                p: 2, borderRadius: 3, border: '1px solid', borderColor: 'divider', cursor: 'pointer',
                transition: 'all 0.15s', position: 'relative',
                '&:hover': { borderColor: spoke.color, transform: 'translateY(-2px)', boxShadow: 2 },
              }}>
              <IconButton size="small"
                onClick={(e) => { e.stopPropagation(); setDeleteTarget(item); }}
                sx={{ position: 'absolute', top: 8, right: 8, opacity: 0.25, '&:hover': { opacity: 1, color: '#E94560' } }}>
                <Delete sx={{ fontSize: 16 }} />
              </IconButton>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ flexGrow: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography sx={{ fontWeight: 600, fontSize: '0.95rem' }}>{item.name}</Typography>
                    {sessionType && (
                      <Chip label={sessionType} size="small"
                        sx={{ fontSize: '0.68rem', height: 20, bgcolor: `${spoke.color}18`, color: spoke.color, fontWeight: 600 }} />
                    )}
                  </Box>
                  {(item.email || item.phone) && (
                    <Typography sx={{ fontSize: '0.8rem', color: 'text.secondary' }}>
                      {[item.email, item.phone].filter(Boolean).join(' · ')}
                    </Typography>
                  )}
                  {item.notes && (
                    <Typography sx={{ fontSize: '0.78rem', color: 'text.secondary', mt: 0.5,
                      overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 1, WebkitBoxOrient: 'vertical' }}>
                      {item.notes}
                    </Typography>
                  )}
                </Box>
                {otherTags.length > 0 && (
                  <Box sx={{ display: 'flex', gap: 0.5 }}>
                    {otherTags.slice(0, 2).map((tag) => (
                      <Chip key={tag} label={tag} size="small" sx={{ fontSize: '0.68rem', height: 20 }} />
                    ))}
                  </Box>
                )}
              </Box>
            </Paper>
          );
        })}
      </Box>

      <FormDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)}
        title={editing ? `Edit ${spoke.label_singular}` : `New ${spoke.label_singular}`}
        onSave={handleSave} loading={saving}
        onDelete={editing ? () => setDeleteTarget(editing) : undefined}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField label="Client Name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <TextField label="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <TextField label="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          <TextField label="Session Notes" multiline rows={3} value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            helperText="Location, special requests, shot ideas, etc." />
          <TextField label="Tags (comma separated)" value={form.tags}
            onChange={(e) => setForm({ ...form, tags: e.target.value })}
            helperText={`e.g. ${SESSION_TYPES.slice(0, 4).join(', ')}`} />
        </Box>
      </FormDrawer>

      <DeleteDialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete} itemName={deleteTarget?.name} labelSingular={spoke.label_singular} />

      <Snackbar open={snack.open} autoHideDuration={3000} onClose={() => setSnack({ ...snack, open: false })}>
        <Alert severity={snack.severity} variant="filled">{snack.message}</Alert>
      </Snackbar>
    </SpokePageShell>
  );
}

/**
 * NotesPage — Searchable, taggable markdown notes.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Box, Paper, Typography, Chip, IconButton, Snackbar, Alert, TextField } from '@mui/material';
import { PushPin, PushPinOutlined, Delete } from '@mui/icons-material';
import SpokePageShell from '../components/spokes/SpokePageShell';
import FormDrawer from '../components/spokes/FormDrawer';
import DeleteDialog from '../components/spokes/DeleteDialog';
import { notesApi } from '../services/spokeApi';
import config from '../agentConfig.json';

const spoke = config.spokes?.notes || { label: 'Notes', label_singular: 'Note', color: '#FFA726' };

export default function NotesPage() {
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ title: '', content: '', tags: '', is_pinned: false });
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [snack, setSnack] = useState({ open: false, message: '', severity: 'success' });

  const fetchItems = useCallback(async () => {
    try {
      const data = await notesApi.list({ q: search });
      setItems(data.items || []);
    } catch (_) {}
  }, [search]);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  const openCreate = () => {
    setEditing(null);
    setForm({ title: '', content: '', tags: '', is_pinned: false });
    setDrawerOpen(true);
  };

  const openEdit = (item) => {
    setEditing(item);
    setForm({
      title: item.title || '',
      content: item.content || '',
      tags: (item.tags || []).join(', '),
      is_pinned: item.is_pinned || false,
    });
    setDrawerOpen(true);
  };

  const handleSave = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      const payload = {
        title: form.title,
        content: form.content,
        tags: form.tags ? form.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
        is_pinned: form.is_pinned,
      };
      if (editing) {
        await notesApi.update(editing.id, payload);
      } else {
        await notesApi.create(payload);
      }
      setDrawerOpen(false);
      fetchItems();
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const togglePin = async (item) => {
    try {
      await notesApi.update(item.id, { is_pinned: !item.is_pinned });
      fetchItems();
    } catch (_) {}
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await notesApi.delete(deleteTarget.id);
      setDeleteTarget(null);
      setDrawerOpen(false);
      fetchItems();
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    }
  };

  return (
    <SpokePageShell title={spoke.label} color={spoke.color} onAdd={openCreate}
      searchValue={search} onSearchChange={setSearch}>

      {items.length === 0 && (
        <Paper elevation={0} sx={{ p: 4, textAlign: 'center', border: '1px dashed', borderColor: 'divider', borderRadius: 3 }}>
          <Typography color="text.secondary">No {spoke.label.toLowerCase()} yet. Start writing!</Typography>
        </Paper>
      )}

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)' }, gap: 1.5 }}>
        {items.map((item) => (
          <Paper key={item.id} elevation={0} onClick={() => openEdit(item)}
            sx={{
              p: 2, borderRadius: 3, border: '1px solid', borderColor: item.is_pinned ? spoke.color : 'divider',
              cursor: 'pointer', transition: 'all 0.15s', minHeight: 100, position: 'relative',
              '&:hover': { borderColor: spoke.color, transform: 'translateY(-2px)', boxShadow: 2 },
            }}>
            <IconButton size="small"
              onClick={(e) => { e.stopPropagation(); setDeleteTarget(item); }}
              sx={{ position: 'absolute', top: 8, right: 8, opacity: 0.25, '&:hover': { opacity: 1, color: '#E94560' } }}>
              <Delete sx={{ fontSize: 16 }} />
            </IconButton>
            <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
              <Typography sx={{ fontWeight: 600, fontSize: '0.9rem', flexGrow: 1, lineHeight: 1.3 }}>
                {item.title}
              </Typography>
              <IconButton size="small" onClick={(e) => { e.stopPropagation(); togglePin(item); }}
                sx={{ p: 0.3, color: item.is_pinned ? spoke.color : 'text.disabled' }}>
                {item.is_pinned ? <PushPin sx={{ fontSize: 16 }} /> : <PushPinOutlined sx={{ fontSize: 16 }} />}
              </IconButton>
            </Box>
            {item.content && (
              <Typography sx={{ fontSize: '0.78rem', color: 'text.secondary', lineHeight: 1.4, mb: 1,
                overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical' }}>
                {item.content}
              </Typography>
            )}
            {item.tags?.length > 0 && (
              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                {item.tags.map((tag) => (
                  <Chip key={tag} label={tag} size="small" sx={{ fontSize: '0.65rem', height: 20 }} />
                ))}
              </Box>
            )}
          </Paper>
        ))}
      </Box>

      <FormDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)}
        title={editing ? `Edit ${spoke.label_singular}` : `New ${spoke.label_singular}`}
        onSave={handleSave} loading={saving}
        onDelete={editing ? () => setDeleteTarget(editing) : undefined}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField label="Title" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <TextField label="Content" multiline rows={8} value={form.content}
            onChange={(e) => setForm({ ...form, content: e.target.value })}
            helperText="Markdown supported" />
          <TextField label="Tags (comma separated)" value={form.tags}
            onChange={(e) => setForm({ ...form, tags: e.target.value })} />
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

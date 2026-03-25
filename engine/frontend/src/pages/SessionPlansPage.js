/**
 * SessionPlansPage — Interactive timeline builder for photo sessions.
 * Create plans with time blocks, reorder, edit inline.
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Paper, Typography, IconButton, TextField, Button,
  Chip, Snackbar, Alert, MenuItem,
} from '@mui/material';
import { Add, Delete, Close, DragIndicator, ArrowUpward, ArrowDownward } from '@mui/icons-material';
import SpokePageShell from '../components/spokes/SpokePageShell';
import FormDrawer from '../components/spokes/FormDrawer';
import DeleteDialog from '../components/spokes/DeleteDialog';
import { sessionPlansApi } from '../services/spokeApi';

const SESSION_TYPES = ['Wedding', 'Engagement', 'Family', 'Newborn', 'Senior', 'Headshot', 'Mini Session', 'Elopement', 'Maternity', 'Pet', 'Event', 'Other'];

export default function SessionPlansPage() {
  const [plans, setPlans] = useState([]);
  const [activePlan, setActivePlan] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ title: '', session_type: '', date: '', location: '', client_name: '', notes: '' });
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [snack, setSnack] = useState({ open: false, message: '', severity: 'success' });

  // New block form
  const [newBlock, setNewBlock] = useState({ time: '', duration: '30', activity: '', notes: '' });

  const fetchPlans = useCallback(async () => {
    try {
      const data = await sessionPlansApi.list();
      setPlans(data.items || []);
    } catch (_) {}
  }, []);

  useEffect(() => { fetchPlans(); }, [fetchPlans]);

  const openCreate = () => {
    setEditing(null);
    setForm({ title: '', session_type: '', date: '', location: '', client_name: '', notes: '' });
    setDrawerOpen(true);
  };

  const openEdit = (plan) => {
    setEditing(plan);
    setForm({
      title: plan.title, session_type: plan.session_type || '',
      date: plan.date || '', location: plan.location || '',
      client_name: plan.client_name || '', notes: plan.notes || '',
    });
    setDrawerOpen(true);
  };

  const handleSave = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      if (editing) {
        const updated = await sessionPlansApi.update(editing.id, { ...form, blocks: editing.blocks });
        if (activePlan?.id === updated.id) setActivePlan(updated);
        setSnack({ open: true, message: 'Plan updated', severity: 'success' });
      } else {
        const created = await sessionPlansApi.create({ ...form, blocks: [] });
        setActivePlan(created);
        setSnack({ open: true, message: 'Plan created', severity: 'success' });
      }
      setDrawerOpen(false);
      fetchPlans();
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await sessionPlansApi.delete(deleteTarget.id);
      if (activePlan?.id === deleteTarget.id) setActivePlan(null);
      setDeleteTarget(null);
      setDrawerOpen(false);
      fetchPlans();
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    }
  };

  // Add a time block
  const addBlock = async () => {
    if (!newBlock.activity.trim() || !activePlan) return;
    const blocks = [...activePlan.blocks, {
      time: newBlock.time, duration: parseInt(newBlock.duration) || 30,
      activity: newBlock.activity.trim(), notes: newBlock.notes.trim(),
    }];
    try {
      const updated = await sessionPlansApi.update(activePlan.id, { blocks });
      setActivePlan(updated);
      setPlans(prev => prev.map(p => p.id === updated.id ? updated : p));
      setNewBlock({ time: '', duration: '30', activity: '', notes: '' });
    } catch (_) {}
  };

  // Remove a block
  const removeBlock = async (idx) => {
    if (!activePlan) return;
    const blocks = activePlan.blocks.filter((_, i) => i !== idx);
    try {
      const updated = await sessionPlansApi.update(activePlan.id, { blocks });
      setActivePlan(updated);
      setPlans(prev => prev.map(p => p.id === updated.id ? updated : p));
    } catch (_) {}
  };

  // Move a block up or down
  const moveBlock = async (idx, direction) => {
    if (!activePlan) return;
    const blocks = [...activePlan.blocks];
    const newIdx = idx + direction;
    if (newIdx < 0 || newIdx >= blocks.length) return;
    [blocks[idx], blocks[newIdx]] = [blocks[newIdx], blocks[idx]];
    try {
      const updated = await sessionPlansApi.update(activePlan.id, { blocks });
      setActivePlan(updated);
      setPlans(prev => prev.map(p => p.id === updated.id ? updated : p));
    } catch (_) {}
  };

  const totalMinutes = activePlan ? activePlan.blocks.reduce((sum, b) => sum + (b.duration || 0), 0) : 0;
  const totalHours = Math.floor(totalMinutes / 60);
  const remainMinutes = totalMinutes % 60;

  return (
    <SpokePageShell title="Session Plans" color="#5B8FB9" onAdd={openCreate}>
      {activePlan ? (
        <Box>
          {/* Header */}
          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 2 }}>
            <Box sx={{ flexGrow: 1 }}>
              <Typography sx={{ fontWeight: 700, fontSize: '1.1rem' }}>{activePlan.title}</Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 0.5 }}>
                {activePlan.session_type && <Chip label={activePlan.session_type} size="small" sx={{ fontSize: '0.7rem', height: 22 }} />}
                {activePlan.date && <Chip label={activePlan.date} size="small" variant="outlined" sx={{ fontSize: '0.7rem', height: 22 }} />}
                {activePlan.location && <Chip label={activePlan.location} size="small" variant="outlined" sx={{ fontSize: '0.7rem', height: 22 }} />}
                {activePlan.client_name && <Chip label={activePlan.client_name} size="small" variant="outlined" sx={{ fontSize: '0.7rem', height: 22 }} />}
              </Box>
              {totalMinutes > 0 && (
                <Typography sx={{ fontSize: '0.78rem', color: 'text.secondary', mt: 0.5 }}>
                  {totalHours > 0 ? `${totalHours}h ` : ''}{remainMinutes > 0 ? `${remainMinutes}m` : ''} total
                  {' · '}{activePlan.blocks.length} blocks
                </Typography>
              )}
            </Box>
            <Button size="small" onClick={() => openEdit(activePlan)}>Edit</Button>
            <IconButton size="small" onClick={() => setActivePlan(null)}><Close /></IconButton>
          </Box>

          {/* Timeline blocks */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {activePlan.blocks.map((block, idx) => (
              <Paper key={idx} elevation={0} sx={{
                p: 1.5, borderRadius: 2, border: '1px solid', borderColor: 'divider',
                display: 'flex', alignItems: 'center', gap: 1,
                borderLeft: '4px solid #5B8FB9',
              }}>
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0.25 }}>
                  <IconButton size="small" onClick={() => moveBlock(idx, -1)} disabled={idx === 0}
                    sx={{ p: 0.25, opacity: 0.4, '&:hover': { opacity: 1 } }}>
                    <ArrowUpward sx={{ fontSize: 14 }} />
                  </IconButton>
                  <DragIndicator sx={{ fontSize: 14, color: 'text.disabled' }} />
                  <IconButton size="small" onClick={() => moveBlock(idx, 1)} disabled={idx === activePlan.blocks.length - 1}
                    sx={{ p: 0.25, opacity: 0.4, '&:hover': { opacity: 1 } }}>
                    <ArrowDownward sx={{ fontSize: 14 }} />
                  </IconButton>
                </Box>
                <Box sx={{ flexGrow: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {block.time && (
                      <Typography sx={{ fontSize: '0.78rem', fontWeight: 700, color: '#5B8FB9', minWidth: 55 }}>
                        {block.time}
                      </Typography>
                    )}
                    <Typography sx={{ fontWeight: 600, fontSize: '0.9rem' }}>{block.activity}</Typography>
                    <Chip label={`${block.duration}m`} size="small"
                      sx={{ fontSize: '0.65rem', height: 18, bgcolor: '#5B8FB920', color: '#5B8FB9', fontWeight: 600 }} />
                  </Box>
                  {block.notes && (
                    <Typography sx={{ fontSize: '0.75rem', color: 'text.secondary', mt: 0.25 }}>{block.notes}</Typography>
                  )}
                </Box>
                <IconButton size="small" onClick={() => removeBlock(idx)}
                  sx={{ opacity: 0.3, '&:hover': { opacity: 1 } }}>
                  <Delete sx={{ fontSize: 16 }} />
                </IconButton>
              </Paper>
            ))}
          </Box>

          {/* Add block */}
          <Paper elevation={0} sx={{ p: 2, mt: 1.5, borderRadius: 2, border: '1px dashed', borderColor: 'divider' }}>
            <Typography sx={{ fontSize: '0.78rem', fontWeight: 600, color: 'text.secondary', mb: 1 }}>Add a time block</Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <TextField size="small" label="Time" type="time" value={newBlock.time}
                onChange={(e) => setNewBlock({ ...newBlock, time: e.target.value })}
                InputLabelProps={{ shrink: true }} sx={{ width: 120 }} />
              <TextField size="small" label="Min" type="number" value={newBlock.duration}
                onChange={(e) => setNewBlock({ ...newBlock, duration: e.target.value })}
                inputProps={{ min: 5, step: 5 }} sx={{ width: 80 }} />
              <TextField size="small" label="Activity" value={newBlock.activity}
                onChange={(e) => setNewBlock({ ...newBlock, activity: e.target.value })}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addBlock(); } }}
                sx={{ flexGrow: 1, minWidth: 150 }} />
              <IconButton onClick={addBlock} disabled={!newBlock.activity.trim()}
                sx={{ bgcolor: '#5B8FB9', color: 'white', '&:hover': { bgcolor: '#4A7EA8' }, '&.Mui-disabled': { bgcolor: '#eee' } }}>
                <Add />
              </IconButton>
            </Box>
            <TextField size="small" fullWidth label="Notes (optional)" value={newBlock.notes}
              onChange={(e) => setNewBlock({ ...newBlock, notes: e.target.value })}
              sx={{ mt: 1 }} />
          </Paper>
        </Box>
      ) : (
        <>
          {plans.length === 0 && (
            <Paper elevation={0} sx={{ p: 4, textAlign: 'center', border: '1px dashed', borderColor: 'divider', borderRadius: 3 }}>
              <Typography color="text.secondary">No session plans yet. Build your first timeline!</Typography>
            </Paper>
          )}

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            {plans.map((plan) => (
              <Paper key={plan.id} elevation={0} onClick={() => setActivePlan(plan)}
                sx={{
                  p: 2, borderRadius: 3, border: '1px solid', borderColor: 'divider', cursor: 'pointer',
                  borderLeft: '4px solid #5B8FB9', position: 'relative',
                  transition: 'all 0.15s', '&:hover': { borderColor: '#5B8FB9', transform: 'translateY(-2px)', boxShadow: 2 },
                }}>
                <IconButton size="small"
                  onClick={(e) => { e.stopPropagation(); setDeleteTarget(plan); }}
                  sx={{ position: 'absolute', top: 8, right: 8, opacity: 0.25, '&:hover': { opacity: 1, color: '#E94560' } }}>
                  <Delete sx={{ fontSize: 16 }} />
                </IconButton>
                <Typography sx={{ fontWeight: 600, fontSize: '0.95rem' }}>{plan.title}</Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 0.5 }}>
                  {plan.session_type && <Chip label={plan.session_type} size="small" sx={{ fontSize: '0.68rem', height: 20 }} />}
                  {plan.date && <Chip label={plan.date} size="small" variant="outlined" sx={{ fontSize: '0.68rem', height: 20 }} />}
                  {plan.client_name && <Chip label={plan.client_name} size="small" variant="outlined" sx={{ fontSize: '0.68rem', height: 20 }} />}
                  <Typography sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                    {plan.blocks.length} blocks
                  </Typography>
                </Box>
              </Paper>
            ))}
          </Box>
        </>
      )}

      <FormDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)}
        title={editing ? 'Edit Plan' : 'New Session Plan'}
        onSave={handleSave} loading={saving}
        onDelete={editing ? () => setDeleteTarget(editing) : undefined}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField label="Title" required value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            helperText="e.g. Johnson Wedding, Fall Mini Day" />
          <TextField label="Session Type" select value={form.session_type}
            onChange={(e) => setForm({ ...form, session_type: e.target.value })}>
            <MenuItem value="">None</MenuItem>
            {SESSION_TYPES.map(t => <MenuItem key={t} value={t}>{t}</MenuItem>)}
          </TextField>
          <TextField label="Date" type="date" value={form.date}
            onChange={(e) => setForm({ ...form, date: e.target.value })}
            InputLabelProps={{ shrink: true }} />
          <TextField label="Location" value={form.location}
            onChange={(e) => setForm({ ...form, location: e.target.value })} />
          <TextField label="Client Name" value={form.client_name}
            onChange={(e) => setForm({ ...form, client_name: e.target.value })} />
          <TextField label="Notes" multiline rows={2} value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </Box>
      </FormDrawer>

      <DeleteDialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete} itemName={deleteTarget?.title} labelSingular="Plan" />

      <Snackbar open={snack.open} autoHideDuration={3000} onClose={() => setSnack({ ...snack, open: false })}>
        <Alert severity={snack.severity} variant="filled">{snack.message}</Alert>
      </Snackbar>
    </SpokePageShell>
  );
}

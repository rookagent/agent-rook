/**
 * MemoriesPage — View, edit, delete, and export what the agent remembers about you.
 *
 * "Your data, your right."
 *
 * Features:
 * - View all memories grouped by type (facts, preferences, goals, interactions)
 * - Edit any memory's content
 * - Delete individual memories
 * - Purge all memories (with confirmation)
 * - Export all memories as JSON
 * - Confidence indicator (visual bar)
 * - Reinforcement count (how many times the agent heard this)
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Paper, Typography, IconButton, Chip, Snackbar, Alert,
  Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField,
  LinearProgress, Tooltip, CircularProgress,
} from '@mui/material';
import {
  Delete, Edit, DeleteForever, Download, Psychology, Autorenew,
} from '@mui/icons-material';
import SpokePageShell from '../components/spokes/SpokePageShell';
import { getToken } from '../services/chatApi';
import config from '../agentConfig.json';

const API_URL = config.api_url;

// Memory type colors
const TYPE_COLORS = {
  fact: '#4CAF50',
  preference: '#2196F3',
  goal: '#FF9800',
  interaction: '#9C27B0',
  schedule: '#009688',
};

const TYPE_LABELS = {
  fact: 'Fact',
  preference: 'Preference',
  goal: 'Goal',
  interaction: 'Interaction',
  schedule: 'Schedule',
};

async function authFetch(path, { method = 'GET', body } = {}) {
  const token = getToken();
  const headers = { 'Authorization': `Bearer ${token}` };
  const opts = { method, headers };
  if (body) {
    headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const response = await fetch(path, opts);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || `Request failed (${response.status})`);
  }
  return response;
}

export default function MemoriesPage() {
  const [memories, setMemories] = useState([]);
  const [search, setSearch] = useState('');
  const [editTarget, setEditTarget] = useState(null);
  const [editContent, setEditContent] = useState('');
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [purgeOpen, setPurgeOpen] = useState(false);
  const [snack, setSnack] = useState({ open: false, message: '', severity: 'success' });
  const [analytics, setAnalytics] = useState(null);
  const [consolidating, setConsolidating] = useState(false);

  const fetchMemories = useCallback(async () => {
    try {
      const res = await authFetch(`${API_URL}/memories`);
      const data = await res.json();
      setMemories(data.memories || []);
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    }
  }, []);

  const fetchAnalytics = useCallback(async () => {
    try {
      const res = await authFetch(`${API_URL}/memories/analytics`);
      const data = await res.json();
      setAnalytics(data);
    } catch (_) {}
  }, []);

  const handleConsolidate = async () => {
    setConsolidating(true);
    try {
      await authFetch(`${API_URL}/memories/consolidate`, { method: 'POST' });
      await Promise.all([fetchMemories(), fetchAnalytics()]);
      setSnack({ open: true, message: 'Memories consolidated', severity: 'success' });
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    } finally {
      setConsolidating(false);
    }
  };

  useEffect(() => { fetchMemories(); fetchAnalytics(); }, [fetchMemories, fetchAnalytics]);

  // Filter by search
  const filtered = memories.filter(m =>
    !search || m.content.toLowerCase().includes(search.toLowerCase()) ||
    (m.category || '').toLowerCase().includes(search.toLowerCase())
  );

  // Group by type
  const grouped = {};
  filtered.forEach(m => {
    const type = m.type || 'fact';
    if (!grouped[type]) grouped[type] = [];
    grouped[type].push(m);
  });

  const handleEdit = async () => {
    if (!editTarget || !editContent.trim()) return;
    try {
      await authFetch(`${API_URL}/memories/${editTarget.id}`, {
        method: 'PUT',
        body: { content: editContent },
      });
      setEditTarget(null);
      fetchMemories();
      setSnack({ open: true, message: 'Memory updated', severity: 'success' });
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await authFetch(`${API_URL}/memories/${deleteTarget.id}`, { method: 'DELETE' });
      setDeleteTarget(null);
      fetchMemories();
      setSnack({ open: true, message: 'Memory deleted', severity: 'success' });
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    }
  };

  const handlePurge = async () => {
    try {
      await authFetch(`${API_URL}/memories/purge`, {
        method: 'POST',
        body: { confirm: true },
      });
      setPurgeOpen(false);
      fetchMemories();
      setSnack({ open: true, message: 'All memories cleared', severity: 'success' });
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    }
  };

  const handleExport = async () => {
    try {
      const res = await authFetch(`${API_URL}/memories/export`);
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'my-memories.json';
      a.click();
      URL.revokeObjectURL(url);
      setSnack({ open: true, message: 'Memories exported', severity: 'success' });
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    }
  };

  return (
    <SpokePageShell
      title="Memories"
      color="#7E57C2"
      searchValue={search}
      onSearchChange={setSearch}
    >
      {/* Action bar */}
      <Box sx={{ display: 'flex', gap: 1, mb: 3, justifyContent: 'flex-end' }}>
        <Button
          size="small"
          startIcon={<Download />}
          onClick={handleExport}
          sx={{ textTransform: 'none', color: 'text.secondary' }}
        >
          Export
        </Button>
        <Button
          size="small"
          startIcon={<DeleteForever />}
          onClick={() => setPurgeOpen(true)}
          sx={{ textTransform: 'none', color: '#d32f2f' }}
        >
          Clear All
        </Button>
      </Box>

      {/* Analytics */}
      <Paper elevation={0} sx={{ p: 2.5, mb: 3, borderRadius: 3, border: '1px solid #eee', bgcolor: '#FAFAF8' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Psychology sx={{ color: '#7E57C2', fontSize: 24 }} />
            <Typography sx={{ fontWeight: 600, fontSize: '0.95rem' }}>
              {analytics?.total_memories ?? memories.length} {(analytics?.total_memories ?? memories.length) === 1 ? 'memory' : 'memories'}
            </Typography>
          </Box>
          <Button
            size="small"
            startIcon={consolidating ? <CircularProgress size={14} /> : <Autorenew />}
            onClick={handleConsolidate}
            disabled={consolidating}
            sx={{ textTransform: 'none', fontSize: '0.8rem', color: '#7E57C2' }}
          >
            Consolidate
          </Button>
        </Box>

        {/* Stat row */}
        {analytics && (
          <Box sx={{ display: 'flex', gap: 3, mb: 1.5 }}>
            <Box>
              <Typography sx={{ fontSize: '1.2rem', fontWeight: 700, color: '#7E57C2', lineHeight: 1 }}>
                {Math.round((analytics.average_confidence || 0) * 100)}%
              </Typography>
              <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>avg confidence</Typography>
            </Box>
            <Box>
              <Typography sx={{ fontSize: '1.2rem', fontWeight: 700, color: '#7E57C2', lineHeight: 1 }}>
                {analytics.memories_this_week ?? 0}
              </Typography>
              <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>this week</Typography>
            </Box>
          </Box>
        )}

        {/* Type distribution chips */}
        {analytics?.type_distribution && Object.keys(analytics.type_distribution).length > 0 && (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
            {Object.entries(analytics.type_distribution).map(([type, count]) => (
              <Chip
                key={type}
                label={`${TYPE_LABELS[type] || type} ${count}`}
                size="small"
                sx={{
                  bgcolor: `${TYPE_COLORS[type] || '#666'}18`,
                  color: TYPE_COLORS[type] || '#666',
                  fontWeight: 600,
                  fontSize: '0.72rem',
                  height: 24,
                }}
              />
            ))}
          </Box>
        )}

        {!analytics && (
          <Typography sx={{ fontSize: '0.8rem', color: 'text.secondary' }}>
            Things your agent remembers about you across conversations.
          </Typography>
        )}
      </Paper>

      {/* Memory groups */}
      {Object.entries(grouped).map(([type, items]) => (
        <Box key={type} sx={{ mb: 3 }}>
          <Typography sx={{
            fontWeight: 600,
            fontSize: '0.9rem',
            color: TYPE_COLORS[type] || '#666',
            mb: 1,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}>
            {TYPE_LABELS[type] || type}s ({items.length})
          </Typography>

          {items.map(memory => (
            <Paper
              key={memory.id}
              elevation={0}
              sx={{
                p: 2,
                mb: 1,
                borderRadius: 2,
                border: '1px solid #eee',
                display: 'flex',
                alignItems: 'flex-start',
                gap: 1.5,
                '&:hover': { bgcolor: '#FAFAF8' },
              }}
            >
              {/* Content */}
              <Box sx={{ flex: 1 }}>
                <Typography sx={{ fontSize: '0.9rem', lineHeight: 1.5 }}>
                  {memory.content}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                  {memory.category && (
                    <Chip
                      label={memory.category}
                      size="small"
                      sx={{ fontSize: '0.7rem', height: 20 }}
                    />
                  )}
                  <Tooltip title={`Confidence: ${Math.round(memory.confidence * 100)}%`}>
                    <Box sx={{ width: 60 }}>
                      <LinearProgress
                        variant="determinate"
                        value={memory.confidence * 100}
                        sx={{
                          height: 4,
                          borderRadius: 2,
                          bgcolor: '#eee',
                          '& .MuiLinearProgress-bar': {
                            bgcolor: TYPE_COLORS[memory.type] || '#666',
                          },
                        }}
                      />
                    </Box>
                  </Tooltip>
                  {memory.times_reinforced > 1 && (
                    <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
                      heard {memory.times_reinforced}x
                    </Typography>
                  )}
                </Box>
              </Box>

              {/* Actions */}
              <Box sx={{ display: 'flex', gap: 0.5 }}>
                <IconButton
                  size="small"
                  onClick={() => { setEditTarget(memory); setEditContent(memory.content); }}
                >
                  <Edit sx={{ fontSize: 16 }} />
                </IconButton>
                <IconButton
                  size="small"
                  onClick={() => setDeleteTarget(memory)}
                >
                  <Delete sx={{ fontSize: 16, color: '#d32f2f' }} />
                </IconButton>
              </Box>
            </Paper>
          ))}
        </Box>
      ))}

      {filtered.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 6 }}>
          <Psychology sx={{ fontSize: 48, color: '#ddd', mb: 1 }} />
          <Typography sx={{ color: 'text.secondary' }}>
            {search ? 'No memories match your search' : 'No memories yet. Chat with your agent to build memory.'}
          </Typography>
        </Box>
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editTarget} onClose={() => setEditTarget(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Memory</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            multiline
            rows={3}
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            sx={{ mt: 1 }}
            inputProps={{ maxLength: 250 }}
            helperText={`${editContent.length}/250 characters`}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditTarget(null)}>Cancel</Button>
          <Button onClick={handleEdit} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Delete Memory?</DialogTitle>
        <DialogContent>
          <Typography>
            "{deleteTarget?.content?.substring(0, 100)}{deleteTarget?.content?.length > 100 ? '...' : ''}"
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button onClick={handleDelete} color="error" variant="contained">Delete</Button>
        </DialogActions>
      </Dialog>

      {/* Purge Confirmation */}
      <Dialog open={purgeOpen} onClose={() => setPurgeOpen(false)}>
        <DialogTitle>Clear All Memories?</DialogTitle>
        <DialogContent>
          <Typography>
            This will delete everything your agent remembers about you.
            It cannot be undone. Your next conversation will start fresh.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPurgeOpen(false)}>Cancel</Button>
          <Button onClick={handlePurge} color="error" variant="contained">Clear All</Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snack.open}
        autoHideDuration={3000}
        onClose={() => setSnack(s => ({ ...s, open: false }))}
      >
        <Alert severity={snack.severity} onClose={() => setSnack(s => ({ ...s, open: false }))}>
          {snack.message}
        </Alert>
      </Snackbar>
    </SpokePageShell>
  );
}

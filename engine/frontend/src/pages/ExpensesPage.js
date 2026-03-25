/**
 * ExpensesPage — Track business expenses with categories, amounts, dates.
 * Essential for any freelancer/sole operator.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Box, Paper, Typography, Chip, IconButton, Snackbar, Alert, TextField, MenuItem } from '@mui/material';
import { Delete } from '@mui/icons-material';
import SpokePageShell from '../components/spokes/SpokePageShell';
import FormDrawer from '../components/spokes/FormDrawer';
import DeleteDialog from '../components/spokes/DeleteDialog';
import { expensesApi } from '../services/spokeApi';
import config from '../agentConfig.json';

const spoke = config.spokes?.expenses || { label: 'Expenses', label_singular: 'Expense', color: '#AB47BC' };

const CATEGORIES = [
  { value: 'gear', label: 'Gear & Equipment' },
  { value: 'software', label: 'Software & Subscriptions' },
  { value: 'travel', label: 'Travel & Mileage' },
  { value: 'marketing', label: 'Marketing & Advertising' },
  { value: 'education', label: 'Education & Workshops' },
  { value: 'insurance', label: 'Insurance' },
  { value: 'meals', label: 'Meals & Entertainment' },
  { value: 'office', label: 'Office & Supplies' },
  { value: 'subcontractor', label: 'Subcontractors' },
  { value: 'other', label: 'Other' },
];

const CATEGORY_COLORS = {
  gear: '#E94560', software: '#42A5F5', travel: '#FFA726', marketing: '#AB47BC',
  education: '#26A69A', insurance: '#78909C', meals: '#66BB6A', office: '#8D6E63',
  subcontractor: '#EC407A', other: '#90A4AE',
};

export default function ExpensesPage() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [filterCat, setFilterCat] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ description: '', amount: '', category: 'other', date: '', vendor: '', notes: '', is_deductible: true });
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [snack, setSnack] = useState({ open: false, message: '', severity: 'success' });

  const fetchItems = useCallback(async () => {
    try {
      const params = { q: search };
      if (filterCat) params.category = filterCat;
      const data = await expensesApi.list(params);
      setItems(data.items || []);
      setTotal(data.total || 0);
    } catch (_) {}
  }, [search, filterCat]);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  const openCreate = () => {
    setEditing(null);
    const today = new Date().toISOString().split('T')[0];
    setForm({ description: '', amount: '', category: 'other', date: today, vendor: '', notes: '', is_deductible: true });
    setDrawerOpen(true);
  };

  const openEdit = (item) => {
    setEditing(item);
    setForm({
      description: item.description || '',
      amount: item.amount?.toString() || '',
      category: item.category || 'other',
      date: item.date || '',
      vendor: item.vendor || '',
      notes: item.notes || '',
      is_deductible: item.is_deductible ?? true,
    });
    setDrawerOpen(true);
  };

  const handleSave = async () => {
    if (!form.description.trim() || !form.amount) return;
    setSaving(true);
    try {
      const payload = {
        description: form.description,
        amount: parseFloat(form.amount),
        category: form.category,
        date: form.date || null,
        vendor: form.vendor,
        notes: form.notes,
        is_deductible: form.is_deductible,
      };
      if (editing) {
        await expensesApi.update(editing.id, payload);
        setSnack({ open: true, message: `${spoke.label_singular} updated`, severity: 'success' });
      } else {
        await expensesApi.create(payload);
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
      await expensesApi.delete(deleteTarget.id);
      setDeleteTarget(null);
      setDrawerOpen(false);
      fetchItems();
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    }
  };

  const getCatLabel = (cat) => CATEGORIES.find(c => c.value === cat)?.label || cat;

  return (
    <SpokePageShell title={spoke.label} color={spoke.color} onAdd={openCreate}
      searchValue={search} onSearchChange={setSearch}>

      {/* Total + category filter */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <Paper elevation={0} sx={{ px: 2, py: 1, borderRadius: 2, bgcolor: `${spoke.color}0A`, border: '1px solid', borderColor: `${spoke.color}33` }}>
          <Typography sx={{ fontSize: '0.72rem', color: 'text.secondary', fontWeight: 500 }}>Total</Typography>
          <Typography sx={{ fontSize: '1.2rem', fontWeight: 700, color: spoke.color }}>
            ${total.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </Typography>
        </Paper>
        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
          <Chip label="All" size="small" onClick={() => setFilterCat('')}
            sx={{ cursor: 'pointer', fontWeight: 600, fontSize: '0.72rem',
              bgcolor: !filterCat ? spoke.color : 'transparent', color: !filterCat ? 'white' : 'text.secondary',
              border: '1px solid', borderColor: !filterCat ? 'transparent' : 'divider' }} />
          {CATEGORIES.slice(0, 6).map(cat => (
            <Chip key={cat.value} label={cat.label.split(' ')[0]} size="small"
              onClick={() => setFilterCat(filterCat === cat.value ? '' : cat.value)}
              sx={{ cursor: 'pointer', fontWeight: 600, fontSize: '0.72rem',
                bgcolor: filterCat === cat.value ? (CATEGORY_COLORS[cat.value] || spoke.color) : 'transparent',
                color: filterCat === cat.value ? 'white' : 'text.secondary',
                border: '1px solid', borderColor: filterCat === cat.value ? 'transparent' : 'divider' }} />
          ))}
        </Box>
      </Box>

      {items.length === 0 && (
        <Paper elevation={0} sx={{ p: 4, textAlign: 'center', border: '1px dashed', borderColor: 'divider', borderRadius: 3 }}>
          <Typography color="text.secondary">No expenses tracked yet. Start logging!</Typography>
        </Paper>
      )}

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {items.map((item) => (
          <Paper key={item.id} elevation={0} onClick={() => openEdit(item)}
            sx={{
              p: 2, borderRadius: 2, border: '1px solid', borderColor: 'divider', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 1.5, position: 'relative',
              '&:hover': { borderColor: spoke.color, transform: 'translateY(-1px)', boxShadow: 1 },
            }}>
            <IconButton size="small"
              onClick={(e) => { e.stopPropagation(); setDeleteTarget(item); }}
              sx={{ position: 'absolute', top: 8, right: 8, opacity: 0.25, '&:hover': { opacity: 1, color: '#E94560' } }}>
              <Delete sx={{ fontSize: 16 }} />
            </IconButton>
            {/* Category dot */}
            <Box sx={{
              width: 10, height: 10, borderRadius: '50%', flexShrink: 0,
              bgcolor: CATEGORY_COLORS[item.category] || '#90A4AE',
            }} />
            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
              <Typography sx={{ fontWeight: 600, fontSize: '0.9rem' }}>{item.description}</Typography>
              <Typography sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                {item.date} {item.vendor ? `· ${item.vendor}` : ''} · {getCatLabel(item.category)}
              </Typography>
            </Box>
            <Typography sx={{ fontWeight: 700, fontSize: '1rem', color: spoke.color, flexShrink: 0 }}>
              ${item.amount?.toFixed(2)}
            </Typography>
          </Paper>
        ))}
      </Box>

      <FormDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)}
        title={editing ? `Edit ${spoke.label_singular}` : `New ${spoke.label_singular}`}
        onSave={handleSave} loading={saving}
        onDelete={editing ? () => setDeleteTarget(editing) : undefined}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField label="Description" required value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            helperText="e.g. Godox AD200 Pro flash" />
          <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField label="Amount ($)" required type="number" value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
              sx={{ flex: 1 }} inputProps={{ step: '0.01', min: '0' }} />
            <TextField label="Date" type="date" value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              InputLabelProps={{ shrink: true }} sx={{ flex: 1 }} />
          </Box>
          <TextField label="Category" select value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}>
            {CATEGORIES.map(cat => (
              <MenuItem key={cat.value} value={cat.value}>{cat.label}</MenuItem>
            ))}
          </TextField>
          <TextField label="Vendor / Store" value={form.vendor}
            onChange={(e) => setForm({ ...form, vendor: e.target.value })} />
          <TextField label="Notes" multiline rows={2} value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </Box>
      </FormDrawer>

      <DeleteDialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete} itemName={deleteTarget?.description} labelSingular={spoke.label_singular} />

      <Snackbar open={snack.open} autoHideDuration={3000} onClose={() => setSnack({ ...snack, open: false })}>
        <Alert severity={snack.severity} variant="filled">{snack.message}</Alert>
      </Snackbar>
    </SpokePageShell>
  );
}

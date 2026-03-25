/**
 * SchedulePage — Full month-by-month calendar view.
 * Labels from agentConfig.json spokes config.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Box, Paper, Typography, Chip, IconButton, Snackbar, Alert, TextField } from '@mui/material';
import { ChevronLeft, ChevronRight } from '@mui/icons-material';
import SpokePageShell from '../components/spokes/SpokePageShell';
import FormDrawer from '../components/spokes/FormDrawer';
import DeleteDialog from '../components/spokes/DeleteDialog';
import { scheduleApi } from '../services/spokeApi';
import config from '../agentConfig.json';

const spoke = config.spokes?.schedule || { label: 'Calendar', label_singular: 'Event', color: '#42A5F5' };
const DAY_HEADERS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function getMonthData(year, month) {
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  // Monday = 0 in our grid
  let startDow = firstDay.getDay() - 1;
  if (startDow < 0) startDow = 6;

  const days = [];
  // Pad days from previous month
  for (let i = startDow - 1; i >= 0; i--) {
    const d = new Date(year, month, -i);
    days.push({ date: d, inMonth: false });
  }
  // Days in current month
  for (let d = 1; d <= lastDay.getDate(); d++) {
    days.push({ date: new Date(year, month, d), inMonth: true });
  }
  // Pad to fill the last week
  while (days.length % 7 !== 0) {
    const d = new Date(year, month + 1, days.length - lastDay.getDate() - startDow + 1);
    days.push({ date: d, inMonth: false });
  }
  return days;
}

function formatDate(d) {
  return d.toISOString().split('T')[0];
}

export default function SchedulePage() {
  const [viewDate, setViewDate] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() };
  });
  const [events, setEvents] = useState([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ title: '', date: '', start_time: '', end_time: '', description: '', tags: '', color: spoke.color });
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [snack, setSnack] = useState({ open: false, message: '', severity: 'success' });

  const monthDays = getMonthData(viewDate.year, viewDate.month);
  const monthStart = formatDate(monthDays[0].date);
  const monthEnd = formatDate(monthDays[monthDays.length - 1].date);
  const monthLabel = new Date(viewDate.year, viewDate.month).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  const fetchEvents = useCallback(async () => {
    try {
      const data = await scheduleApi.list({ start: monthStart, end: monthEnd });
      setEvents(data.items || []);
    } catch (_) {}
  }, [monthStart, monthEnd]);

  useEffect(() => { fetchEvents(); }, [fetchEvents]);

  const prevMonth = () => setViewDate(v => v.month === 0 ? { year: v.year - 1, month: 11 } : { ...v, month: v.month - 1 });
  const nextMonth = () => setViewDate(v => v.month === 11 ? { year: v.year + 1, month: 0 } : { ...v, month: v.month + 1 });
  const goToday = () => { const now = new Date(); setViewDate({ year: now.getFullYear(), month: now.getMonth() }); };

  const openCreate = (dateStr) => {
    setEditing(null);
    setForm({ title: '', date: dateStr || formatDate(new Date()), start_time: '', end_time: '', description: '', tags: '', color: spoke.color });
    setDrawerOpen(true);
  };

  const openEdit = (item) => {
    setEditing(item);
    setForm({
      title: item.title || '',
      date: item.date || '',
      start_time: item.start_time?.slice(0, 5) || '',
      end_time: item.end_time?.slice(0, 5) || '',
      description: item.description || '',
      tags: (item.tags || []).join(', '),
      color: item.color || spoke.color,
    });
    setDrawerOpen(true);
  };

  const handleSave = async () => {
    if (!form.title.trim() || !form.date) return;
    setSaving(true);
    try {
      const payload = {
        title: form.title, date: form.date,
        start_time: form.start_time || null, end_time: form.end_time || null,
        description: form.description,
        tags: form.tags ? form.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
        color: form.color,
      };
      if (editing) await scheduleApi.update(editing.id, payload);
      else await scheduleApi.create(payload);
      setDrawerOpen(false);
      fetchEvents();
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await scheduleApi.delete(deleteTarget.id);
      setDeleteTarget(null);
      setDrawerOpen(false);
      fetchEvents();
    } catch (err) {
      setSnack({ open: true, message: err.message, severity: 'error' });
    }
  };

  const today = formatDate(new Date());
  const isCurrentMonth = viewDate.year === new Date().getFullYear() && viewDate.month === new Date().getMonth();

  return (
    <SpokePageShell title={spoke.label} color={spoke.color} onAdd={() => openCreate()}>
      {/* Month navigation */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2, mb: 2 }}>
        <IconButton onClick={prevMonth}><ChevronLeft /></IconButton>
        <Typography sx={{ fontWeight: 700, fontSize: '1.1rem', minWidth: 180, textAlign: 'center', color: spoke.color }}>
          {monthLabel}
        </Typography>
        <IconButton onClick={nextMonth}><ChevronRight /></IconButton>
        {!isCurrentMonth && (
          <Chip label="Today" size="small" onClick={goToday}
            sx={{ cursor: 'pointer', fontWeight: 600, fontSize: '0.75rem' }} />
        )}
      </Box>

      {/* Day headers */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 0.5, mb: 0.5 }}>
        {DAY_HEADERS.map(d => (
          <Typography key={d} sx={{ textAlign: 'center', fontSize: '0.72rem', fontWeight: 700, color: 'text.secondary', py: 0.5 }}>
            {d}
          </Typography>
        ))}
      </Box>

      {/* Calendar grid */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 0.5 }}>
        {monthDays.map(({ date: d, inMonth }, i) => {
          const dateStr = formatDate(d);
          const isToday = dateStr === today;
          const dayEvents = events.filter(e => e.date === dateStr);

          return (
            <Paper key={i} elevation={0}
              onClick={() => openCreate(dateStr)}
              sx={{
                p: 0.75, borderRadius: 1.5, minHeight: { xs: 60, sm: 80 }, cursor: 'pointer',
                border: '1px solid', borderColor: isToday ? spoke.color : inMonth ? 'divider' : 'transparent',
                bgcolor: isToday ? `${spoke.color}0A` : inMonth ? 'white' : '#FAFAFA',
                opacity: inMonth ? 1 : 0.4,
                '&:hover': { borderColor: spoke.color, bgcolor: `${spoke.color}05` },
              }}>
              <Typography sx={{
                fontSize: '0.72rem', fontWeight: isToday ? 800 : 500,
                color: isToday ? spoke.color : 'text.secondary', mb: 0.25,
              }}>
                {d.getDate()}
              </Typography>
              {dayEvents.slice(0, 3).map((evt) => (
                <Box key={evt.id}
                  onClick={(e) => { e.stopPropagation(); openEdit(evt); }}
                  sx={{
                    bgcolor: evt.color || spoke.color, color: 'white', borderRadius: 0.5,
                    px: 0.5, py: 0.15, mb: 0.25, fontSize: '0.62rem', fontWeight: 600,
                    cursor: 'pointer', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    '&:hover': { opacity: 0.85 },
                  }}>
                  {evt.title}
                </Box>
              ))}
              {dayEvents.length > 3 && (
                <Typography sx={{ fontSize: '0.58rem', color: 'text.secondary', fontWeight: 600 }}>
                  +{dayEvents.length - 3} more
                </Typography>
              )}
            </Paper>
          );
        })}
      </Box>

      <FormDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)}
        title={editing ? `Edit ${spoke.label_singular}` : `New ${spoke.label_singular}`}
        onSave={handleSave} loading={saving}
        onDelete={editing ? () => setDeleteTarget(editing) : undefined}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField label="Title" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <TextField label="Date" type="date" required value={form.date}
            onChange={(e) => setForm({ ...form, date: e.target.value })}
            InputLabelProps={{ shrink: true }} />
          <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField label="Start Time" type="time" value={form.start_time}
              onChange={(e) => setForm({ ...form, start_time: e.target.value })}
              InputLabelProps={{ shrink: true }} sx={{ flex: 1 }} />
            <TextField label="End Time" type="time" value={form.end_time}
              onChange={(e) => setForm({ ...form, end_time: e.target.value })}
              InputLabelProps={{ shrink: true }} sx={{ flex: 1 }} />
          </Box>
          <TextField label="Description" multiline rows={2} value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })} />
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

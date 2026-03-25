/**
 * DashboardPage — Hub with live overview + card navigation.
 * Overview: upcoming events, pending tasks, quick stats.
 * Cards: 8 warm-colored cards routing to spoke pages + chat.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, Paper, Chip, Skeleton } from '@mui/material';
import {
  CameraAlt, CalendarMonth, Schedule, Inventory, CheckCircle,
  Receipt, Description, Chat, PhotoCamera, Email, Tag, FlashOn,
  AutoAwesome, Event, Warning, TrendingUp,
} from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { getDashboardSummary } from '../services/spokeApi';
import config from '../agentConfig.json';

const ICON_MAP = {
  CameraAlt, CalendarMonth, Schedule, Inventory, CheckCircle,
  Receipt, Description, Chat, PhotoCamera, Email, Tag, FlashOn,
  AutoAwesome,
};

const { primary_color, secondary_color, fonts } = config.branding;
const dashboard = config.dashboard || { greeting: true, cards: [] };

// Use the new /overview endpoint
async function fetchOverview() {
  const token = localStorage.getItem('rook_token');
  const res = await fetch('/api/dashboard/overview', {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed');
  return res.json();
}

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

function formatEventDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  if (d.getTime() === today.getTime()) return 'Today';
  if (d.getTime() === tomorrow.getTime()) return 'Tomorrow';
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

const PRIORITY_COLORS = { high: '#E94560', medium: '#FFA726', low: '#90A4AE' };

function HubCard({ title, description, icon, color, onClick }) {
  const IconComponent = ICON_MAP[icon] || AutoAwesome;
  const cardColor = color || secondary_color;

  return (
    <Paper elevation={0} onClick={onClick}
      sx={{
        p: { xs: 2.5, sm: 3 }, borderRadius: 4, cursor: 'pointer',
        position: 'relative', overflow: 'hidden',
        minHeight: { xs: 120, sm: 140 },
        display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center',
        bgcolor: cardColor,
        background: `linear-gradient(145deg, ${cardColor} 0%, ${cardColor}EE 40%, ${cardColor}CC 100%)`,
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
        '&:hover': { transform: 'translateY(-4px)', boxShadow: `0 8px 28px ${cardColor}44` },
      }}>
      <Box sx={{ position: 'absolute', top: 10, right: 12, opacity: 0.15 }}>
        <IconComponent sx={{ fontSize: 48, color: 'white' }} />
      </Box>
      <Box sx={{
        width: 40, height: 40, borderRadius: '50%', bgcolor: 'rgba(255,255,255,0.2)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 1.5,
      }}>
        <IconComponent sx={{ fontSize: 22, color: 'white' }} />
      </Box>
      <Typography sx={{ color: 'white', fontWeight: 700, fontSize: { xs: '0.95rem', sm: '1.05rem' }, lineHeight: 1.2, mb: 0.5 }}>
        {title}
      </Typography>
      <Typography sx={{ color: 'rgba(255,255,255,0.75)', fontSize: { xs: '0.75rem', sm: '0.8rem' }, lineHeight: 1.4, maxWidth: 200 }}>
        {description}
      </Typography>
    </Paper>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const firstName = user?.name?.split(' ')[0] || '';

  useEffect(() => {
    fetchOverview().then(setOverview).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const handleCardClick = (card) => {
    if (card.route) navigate(card.route);
    else if (card.prompt) navigate('/chat', { state: { prompt: card.prompt } });
  };

  const upcomingEvents = overview?.upcoming_events || [];
  const pendingTasks = overview?.pending_tasks || [];
  const overdueCount = overview?.overdue_count || 0;
  const expensesMonth = overview?.expenses_month || 0;
  const counts = overview?.counts || {};
  const hasOverviewData = upcomingEvents.length > 0 || pendingTasks.length > 0 || expensesMonth > 0;

  return (
    <Box sx={{ flexGrow: 1, px: { xs: 2, sm: 3, md: 4 }, py: { xs: 3, sm: 4 }, bgcolor: '#FBF9F7' }}>
      <Box sx={{ maxWidth: 960, mx: 'auto' }}>
        {/* Greeting */}
        {dashboard.greeting && (
          <Box sx={{ mb: { xs: 2.5, sm: 3 } }}>
            <Typography sx={{
              fontFamily: `"${fonts.heading}", cursive`,
              fontWeight: 700, color: primary_color,
              fontSize: { xs: '1.6rem', sm: '2rem' }, lineHeight: 1.2, mb: 0.5,
            }}>
              {getGreeting()}{firstName ? `, ${firstName}` : ''}
            </Typography>
            <Typography sx={{ color: `${primary_color}66`, fontSize: '0.88rem', fontWeight: 500 }}>
              {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
            </Typography>
          </Box>
        )}

        {/* ── Overview Section ── */}
        {loading ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2, mb: 3 }}>
            <Skeleton variant="rounded" height={140} sx={{ borderRadius: 3 }} />
            <Skeleton variant="rounded" height={140} sx={{ borderRadius: 3 }} />
          </Box>
        ) : hasOverviewData ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2, mb: { xs: 3, sm: 4 } }}>

            {/* Upcoming Events */}
            <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, border: '1px solid', borderColor: `${primary_color}12`, bgcolor: 'white' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                <Event sx={{ fontSize: 18, color: '#5B8FB9' }} />
                <Typography sx={{ fontWeight: 700, fontSize: '0.85rem', color: primary_color }}>
                  Coming Up
                </Typography>
                {counts.upcoming > 0 && (
                  <Chip label={`${counts.upcoming} total`} size="small"
                    sx={{ ml: 'auto', fontSize: '0.65rem', height: 20, fontWeight: 600 }} />
                )}
              </Box>
              {upcomingEvents.length === 0 ? (
                <Typography sx={{ fontSize: '0.82rem', color: 'text.secondary', fontStyle: 'italic' }}>
                  Nothing scheduled this week. Enjoy the quiet!
                </Typography>
              ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
                  {upcomingEvents.map((evt) => (
                    <Box key={evt.id} onClick={() => navigate('/schedule')}
                      sx={{
                        display: 'flex', alignItems: 'center', gap: 1, cursor: 'pointer',
                        p: 1, borderRadius: 2, '&:hover': { bgcolor: '#f8f8f8' },
                      }}>
                      <Box sx={{
                        width: 4, height: 32, borderRadius: 2, flexShrink: 0,
                        bgcolor: evt.color || '#5B8FB9',
                      }} />
                      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                        <Typography sx={{ fontWeight: 600, fontSize: '0.85rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {evt.title}
                        </Typography>
                        <Typography sx={{ fontSize: '0.72rem', color: 'text.secondary' }}>
                          {formatEventDate(evt.date)}
                          {evt.start_time && ` at ${evt.start_time.slice(0, 5)}`}
                        </Typography>
                      </Box>
                    </Box>
                  ))}
                </Box>
              )}
            </Paper>

            {/* Tasks + Stats */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {/* Pending Tasks */}
              <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, border: '1px solid', borderColor: `${primary_color}12`, bgcolor: 'white', flexGrow: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                  <CheckCircle sx={{ fontSize: 18, color: '#7BAF6E' }} />
                  <Typography sx={{ fontWeight: 700, fontSize: '0.85rem', color: primary_color }}>
                    To Do
                  </Typography>
                  {overdueCount > 0 && (
                    <Chip icon={<Warning sx={{ fontSize: 12 }} />} label={`${overdueCount} overdue`} size="small"
                      sx={{ ml: 'auto', fontSize: '0.65rem', height: 20, fontWeight: 600, bgcolor: '#FFF3E0', color: '#E65100' }} />
                  )}
                </Box>
                {pendingTasks.length === 0 ? (
                  <Typography sx={{ fontSize: '0.82rem', color: 'text.secondary', fontStyle: 'italic' }}>
                    All caught up!
                  </Typography>
                ) : (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                    {pendingTasks.map((task) => (
                      <Box key={task.id} onClick={() => navigate('/tasks')}
                        sx={{
                          display: 'flex', alignItems: 'center', gap: 1, cursor: 'pointer',
                          p: 0.75, borderRadius: 1.5, '&:hover': { bgcolor: '#f8f8f8' },
                        }}>
                        <Box sx={{
                          width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                          bgcolor: PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.medium,
                        }} />
                        <Typography sx={{
                          fontSize: '0.82rem', flexGrow: 1, fontWeight: 500,
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        }}>
                          {task.title}
                        </Typography>
                        {task.due_date && (
                          <Typography sx={{ fontSize: '0.68rem', color: 'text.secondary', flexShrink: 0 }}>
                            {formatEventDate(task.due_date)}
                          </Typography>
                        )}
                      </Box>
                    ))}
                  </Box>
                )}
              </Paper>

              {/* Quick Stats Row */}
              <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1 }}>
                <Paper elevation={0} onClick={() => navigate('/clients')}
                  sx={{
                    p: 1.5, borderRadius: 2, textAlign: 'center', cursor: 'pointer',
                    border: '1px solid', borderColor: `${primary_color}12`, bgcolor: 'white',
                    '&:hover': { bgcolor: '#f8f8f8' },
                  }}>
                  <Typography sx={{ fontWeight: 700, fontSize: '1.2rem', color: primary_color }}>{counts.clients || 0}</Typography>
                  <Typography sx={{ fontSize: '0.68rem', color: 'text.secondary', fontWeight: 500 }}>Shoots</Typography>
                </Paper>
                <Paper elevation={0} onClick={() => navigate('/expenses')}
                  sx={{
                    p: 1.5, borderRadius: 2, textAlign: 'center', cursor: 'pointer',
                    border: '1px solid', borderColor: `${primary_color}12`, bgcolor: 'white',
                    '&:hover': { bgcolor: '#f8f8f8' },
                  }}>
                  <Typography sx={{ fontWeight: 700, fontSize: '1.2rem', color: '#9B7DB8' }}>
                    ${expensesMonth.toLocaleString()}
                  </Typography>
                  <Typography sx={{ fontSize: '0.68rem', color: 'text.secondary', fontWeight: 500 }}>This Month</Typography>
                </Paper>
                <Paper elevation={0} onClick={() => navigate('/notes')}
                  sx={{
                    p: 1.5, borderRadius: 2, textAlign: 'center', cursor: 'pointer',
                    border: '1px solid', borderColor: `${primary_color}12`, bgcolor: 'white',
                    '&:hover': { bgcolor: '#f8f8f8' },
                  }}>
                  <Typography sx={{ fontWeight: 700, fontSize: '1.2rem', color: primary_color }}>{counts.notes || 0}</Typography>
                  <Typography sx={{ fontSize: '0.68rem', color: 'text.secondary', fontWeight: 500 }}>Notes</Typography>
                </Paper>
              </Box>
            </Box>
          </Box>
        ) : (
          /* Empty state — first time user */
          <Paper elevation={0} sx={{
            p: 3, mb: { xs: 3, sm: 4 }, borderRadius: 3, textAlign: 'center',
            border: '1px dashed', borderColor: `${primary_color}22`, bgcolor: 'white',
          }}>
            <Typography sx={{ fontSize: '0.9rem', color: primary_color, fontWeight: 600, mb: 0.5 }}>
              Welcome to {config.name}!
            </Typography>
            <Typography sx={{ fontSize: '0.82rem', color: 'text.secondary' }}>
              Start by adding a shoot, creating a checklist, or just ask me anything.
            </Typography>
          </Paper>
        )}

        {/* ── Card Grid ── */}
        <Box sx={{
          display: 'grid',
          gridTemplateColumns: { xs: 'repeat(2, 1fr)', sm: 'repeat(3, 1fr)', md: 'repeat(4, 1fr)' },
          gap: { xs: 1.5, sm: 2 },
        }}>
          {dashboard.cards.map((card) => (
            <HubCard key={card.title} title={card.title} description={card.description}
              icon={card.icon} color={card.color} onClick={() => handleCardClick(card)} />
          ))}
        </Box>
      </Box>
    </Box>
  );
}

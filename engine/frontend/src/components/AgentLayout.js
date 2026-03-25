/**
 * AgentLayout — Clean top bar (brand + credits + logout) + footer.
 * No nav chips — dashboard cards ARE the navigation.
 */
import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Box, Typography, IconButton, Tooltip, Fab } from '@mui/material';
import { Logout, ConfirmationNumber, Chat, CameraAlt, DarkMode, LightMode } from '@mui/icons-material';
import { useThemeMode } from '../App';
import { useAuth } from '../context/AuthContext';
import config from '../agentConfig.json';

const PALETTE = {
  bg: '#FBF9F7',
  headline: config.branding.primary_color,
  subtext: config.branding.primary_color + '99',
  gold: config.branding.secondary_color,
  border: config.branding.primary_color + '14',
  navBg: '#FFFFFF',
};

function ThemeToggle() {
  const { mode, toggle } = useThemeMode();
  return (
    <Tooltip title={mode === 'light' ? 'Dark mode' : 'Light mode'}>
      <IconButton size="small" onClick={toggle} sx={{ color: PALETTE.subtext }}>
        {mode === 'light' ? <DarkMode fontSize="small" /> : <LightMode fontSize="small" />}
      </IconButton>
    </Tooltip>
  );
}

function AgentNav() {
  const navigate = useNavigate();
  const { user, isLoggedIn, credits, isAdmin, logout } = useAuth();

  const firstName = user?.name?.split(' ')[0] || '';
  const isUnlimited = isAdmin;

  return (
    <Box sx={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      px: { xs: 2, md: 3 }, py: 1.5,
      bgcolor: PALETTE.navBg, borderBottom: '1px solid', borderColor: PALETTE.border,
    }}>
      <Box
        sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'pointer' }}
        onClick={() => navigate(isLoggedIn ? '/dashboard' : '/')}
      >
        <Typography sx={{
          fontFamily: `"${config.branding.fonts.heading}", cursive`,
          fontWeight: 700, color: PALETTE.headline, fontSize: '1.3rem', lineHeight: 1,
        }}>
          {config.name}
        </Typography>
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        {isLoggedIn && !isUnlimited && (
          <Tooltip title={credits > 0 ? `${credits} credits remaining` : 'Get credits'}>
            <Box onClick={() => navigate('/upgrade')}
              sx={{
                display: 'flex', alignItems: 'center', gap: 0.5,
                px: 1.25, py: 0.4, borderRadius: '50px', cursor: 'pointer',
                bgcolor: credits > 0 ? `${PALETTE.headline}14` : `${PALETTE.gold}1F`,
                '&:hover': { bgcolor: credits > 0 ? `${PALETTE.headline}22` : `${PALETTE.gold}33` },
              }}>
              <ConfirmationNumber sx={{ fontSize: 14, color: credits > 0 ? PALETTE.headline : PALETTE.gold }} />
              <Typography sx={{ fontSize: '0.75rem', fontWeight: 600, color: credits > 0 ? PALETTE.headline : PALETTE.gold }}>
                {credits > 0 ? credits : 'Get Credits'}
              </Typography>
            </Box>
          </Tooltip>
        )}
        {isLoggedIn && firstName && (
          <Typography sx={{ fontWeight: 500, color: PALETTE.subtext, fontSize: '0.85rem', display: { xs: 'none', sm: 'block' } }}>
            {firstName}
          </Typography>
        )}
        <ThemeToggle />
        {isLoggedIn && (
          <Tooltip title="Log out">
            <IconButton size="small" onClick={() => { logout(); navigate('/'); }} sx={{ color: PALETTE.subtext }}>
              <Logout fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </Box>
    </Box>
  );
}

function AgentFooter() {
  return (
    <Box sx={{ py: 2, px: { xs: 2, md: 3 }, textAlign: 'center', borderTop: '1px solid', borderColor: PALETTE.border }}>
      <Typography sx={{ fontWeight: 400, color: '#bbb', fontSize: '0.72rem' }}>
        Powered by <strong>Agent Rook</strong> &mdash; Your Strategic AI Scaffold
      </Typography>
    </Box>
  );
}

function FloatingChatButton() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isLoggedIn } = useAuth();

  // Hide on chat page, dashboard, and when logged out
  if (!isLoggedIn || location.pathname === '/chat' || location.pathname === '/dashboard') return null;

  return (
    <Tooltip title={`Ask ${config.name}`} placement="left">
      <Fab
        onClick={() => navigate('/chat')}
        sx={{
          position: 'fixed',
          bottom: { xs: 20, sm: 28 },
          right: { xs: 16, sm: 24 },
          zIndex: 1200,
          bgcolor: config.branding.secondary_color,
          color: 'white',
          boxShadow: `0 4px 14px ${config.branding.secondary_color}44`,
          '&:hover': { bgcolor: config.branding.secondary_color, opacity: 0.9 },
        }}
      >
        <CameraAlt />
      </Fab>
    </Tooltip>
  );
}

export default function AgentLayout({ children }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', bgcolor: PALETTE.bg }}>
      <AgentNav />
      <Box component="main" sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        {children}
      </Box>
      <AgentFooter />
      <FloatingChatButton />
    </Box>
  );
}

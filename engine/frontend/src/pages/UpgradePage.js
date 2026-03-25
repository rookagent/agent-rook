/**
 * UpgradePage — Credit pack purchase via Stripe checkout.
 * For now, shows credit packs with a "coming soon" state until
 * Stripe webhook is wired up in Session 4.
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Button,
  Chip,
} from '@mui/material';
import { ArrowBack, Star } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import config from '../agentConfig.json';

const CREDIT_PACKS = [
  { id: 'starter', name: 'Starter', credits: 50, price: '$4.99', popular: false },
  { id: 'pro', name: 'Pro', credits: 200, price: '$14.99', popular: true },
  { id: 'power', name: 'Power User', credits: 500, price: '$29.99', popular: false },
];

export default function UpgradePage() {
  const navigate = useNavigate();
  const { credits, isAdmin } = useAuth();

  const handlePurchase = (pack) => {
    // TODO: Stripe checkout redirect — wire up in Session 4
    alert(`Stripe checkout for ${pack.name} pack coming in Session 4!`);
  };

  return (
    <Box sx={{ flexGrow: 1, px: 2, py: 4, bgcolor: 'background.default' }}>
      <Box sx={{ maxWidth: 600, mx: 'auto' }}>
        {/* Back button */}
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate('/chat')}
          sx={{ mb: 3, color: 'text.secondary' }}
        >
          Back to chat
        </Button>

        <Typography
          variant="h4"
          sx={{
            fontFamily: `"${config.branding.fonts.heading}", cursive`,
            color: 'primary.main',
            fontWeight: 700,
            textAlign: 'center',
            mb: 1,
          }}
        >
          Get More Credits
        </Typography>
        <Typography sx={{ textAlign: 'center', color: 'text.secondary', fontSize: '0.9rem', mb: 1 }}>
          Each message costs 1 credit. You get {config.access.free_messages_per_day} free messages per day.
        </Typography>
        {credits > 0 && !isAdmin && (
          <Typography sx={{ textAlign: 'center', color: 'primary.main', fontWeight: 600, fontSize: '0.85rem', mb: 3 }}>
            Current balance: {credits} credits
          </Typography>
        )}
        {isAdmin && (
          <Typography sx={{ textAlign: 'center', color: 'primary.main', fontWeight: 600, fontSize: '0.85rem', mb: 3 }}>
            Admin account — unlimited messages
          </Typography>
        )}

        {/* Credit packs */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {CREDIT_PACKS.map((pack) => (
            <Paper
              key={pack.id}
              elevation={pack.popular ? 3 : 1}
              sx={{
                p: 3,
                borderRadius: 3,
                border: pack.popular ? '2px solid' : '1px solid',
                borderColor: pack.popular ? 'secondary.main' : 'divider',
                position: 'relative',
              }}
            >
              {pack.popular && (
                <Chip
                  icon={<Star sx={{ fontSize: 14 }} />}
                  label="Most Popular"
                  size="small"
                  sx={{
                    position: 'absolute', top: -12, right: 16,
                    bgcolor: 'secondary.main', color: 'white', fontWeight: 600,
                    fontSize: '0.7rem',
                  }}
                />
              )}
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography sx={{ fontWeight: 700, fontSize: '1.1rem', color: 'text.primary' }}>
                    {pack.name}
                  </Typography>
                  <Typography sx={{ color: 'text.secondary', fontSize: '0.85rem' }}>
                    {pack.credits} credits
                  </Typography>
                </Box>
                <Box sx={{ textAlign: 'right' }}>
                  <Typography sx={{ fontWeight: 700, fontSize: '1.2rem', color: 'primary.main' }}>
                    {pack.price}
                  </Typography>
                  <Button
                    variant={pack.popular ? 'contained' : 'outlined'}
                    size="small"
                    onClick={() => handlePurchase(pack)}
                    sx={{ mt: 0.5 }}
                  >
                    Buy
                  </Button>
                </Box>
              </Box>
            </Paper>
          ))}
        </Box>
      </Box>
    </Box>
  );
}

/**
 * SpokePageShell — shared layout for all spoke pages.
 * Title, search, add button, consistent styling.
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, TextField, Button, IconButton, InputAdornment } from '@mui/material';
import { Add, Search, ArrowBack } from '@mui/icons-material';

export default function SpokePageShell({ title, color, onAdd, searchValue, onSearchChange, children }) {
  const navigate = useNavigate();

  return (
    <Box sx={{ flexGrow: 1, px: { xs: 2, sm: 3, md: 4 }, py: 3, bgcolor: 'background.default', minHeight: 0 }}>
      <Box sx={{ maxWidth: 900, mx: 'auto' }}>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <IconButton size="small" onClick={() => navigate('/dashboard')} sx={{ color: 'text.secondary' }}>
            <ArrowBack fontSize="small" />
          </IconButton>
          <Typography sx={{ fontWeight: 700, fontSize: '1.4rem', color: color || 'text.primary', flexGrow: 1 }}>
            {title}
          </Typography>
          {onAdd && (
            <Button variant="contained" startIcon={<Add />} onClick={onAdd}
              sx={{ bgcolor: color, '&:hover': { bgcolor: color, opacity: 0.9 } }}>
              Add
            </Button>
          )}
        </Box>

        {/* Search */}
        {onSearchChange && (
          <TextField
            size="small"
            placeholder={`Search ${title.toLowerCase()}...`}
            value={searchValue || ''}
            onChange={(e) => onSearchChange(e.target.value)}
            fullWidth
            sx={{ mb: 2 }}
            InputProps={{
              startAdornment: <InputAdornment position="start"><Search sx={{ fontSize: 18, color: 'text.secondary' }} /></InputAdornment>,
            }}
          />
        )}

        {children}
      </Box>
    </Box>
  );
}

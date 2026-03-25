/**
 * SignupPage — Email + password + name, agent-branded.
 */
import React, { useState } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Typography,
  TextField,
  Button,
  Alert,
  Paper,
  Link,
} from '@mui/material';
import { register, setToken } from '../services/chatApi';
import { useAuth } from '../context/AuthContext';
import config from '../agentConfig.json';

export default function SignupPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setLoading(true);

    try {
      const res = await register(email, password, name);
      setToken(res.token);
      login(res.token, res.user);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{
      flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
      px: 2, py: 4, bgcolor: '#FBF9F7',
    }}>
      <Paper elevation={1} sx={{ maxWidth: 400, width: '100%', p: 4, borderRadius: 3 }}>
        <Typography
          variant="h4"
          sx={{
            fontFamily: `"${config.branding.fonts.heading}", cursive`,
            color: 'primary.main',
            fontWeight: 700,
            textAlign: 'center',
            mb: 0.5,
          }}
        >
          {config.name}
        </Typography>
        <Typography sx={{ textAlign: 'center', color: 'text.secondary', fontSize: '0.85rem', mb: 3 }}>
          Create your account
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <Box component="form" onSubmit={handleSubmit}>
          <TextField
            label="Name"
            fullWidth
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            sx={{ mb: 2 }}
            autoComplete="name"
          />
          <TextField
            label="Email"
            type="email"
            fullWidth
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            sx={{ mb: 2 }}
            autoComplete="email"
          />
          <TextField
            label="Password"
            type="password"
            fullWidth
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            helperText="At least 6 characters"
            sx={{ mb: 3 }}
            autoComplete="new-password"
          />
          <Button
            type="submit"
            variant="contained"
            fullWidth
            disabled={loading}
            size="large"
            sx={{ mb: 2 }}
          >
            {loading ? 'Creating account...' : 'Sign Up'}
          </Button>
        </Box>

        <Typography sx={{ textAlign: 'center', fontSize: '0.85rem' }}>
          Already have an account?{' '}
          <Link component={RouterLink} to="/login" sx={{ color: 'primary.main', fontWeight: 600 }}>
            Log in
          </Link>
        </Typography>

        <Typography sx={{ textAlign: 'center', fontSize: '0.72rem', color: '#bbb', mt: 2 }}>
          {config.access.free_messages_per_day} free messages per day, no credit card required.
        </Typography>
      </Paper>
    </Box>
  );
}

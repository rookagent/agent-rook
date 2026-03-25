/**
 * Chat API service for Agent Rook.
 *
 * Single authenticated mode — JWT required for all chat.
 * Retry logic with exponential backoff on network errors.
 */
import config from '../agentConfig.json';

const API_URL = config.api_url;
const TOKEN_KEY = 'rook_token';

const MAX_RETRIES = 2;
const BASE_DELAY_MS = 2000;

/**
 * Get the stored auth token.
 */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Store the auth token.
 */
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

/**
 * Clear the auth token.
 */
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * Extract a friendly error message from a failed response.
 */
async function _friendlyError(response) {
  try {
    const data = await response.json();
    if (data.error) return data.error;
    if (data.message) return data.message;
  } catch (_) {}
  if (response.status === 429) return "I need a quick breather — try again in a moment!";
  if (response.status === 401 || response.status === 403) return "Your session may have expired. Try logging in again.";
  if (response.status >= 500) return "The server hit a bump. Try again in a few seconds!";
  return "Couldn't connect right now. Give it another try in a moment!";
}

/**
 * Check if an error is retryable (network/timeout, not auth/rate-limit).
 */
function _isRetryableError(err) {
  if (err.status && err.status < 500) return false;
  const msg = (err.message || '').toLowerCase();
  return (
    err.name === 'TypeError' ||
    msg.includes('failed to fetch') ||
    msg.includes('network') ||
    msg.includes('timeout') ||
    msg.includes('aborted') ||
    msg.includes('connection') ||
    msg.includes('load failed')
  );
}

function _sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Send a chat message (authenticated, non-streaming).
 * Returns { message, data, credits, remaining, access_type }
 */
export async function sendChatMessage(message, history = []) {
  const token = getToken();
  let lastError = null;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      if (attempt > 0) await _sleep(BASE_DELAY_MS * attempt);

      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ message, history }),
      });

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          const err = new Error('Authentication required');
          err.status = response.status;
          throw err;
        }
        const err = new Error(await _friendlyError(response));
        err.status = response.status;
        throw err;
      }

      return response.json();
    } catch (err) {
      lastError = err;
      if (!_isRetryableError(err) || attempt >= MAX_RETRIES) {
        throw err;
      }
    }
  }

  throw lastError;
}

/**
 * Register a new account.
 * Returns { token, user, message }
 */
export async function register(email, password, name) {
  const response = await fetch(`${API_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      password,
      name,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || 'Registration failed');
  }

  return response.json();
}

/**
 * Log in with email + password.
 * Returns { token, user }
 */
export async function login(email, password) {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || 'Login failed');
  }

  return response.json();
}

/**
 * Get current user profile.
 * Returns { user }
 */
export async function getMe() {
  const token = getToken();
  const response = await fetch(`${API_URL}/auth/me`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });

  if (!response.ok) {
    const err = new Error('Session expired');
    err.status = response.status;
    throw err;
  }

  return response.json();
}

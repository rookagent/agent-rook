/**
 * Spoke API — generic CRUD factory for spoke pages.
 * Reuses auth token from chatApi.
 */
import { getToken } from './chatApi';
import config from '../agentConfig.json';

const API_URL = config.api_url;

async function authFetch(path, { method = 'GET', body, params } = {}) {
  const token = getToken();
  const url = new URL(path, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v);
    });
  }

  const headers = { 'Authorization': `Bearer ${token}` };
  const opts = { method, headers };
  if (body) {
    headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }

  const response = await fetch(url.pathname + url.search, opts);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const err = new Error(data.error || `Request failed (${response.status})`);
    err.status = response.status;
    throw err;
  }
  return response.json();
}

function createSpokeApi(resource) {
  return {
    list: (params) => authFetch(`${API_URL}/${resource}`, { params }),
    get: (id) => authFetch(`${API_URL}/${resource}/${id}`),
    create: (data) => authFetch(`${API_URL}/${resource}`, { method: 'POST', body: data }),
    update: (id, data) => authFetch(`${API_URL}/${resource}/${id}`, { method: 'PUT', body: data }),
    delete: (id) => authFetch(`${API_URL}/${resource}/${id}`, { method: 'DELETE' }),
  };
}

export const clientsApi = createSpokeApi('clients');
export const scheduleApi = createSpokeApi('schedule');
export const tasksApi = createSpokeApi('tasks');
export const expensesApi = createSpokeApi('expenses');
export const checklistsApi = createSpokeApi('checklists');
export const sessionPlansApi = createSpokeApi('session-plans');
export const notesApi = createSpokeApi('notes');

export async function getDashboardSummary() {
  return authFetch(`${API_URL}/dashboard/summary`);
}

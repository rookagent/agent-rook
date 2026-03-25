/**
 * Agent Rook — App router with dark mode support.
 */
import React, { useState, useMemo, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { lightTheme, darkTheme } from './theme';
import { AuthProvider, useAuth } from './context/AuthContext';
import AgentLayout from './components/AgentLayout';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import DashboardPage from './pages/DashboardPage';
import ChatPage from './pages/ChatPage';
import UpgradePage from './pages/UpgradePage';
import ClientsPage from './pages/ClientsPage';
import SchedulePage from './pages/SchedulePage';
import TasksPage from './pages/TasksPage';
import ExpensesPage from './pages/ExpensesPage';
import ChecklistsPage from './pages/ChecklistsPage';
import SessionPlansPage from './pages/SessionPlansPage';
import NotesPage from './pages/NotesPage';

// Theme context
const ThemeModeContext = createContext({ mode: 'light', toggle: () => {} });
export function useThemeMode() { return useContext(ThemeModeContext); }

function ProtectedRoute({ children }) {
  const { isLoggedIn } = useAuth();
  if (!isLoggedIn) return <Navigate to="/login" replace />;
  return children;
}

function PublicRoute({ children }) {
  const { isLoggedIn } = useAuth();
  if (isLoggedIn) return <Navigate to="/dashboard" replace />;
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<PublicRoute><Navigate to="/login" replace /></PublicRoute>} />
      <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
      <Route path="/signup" element={<PublicRoute><SignupPage /></PublicRoute>} />
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/chat" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
      <Route path="/upgrade" element={<ProtectedRoute><UpgradePage /></ProtectedRoute>} />
      <Route path="/clients" element={<ProtectedRoute><ClientsPage /></ProtectedRoute>} />
      <Route path="/schedule" element={<ProtectedRoute><SchedulePage /></ProtectedRoute>} />
      <Route path="/tasks" element={<ProtectedRoute><TasksPage /></ProtectedRoute>} />
      <Route path="/expenses" element={<ProtectedRoute><ExpensesPage /></ProtectedRoute>} />
      <Route path="/checklists" element={<ProtectedRoute><ChecklistsPage /></ProtectedRoute>} />
      <Route path="/session-plans" element={<ProtectedRoute><SessionPlansPage /></ProtectedRoute>} />
      <Route path="/notes" element={<ProtectedRoute><NotesPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  const [mode, setMode] = useState(() => localStorage.getItem('rook_theme') || 'light');

  const toggle = () => {
    const next = mode === 'light' ? 'dark' : 'light';
    setMode(next);
    localStorage.setItem('rook_theme', next);
  };

  const theme = useMemo(() => mode === 'dark' ? darkTheme : lightTheme, [mode]);

  return (
    <ThemeModeContext.Provider value={{ mode, toggle }}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter>
          <AuthProvider>
            <AgentLayout>
              <AppRoutes />
            </AgentLayout>
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </ThemeModeContext.Provider>
  );
}

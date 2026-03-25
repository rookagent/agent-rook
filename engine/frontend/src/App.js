/**
 * Agent Rook — App router.
 *
 * Routes:
 *   /          → Dashboard (logged in) or Login (logged out)
 *   /login     → Login page
 *   /signup    → Signup page
 *   /dashboard → Hub dashboard with feature cards (protected)
 *   /chat      → Chat page (protected)
 *   /upgrade   → Credit purchase (protected)
 */
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import theme from './theme';
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
  return (
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
  );
}

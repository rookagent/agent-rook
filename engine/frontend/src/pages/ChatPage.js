/**
 * ChatPage — Full-page chat with the agent.
 * ChatWidget fills the available space between nav and footer.
 * Accepts a pre-filled prompt via location.state.prompt (from dashboard cards).
 */
import React from 'react';
import { useLocation } from 'react-router-dom';
import { Box } from '@mui/material';
import ChatWidget from '../components/ChatWidget';

export default function ChatPage() {
  const location = useLocation();
  const initialPrompt = location.state?.prompt || null;

  return (
    <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', minHeight: 0, bgcolor: '#FBF9F7' }}>
      <ChatWidget initialPrompt={initialPrompt} />
    </Box>
  );
}

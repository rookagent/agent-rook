/**
 * Agent Rook — Full-page chat widget.
 *
 * Adapted from Daisy's ChatWidget. Stripped out:
 * - Parent/provider/teacher mode branching
 * - Provider card rendering
 * - ElevenLabs TTS + wake word
 * - Document upload
 * - daisy-chart HTML blocks
 *
 * Kept: markdown rendering, Web Speech STT, print, suggestion chips,
 * error retry, thinking indicator. All branding from agentConfig.
 */
import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  TextField,
  IconButton,
  Chip,
  CircularProgress,
  Button,
} from '@mui/material';
import {
  Send,
  DeleteOutline,
  Mic,
  MicOff,
  PrintOutlined,
  Refresh,
} from '@mui/icons-material';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import { streamChatMessage, getToken } from '../services/chatApi';
import { useAuth } from '../context/AuthContext';
import config from '../agentConfig.json';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const { primary_color } = config.branding;

// Markdown component overrides — styled to match agent branding
const markdownComponents = {
  p: ({ children }) => (
    <Typography variant="body2" sx={{ fontSize: '0.88rem', lineHeight: 1.6, mb: 0.5 }}>
      {children}
    </Typography>
  ),
  strong: ({ children }) => <Box component="span" sx={{ fontWeight: 600 }}>{children}</Box>,
  em: ({ children }) => <Box component="span" sx={{ fontStyle: 'italic' }}>{children}</Box>,
  h1: ({ children }) => (
    <Typography sx={{ color: primary_color, fontWeight: 700, fontSize: '1.1rem', mt: 1.5, mb: 0.5 }}>
      {children}
    </Typography>
  ),
  h2: ({ children }) => (
    <Typography sx={{ color: primary_color, fontWeight: 700, fontSize: '1rem', mt: 1.5, mb: 0.5 }}>
      {children}
    </Typography>
  ),
  h3: ({ children }) => (
    <Typography sx={{ color: primary_color, fontWeight: 600, fontSize: '0.95rem', mt: 1, mb: 0.5 }}>
      {children}
    </Typography>
  ),
  ul: ({ children }) => (
    <Box component="ul" sx={{ pl: 2.5, my: 0.5, '& li': { mb: 0.25, fontSize: '0.88rem' } }}>
      {children}
    </Box>
  ),
  ol: ({ children }) => (
    <Box component="ol" sx={{ pl: 2.5, my: 0.5, '& li': { mb: 0.25, fontSize: '0.88rem' } }}>
      {children}
    </Box>
  ),
  li: ({ children }) => <Box component="li" sx={{ fontSize: '0.88rem', lineHeight: 1.6 }}>{children}</Box>,
  table: ({ children }) => (
    <Box component="table" sx={{ borderCollapse: 'collapse', width: '100%', my: 1 }}>{children}</Box>
  ),
  thead: ({ children }) => <Box component="thead">{children}</Box>,
  tbody: ({ children }) => <Box component="tbody">{children}</Box>,
  tr: ({ children, ...props }) => (
    <Box component="tr" sx={{ '&:nth-of-type(even)': { bgcolor: `${primary_color}08` } }} {...props}>
      {children}
    </Box>
  ),
  th: ({ children }) => (
    <Box component="th" sx={{
      border: '1px solid #ddd', px: 1.5, py: 0.75, fontSize: '0.82rem',
      textAlign: 'center', bgcolor: primary_color, color: 'white', fontWeight: 600,
    }}>
      {children}
    </Box>
  ),
  td: ({ children }) => (
    <Box component="td" sx={{ border: '1px solid #ddd', px: 1.5, py: 0.75, fontSize: '0.82rem', textAlign: 'center' }}>
      {children}
    </Box>
  ),
  code: ({ children, inline }) => inline
    ? <Box component="code" sx={{ bgcolor: 'rgba(0,0,0,0.05)', px: 0.5, borderRadius: 0.5, fontSize: '0.82rem', fontFamily: 'monospace' }}>{children}</Box>
    : <Box component="pre" sx={{ bgcolor: 'rgba(0,0,0,0.04)', p: 1.5, borderRadius: 1, overflow: 'auto', fontSize: '0.82rem', fontFamily: 'monospace', my: 0.5 }}><code>{children}</code></Box>,
  hr: () => <Box component="hr" sx={{ border: 'none', borderTop: '1px solid #ddd', my: 1 }} />,
  a: ({ href, children }) => (
    <Box component="a" href={href} target="_blank" rel="noopener noreferrer"
      sx={{ color: primary_color, textDecoration: 'underline', '&:hover': { opacity: 0.8 } }}>
      {children}
    </Box>
  ),
  blockquote: ({ children }) => (
    <Box sx={{ borderLeft: `3px solid ${config.branding.secondary_color}`, pl: 1.5, ml: 0.5, my: 0.5, color: 'text.secondary', fontStyle: 'italic' }}>
      {children}
    </Box>
  ),
};

// Web Speech API detection
function isSpeechRecognitionSupported() {
  return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
}

function createSpeechRecognition({ onResult, onStart, onEnd, onError }) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = 'en-US';

  recognition.onresult = (event) => {
    const result = event.results[event.results.length - 1];
    const transcript = result[0].transcript;
    onResult(transcript, result.isFinal);
  };
  recognition.onstart = onStart;
  recognition.onend = onEnd;
  recognition.onerror = onError;
  return recognition;
}

function ChatWidget({ initialPrompt }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [consecutiveErrors, setConsecutiveErrors] = useState(0);
  const [isListening, setIsListening] = useState(false);
  const [snack, setSnack] = useState({ open: false, message: '', severity: 'info' });
  const initialPromptSent = useRef(false);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const recognitionRef = useRef(null);
  const isSendingRef = useRef(false);

  const { credits, isAdmin, updateCredits } = useAuth();
  const sttSupported = isSpeechRecognitionSupported();

  // Auto-scroll on new messages
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading]);

  // Focus input on mount
  useEffect(() => {
    if (inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, []);

  // Ref so voice auto-send can call handleSend
  const handleSendRef = useRef(null);

  // Voice: start/stop speech recognition
  const voiceSentRef = useRef(false);
  const toggleListening = useCallback(() => {
    if (isListening) {
      if (recognitionRef.current) recognitionRef.current.stop();
      setIsListening(false);
      return;
    }
    if (!sttSupported) return;

    voiceSentRef.current = false;
    const recognition = createSpeechRecognition({
      onResult: (transcript, isFinal) => {
        setInput(transcript);
        if (isFinal && transcript.trim() && !voiceSentRef.current) {
          voiceSentRef.current = true;
          if (handleSendRef.current) handleSendRef.current(transcript.trim());
          setInput('');
        }
      },
      onStart: () => setIsListening(true),
      onEnd: () => setIsListening(false),
      onError: () => setIsListening(false),
    });
    recognitionRef.current = recognition;
    recognition.start();
  }, [isListening, sttSupported]);

  const handlePrint = useCallback((content) => {
    const printWindow = window.open('', '_blank');
    if (!printWindow) return;
    const dateStr = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    printWindow.document.write(`<!DOCTYPE html><html><head><title>${config.name}</title>
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;600&family=Quicksand:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  body { font-family: '${config.branding.fonts.body}', Arial, sans-serif; max-width: 700px; margin: 40px auto; color: #333; line-height: 1.7; padding: 0 20px; font-size: 14px; }
  h1 { font-family: '${config.branding.fonts.heading}', cursive; color: ${primary_color}; font-size: 1.3rem; margin: 0; }
  .subtitle { color: #888; font-size: 0.8rem; margin-bottom: 16px; }
  .rule { border: none; border-top: 2px solid ${config.branding.secondary_color}; margin-bottom: 20px; }
  .content { white-space: pre-wrap; word-wrap: break-word; }
  table { border-collapse: collapse; width: 100%; margin: 8px 0; }
  th, td { border: 1px solid #ccc; padding: 8px 12px; text-align: center; font-size: 13px; }
  th { background-color: ${primary_color}; color: white; font-weight: 600; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  @media print { th { background-color: ${primary_color} !important; color: white !important; } }
</style></head><body>
<h1>${config.name}</h1>
<div class="subtitle">${config.tagline} &bull; ${dateStr}</div>
<hr class="rule">
<div class="content">${content.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
</body></html>`);
    printWindow.document.close();
    printWindow.print();
  }, []);

  const handleSend = useCallback(async (text) => {
    const messageText = (text || input).trim();
    if (!messageText || loading) return;
    if (isSendingRef.current) return;
    isSendingRef.current = true;

    setInput('');
    setHasInteracted(true);

    const userMsg = { role: 'user', content: messageText };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const maxHistory = 20;
      const history = [...messages, userMsg]
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .map((m) => ({ role: m.role, content: m.content }))
        .slice(-maxHistory);

      // Add empty streaming assistant message
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '', streaming: true },
      ]);

      let fullText = '';
      let hadError = false;

      await streamChatMessage(messageText, history.slice(0, -1), {
        onToken: (chunk) => {
          fullText += chunk;
          setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (updated[lastIdx]?.streaming) {
              updated[lastIdx] = { ...updated[lastIdx], content: fullText };
            }
            return updated;
          });
        },
        onStatus: (statusText) => {
          setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (updated[lastIdx]?.streaming) {
              updated[lastIdx] = { ...updated[lastIdx], status: statusText };
            }
            return updated;
          });
        },
        onDone: (payload) => {
          if (payload?.credits_remaining !== undefined) {
            updateCredits(payload.credits_remaining);
          }
        },
        onError: (errMsg) => {
          hadError = true;
          fullText = errMsg || "Something went wrong. Try again in a moment.";
        },
      });

      // Finalize — remove streaming flag
      setMessages((prev) => {
        const updated = [...prev];
        const lastIdx = updated.length - 1;
        if (updated[lastIdx]?.streaming) {
          updated[lastIdx] = {
            role: 'assistant',
            content: fullText || "Done!",
            isError: hadError,
            retryMessage: hadError ? messageText : undefined,
          };
        }
        return updated;
      });

      if (hadError) {
        setConsecutiveErrors((prev) => prev + 1);
      } else {
        setConsecutiveErrors(0);
      }
    } catch (err) {
      setConsecutiveErrors((prev) => prev + 1);
      const errorCount = consecutiveErrors + 1;
      const refreshHint = errorCount >= 3
        ? " If this keeps happening, try refreshing the page."
        : "";

      const isAuthError = err.status === 401 || err.status === 403;
      const errorMessage = isAuthError
        ? "Your session has expired. Please log in again."
        : `${err.message || "Something went wrong. Try again in a moment."}${refreshHint}`;

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: errorMessage,
          isError: true,
          retryMessage: isAuthError ? undefined : messageText,
        },
      ]);
    } finally {
      setLoading(false);
      isSendingRef.current = false;
    }
  }, [input, loading, messages, updateCredits, consecutiveErrors]);

  handleSendRef.current = handleSend;

  // --- Session-end memory extraction ---
  const messagesRef = useRef(messages);
  messagesRef.current = messages;
  const extractingRef = useRef(false);

  const extractMemories = useCallback(() => {
    const msgs = messagesRef.current;
    if (extractingRef.current || msgs.length < 4) return;
    extractingRef.current = true;

    const token = getToken();
    const payload = JSON.stringify({
      messages: msgs
        .filter(m => m.role === 'user' || (m.role === 'assistant' && !m.isError))
        .map(m => ({ role: m.role, content: m.content })),
    });

    // Use sendBeacon on unload (fire-and-forget), regular fetch otherwise
    if (document.visibilityState === 'hidden' || !document.hasFocus()) {
      const blob = new Blob([payload], { type: 'application/json' });
      navigator.sendBeacon?.(`${config.api_url}/memories/extract?token=${token}`, blob);
    } else {
      fetch(`${config.api_url}/memories/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: payload,
        keepalive: true,
      })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (data?.saved > 0) {
            setSnack({ open: true, message: 'Memories saved', severity: 'info' });
          }
        })
        .catch(() => {});
    }
  }, []);

  // Inactivity timer — extract after 2 minutes of no new messages
  const inactivityTimer = useRef(null);
  useEffect(() => {
    if (messages.length >= 4) {
      clearTimeout(inactivityTimer.current);
      inactivityTimer.current = setTimeout(extractMemories, 2 * 60 * 1000);
    }
    return () => clearTimeout(inactivityTimer.current);
  }, [messages, extractMemories]);

  // Extract on page unload / navigation away
  useEffect(() => {
    const handleBeforeUnload = () => extractMemories();
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      // Component unmount (navigation away) — extract if enough messages
      extractMemories();
    };
  }, [extractMemories]);

  // Auto-send initial prompt from dashboard card click
  useEffect(() => {
    if (initialPrompt && !initialPromptSent.current && handleSendRef.current) {
      initialPromptSent.current = true;
      // Small delay so the component is fully mounted
      setTimeout(() => handleSendRef.current(initialPrompt), 300);
    }
  }, [initialPrompt]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClear = () => {
    setMessages([]);
    setHasInteracted(false);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      {/* Messages Area */}
      <Box
        sx={{
          flexGrow: 1,
          overflowY: 'auto',
          px: { xs: 2, sm: 3 },
          py: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 1.5,
        }}
      >
        {/* Welcome message */}
        {messages.length === 0 && (
          <Box sx={{ maxWidth: 600, mx: 'auto', width: '100%', mt: { xs: 2, sm: 4 } }}>
            <Box
              sx={{
                bgcolor: 'background.paper',
                p: 3,
                borderRadius: '4px 16px 16px 16px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                mb: 2,
              }}
            >
              <Typography variant="body1" sx={{ fontSize: '0.95rem', lineHeight: 1.6 }}>
                {config.welcome_message}
              </Typography>
            </Box>

            {/* Suggestion chips */}
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
              {config.suggestions.map((suggestion) => (
                <Chip
                  key={suggestion}
                  label={suggestion}
                  size="small"
                  onClick={() => handleSend(suggestion)}
                  sx={{
                    bgcolor: 'background.paper',
                    border: '1px solid',
                    borderColor: 'primary.light',
                    color: 'primary.main',
                    fontWeight: 500,
                    fontSize: '0.78rem',
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'primary.main', color: 'white' },
                  }}
                />
              ))}
            </Box>
          </Box>
        )}

        {/* Message bubbles */}
        {messages.map((msg, idx) => (
          <Box key={idx} sx={{ maxWidth: 700, mx: 'auto', width: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
              <Box
                sx={{
                  maxWidth: '85%',
                  p: 2,
                  borderRadius: msg.role === 'user' ? '16px 4px 16px 16px' : '4px 16px 16px 16px',
                  bgcolor: msg.role === 'user' ? 'primary.main' : 'background.paper',
                  color: msg.role === 'user' ? 'white' : 'text.primary',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                }}
              >
                {msg.role === 'assistant' ? (
                  <Box sx={{ fontSize: '0.88rem', lineHeight: 1.6 }}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                      {msg.content}
                    </ReactMarkdown>
                    {msg.streaming && (
                      <Box component="span" sx={{
                        display: 'inline-block', width: 6, height: 14,
                        bgcolor: 'primary.main', ml: 0.3, mb: '-2px',
                        animation: 'blink 1s step-end infinite',
                        '@keyframes blink': { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0 } },
                      }} />
                    )}
                    {msg.status && msg.streaming && (
                      <Typography variant="caption" sx={{
                        display: 'block', mt: 0.5, color: 'primary.light',
                        fontStyle: 'italic', fontSize: '0.75rem',
                      }}>
                        {msg.status}
                      </Typography>
                    )}
                  </Box>
                ) : (
                  <Typography variant="body2" sx={{ fontSize: '0.88rem', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                    {msg.content}
                  </Typography>
                )}
              </Box>
            </Box>

            {/* Print button */}
            {msg.role === 'assistant' && msg.content && (
              <IconButton
                size="small"
                onClick={() => handlePrint(msg.content)}
                title="Print this response"
                sx={{ mt: 0.25, ml: 0.5, opacity: 0.3, '&:hover': { opacity: 0.8 }, p: 0.3 }}
              >
                <PrintOutlined sx={{ fontSize: 14 }} />
              </IconButton>
            )}

            {/* Try Again button on errors */}
            {msg.isError && msg.retryMessage && !loading && (
              <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<Refresh sx={{ fontSize: 14 }} />}
                  onClick={() => handleSend(msg.retryMessage)}
                  sx={{
                    fontSize: '0.75rem', fontWeight: 600,
                    borderColor: 'primary.main', color: 'primary.main',
                    borderRadius: 2, py: 0.25,
                    '&:hover': { bgcolor: 'primary.main', color: 'white' },
                  }}
                >
                  Try Again
                </Button>
                {consecutiveErrors >= 3 && (
                  <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.65rem' }}>
                    Try refreshing the page
                  </Typography>
                )}
              </Box>
            )}
          </Box>
        ))}

        {/* Thinking indicator */}
        {loading && (
          <Box sx={{ maxWidth: 700, mx: 'auto', width: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'flex-start' }}>
              <Box
                sx={{
                  bgcolor: 'background.paper',
                  px: 2,
                  py: 1.2,
                  borderRadius: '4px 16px 16px 16px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                }}
              >
                <Box component="span" sx={{ fontSize: '0.88rem', color: 'primary.main', fontStyle: 'italic' }}>
                  Thinking...
                </Box>
                {[0, 1, 2].map((i) => (
                  <Box
                    key={i}
                    sx={{
                      width: 6, height: 6, borderRadius: '50%', bgcolor: 'primary.light',
                      animation: 'bounce 1.4s ease-in-out infinite',
                      animationDelay: `${i * 0.2}s`,
                      '@keyframes bounce': {
                        '0%, 80%, 100%': { transform: 'scale(0.6)' },
                        '40%': { transform: 'scale(1)' },
                      },
                    }}
                  />
                ))}
              </Box>
            </Box>
          </Box>
        )}

        <div ref={messagesEndRef} />
      </Box>

      {/* Input Area */}
      <Box
        sx={{
          p: { xs: 1.5, sm: 2 },
          borderTop: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
          display: 'flex',
          gap: 1,
          alignItems: 'flex-end',
        }}
      >
        {/* Mic button */}
        {sttSupported && (
          <IconButton
            onClick={toggleListening}
            disabled={loading}
            sx={{
              width: 40, height: 40,
              bgcolor: isListening ? 'error.main' : 'grey.100',
              color: isListening ? 'white' : 'text.secondary',
              '&:hover': { bgcolor: isListening ? 'error.dark' : 'grey.200' },
              ...(isListening && {
                animation: 'micPulse 1.5s ease-in-out infinite',
                '@keyframes micPulse': {
                  '0%, 100%': { boxShadow: '0 0 0 0 rgba(211, 47, 47, 0.4)' },
                  '50%': { boxShadow: '0 0 0 8px rgba(211, 47, 47, 0)' },
                },
              }),
            }}
            title={isListening ? 'Stop listening' : 'Voice input'}
          >
            {isListening ? <MicOff sx={{ fontSize: 20 }} /> : <Mic sx={{ fontSize: 20 }} />}
          </IconButton>
        )}
        <TextField
          inputRef={inputRef}
          fullWidth
          multiline
          maxRows={3}
          size="small"
          placeholder={isListening ? 'Listening...' : `Ask ${config.name} anything...`}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: 3,
              fontSize: '0.88rem',
            },
          }}
        />
        {/* Clear button */}
        {messages.length > 0 && (
          <IconButton
            size="small"
            onClick={handleClear}
            sx={{ width: 40, height: 40, color: 'text.secondary' }}
            title="Clear chat"
          >
            <DeleteOutline sx={{ fontSize: 20 }} />
          </IconButton>
        )}
        {/* Send button */}
        <IconButton
          onClick={() => handleSend()}
          disabled={!input.trim() || loading}
          sx={{
            bgcolor: 'primary.main', color: 'white',
            width: 40, height: 40,
            '&:hover': { bgcolor: 'primary.dark' },
            '&.Mui-disabled': { bgcolor: 'grey.200', color: 'grey.400' },
          }}
        >
          {loading ? <CircularProgress size={20} color="inherit" /> : <Send sx={{ fontSize: 20 }} />}
        </IconButton>
      </Box>

      {/* Memory extraction snackbar */}
      <Snackbar
        open={snack.open}
        autoHideDuration={2500}
        onClose={() => setSnack(s => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={snack.severity} variant="standard" sx={{ fontSize: '0.8rem' }}
          onClose={() => setSnack(s => ({ ...s, open: false }))}>
          {snack.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default ChatWidget;

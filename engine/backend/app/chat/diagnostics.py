"""
Agent Rook — Self-diagnosis system.

Built into the engine so every agent can diagnose errors and explain
what went wrong. Catches tool failures, API errors, knowledge gaps,
and access issues — then formats a human-readable explanation.
"""
import logging
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Error categories ──

class DiagnosticResult:
    """Structured diagnosis of what went wrong."""
    def __init__(self, category, summary, detail, suggestion, raw_error=None):
        self.category = category      # tool_error, api_error, access_error, knowledge_gap, config_error
        self.summary = summary        # One-line for the user
        self.detail = detail          # Technical detail
        self.suggestion = suggestion  # What the user can do
        self.raw_error = raw_error    # Original exception
        self.timestamp = datetime.utcnow().isoformat()

    def to_user_message(self):
        """Format as a message the agent can include in its response."""
        return (
            f"**Something went wrong:** {self.summary}\n\n"
            f"{self.detail}\n\n"
            f"**What to do:** {self.suggestion}"
        )

    def to_dict(self):
        return {
            'category': self.category,
            'summary': self.summary,
            'detail': self.detail,
            'suggestion': self.suggestion,
            'timestamp': self.timestamp,
        }


def diagnose_tool_error(tool_name, tool_params, error):
    """Diagnose a tool execution failure."""
    err_str = str(error)

    if 'not found' in err_str.lower():
        return DiagnosticResult(
            category='tool_error',
            summary=f'The record wasn\'t found.',
            detail=f'Tool "{tool_name}" tried to access a record that doesn\'t exist or belongs to another user.',
            suggestion='Try listing your records first to get the correct ID, then retry.',
        )

    if 'required' in err_str.lower():
        return DiagnosticResult(
            category='tool_error',
            summary=f'Missing required information.',
            detail=f'Tool "{tool_name}" needs more data: {err_str}',
            suggestion='I\'ll ask for the missing details and try again.',
        )

    if 'permission' in err_str.lower() or 'authorized' in err_str.lower():
        return DiagnosticResult(
            category='access_error',
            summary='Permission denied.',
            detail=f'Tool "{tool_name}" couldn\'t access this resource.',
            suggestion='You may need to log in again, or this action may require a premium account.',
        )

    return DiagnosticResult(
        category='tool_error',
        summary=f'Tool "{tool_name}" encountered an error.',
        detail=f'Error: {err_str}',
        suggestion='Try rephrasing your request. If this keeps happening, it may be a bug — let your admin know.',
        raw_error=error,
    )


def diagnose_api_error(error):
    """Diagnose an AI API failure."""
    err_str = str(error).lower()

    if 'api key' in err_str or 'authentication' in err_str or '401' in err_str:
        return DiagnosticResult(
            category='config_error',
            summary='AI service authentication failed.',
            detail='The API key for the AI provider is missing or invalid.',
            suggestion='Check that your API key is set correctly in the .env file.',
            raw_error=error,
        )

    if 'rate limit' in err_str or '429' in err_str:
        return DiagnosticResult(
            category='api_error',
            summary='Hit the AI rate limit.',
            detail='Too many requests to the AI service in a short time.',
            suggestion='Wait a moment and try again. If this persists, you may need to upgrade your API plan.',
            raw_error=error,
        )

    if 'overloaded' in err_str or '529' in err_str or '503' in err_str:
        return DiagnosticResult(
            category='api_error',
            summary='AI service is temporarily overloaded.',
            detail='The AI provider is experiencing high traffic.',
            suggestion='Try again in 30 seconds. This is temporary.',
            raw_error=error,
        )

    if 'context' in err_str or 'token' in err_str and 'limit' in err_str:
        return DiagnosticResult(
            category='api_error',
            summary='Conversation is too long for the AI to process.',
            detail='The conversation history exceeded the model\'s context window.',
            suggestion='Start a new conversation. Long conversations use more AI capacity.',
            raw_error=error,
        )

    if 'timeout' in err_str or 'timed out' in err_str:
        return DiagnosticResult(
            category='api_error',
            summary='AI request timed out.',
            detail='The AI took too long to respond.',
            suggestion='Try a simpler question, or try again in a moment.',
            raw_error=error,
        )

    return DiagnosticResult(
        category='api_error',
        summary='AI service encountered an error.',
        detail=f'Error: {str(error)}',
        suggestion='Try again in a moment. If this persists, check the AI provider\'s status page.',
        raw_error=error,
    )


def diagnose_knowledge_gap(query):
    """Diagnose when knowledge lookup returns no results."""
    return DiagnosticResult(
        category='knowledge_gap',
        summary='No matching knowledge found.',
        detail=f'Searched the knowledge base for: "{query}" but found no relevant modules.',
        suggestion='Try rephrasing your question, or I can answer from my general knowledge (which may be less specific).',
    )


def diagnose_access_error(access_result):
    """Diagnose when the user can't access the chat."""
    return DiagnosticResult(
        category='access_error',
        summary=access_result.get('message', 'Access denied.'),
        detail='You\'ve used your free messages for today or your credits have run out.',
        suggestion='Visit the Upgrade page to get more credits, or come back tomorrow for more free messages.',
    )


def format_error_for_log(error, context=""):
    """Format an error for structured logging."""
    return {
        'error': str(error),
        'type': type(error).__name__,
        'context': context,
        'traceback': traceback.format_exc(),
        'timestamp': datetime.utcnow().isoformat(),
    }

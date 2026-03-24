"""
Agent Rook — Smart query routing.

Simple messages (greetings, thanks) use the fast model (cheaper).
Complex messages needing tools use the smart model.
"""

# Base patterns — always included
_BASE_SIMPLE_PATTERNS = {
    # Greetings
    'hi', 'hey', 'hello', 'howdy', 'hiya', 'yo',
    'good morning', 'good afternoon', 'good evening',
    'morning', 'afternoon', 'evening',
    # Thanks
    'thanks', 'thank you', 'thx', 'ty',
    'thanks so much', 'thank you so much', 'appreciate it',
    # Acknowledgments
    'ok', 'okay', 'got it', 'sounds good', 'perfect', 'great',
    'cool', 'awesome', 'nice', 'love it', 'wonderful', 'amazing',
    'will do', 'noted', 'understood',
    # Farewells
    'bye', 'goodbye', 'see you', 'see ya', 'later', 'night',
    'good night', 'have a good day', 'gotta go', 'ttyl',
    # Simple affirmations
    'yes', 'yeah', 'yep', 'yup', 'sure', 'absolutely', 'definitely',
    'no', 'nope', 'nah',
    # Emotional
    'lol', 'haha', 'hehe',
}


def is_simple_query(message: str, extra_patterns: set = None) -> bool:
    """
    Detect if a message is simple enough for the fast model (no tools needed).

    Args:
        message: The user's message text.
        extra_patterns: Optional additional patterns from agent.yaml config.

    Returns True for short greetings, thanks, acknowledgments, farewells.
    """
    if not message:
        return False

    clean = message.lower().strip().rstrip('!?.,:;')

    if len(clean) > 30:
        return False

    patterns = _BASE_SIMPLE_PATTERNS
    if extra_patterns:
        patterns = patterns | extra_patterns

    if clean in patterns:
        return True

    # Short greeting + continuation (e.g. "hi there!", "hey girl")
    for greeting in ('hi ', 'hey ', 'hello ', 'good morning', 'good afternoon', 'good evening'):
        if clean.startswith(greeting) and len(clean) < 25:
            if '?' not in message and not any(w in clean for w in ('how', 'what', 'when', 'where', 'why', 'can', 'help', 'tell')):
                return True

    return False

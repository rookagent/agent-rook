import os
import yaml

# Load agent.yaml
_AGENT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'agent.yaml')
try:
    with open(_AGENT_CONFIG_PATH) as f:
        AGENT_CONFIG = yaml.safe_load(f)
except FileNotFoundError:
    AGENT_CONFIG = {}

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///agentrook.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Fix Railway postgres:// -> postgresql://
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)

    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 hours

    # AI
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    ai_config = AGENT_CONFIG.get('ai', {})
    AI_MODEL_FAST = os.environ.get('AI_MODEL_FAST', ai_config.get('fast_model', 'claude-haiku-4-20250514'))
    AI_MODEL_SMART = os.environ.get('AI_MODEL_SMART', ai_config.get('smart_model', 'claude-sonnet-4-20250514'))
    AI_MAX_TOKENS = ai_config.get('max_tokens', 4096)

    # Redis (for rate limiting, memory cache, session buffer)
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))

    # Stripe
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

    # SendGrid (optional)
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
    SENDGRID_FROM_EMAIL = os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@example.com')

    # Frontend
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

    # Sentry (optional)
    SENTRY_DSN = os.environ.get('SENTRY_DSN')

    # Agent config (from agent.yaml)
    _agent = AGENT_CONFIG.get('agent', {})
    AGENT_NAME = _agent.get('name', 'Rook')
    AGENT_PERSONALITY = _agent.get('personality', 'You are a helpful AI assistant.')
    AGENT_TAGLINE = _agent.get('tagline', '')
    FREE_MESSAGES_PER_DAY = AGENT_CONFIG.get('access', {}).get('free_messages_per_day', 3)
    KNOWLEDGE_DIR = AGENT_CONFIG.get('knowledge', {}).get('directory', 'agent/knowledge')
    MEMORY_ENABLED = AGENT_CONFIG.get('memory', {}).get('enabled', True)
    MEMORY_CATEGORIES = AGENT_CONFIG.get('memory', {}).get('extraction_categories', ['preferences', 'facts', 'goals'])
    CHAT_WELCOME = AGENT_CONFIG.get('chat', {}).get('welcome_message', f"Hey! I'm {AGENT_NAME}. How can I help?")
    CHAT_SUGGESTIONS = AGENT_CONFIG.get('chat', {}).get('suggestions', [])
    CHAT_MAX_HISTORY = AGENT_CONFIG.get('chat', {}).get('max_history', 20)

    # Admin
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'

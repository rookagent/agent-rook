import os
import logging
from flask import Flask, jsonify
from .extensions import db, migrate, jwt, limiter, cors

logger = logging.getLogger(__name__)

def create_app(config_class=None):
    app = Flask(__name__)

    # Load config
    env = os.environ.get('FLASK_ENV', 'development')
    if config_class is None:
        from config.settings import DevelopmentConfig, ProductionConfig, TestingConfig
        configs = {
            'development': DevelopmentConfig,
            'production': ProductionConfig,
            'testing': TestingConfig,
        }
        config_class = configs.get(env, DevelopmentConfig)

    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Rate limiter with Redis
    redis_url = app.config.get('CELERY_BROKER_URL')
    if redis_url:
        try:
            limiter.init_app(app, storage_uri=redis_url)
        except Exception:
            limiter.init_app(app)
    else:
        limiter.init_app(app)

    # CORS
    frontend_url = app.config.get('FRONTEND_URL', '*')
    cors.init_app(app, resources={r"/api/*": {"origins": [frontend_url, "http://localhost:3000", "http://localhost:3001"]}})

    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    # Health check
    @app.route('/api/health')
    def health():
        return jsonify(status='ok', agent=app.config.get('AGENT_NAME', 'Rook'))

    # Register blueprints
    from .routes import register_blueprints
    register_blueprints(app)

    # Import models so Alembic sees them
    from .models import user, agent_memory, subscription, promo_code, client, schedule_event, task, note, expense, checklist, session_plan

    # Register chat tools from agent.yaml
    with app.app_context():
        from .chat.engine import register_tools
        register_tools(app)

    # Sentry (optional)
    dsn = app.config.get('SENTRY_DSN')
    if dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            sentry_sdk.init(dsn=dsn, integrations=[FlaskIntegration()])
        except ImportError:
            pass

    logger.info(f"Agent Rook initialized: {app.config.get('AGENT_NAME', 'Rook')}")
    return app

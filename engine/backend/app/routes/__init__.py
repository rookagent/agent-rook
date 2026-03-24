def register_blueprints(app):
    from .auth import auth_bp
    from .chat import chat_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')

    # Stripe (optional — only if keys configured)
    if app.config.get('STRIPE_SECRET_KEY'):
        from .stripe_webhook import stripe_bp
        app.register_blueprint(stripe_bp, url_prefix='/api/stripe')

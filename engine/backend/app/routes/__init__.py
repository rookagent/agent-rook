def register_blueprints(app):
    from .auth import auth_bp
    from .chat import chat_bp
    from .clients import clients_bp
    from .schedule import schedule_bp
    from .tasks import tasks_bp
    from .notes import notes_bp
    from .expenses import expenses_bp
    from .checklists import checklists_bp
    from .session_plans import session_plans_bp
    from .dashboard import dashboard_bp
    from .outreach import outreach_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(clients_bp, url_prefix='/api/clients')
    app.register_blueprint(schedule_bp, url_prefix='/api/schedule')
    app.register_blueprint(tasks_bp, url_prefix='/api/tasks')
    app.register_blueprint(notes_bp, url_prefix='/api/notes')
    app.register_blueprint(expenses_bp, url_prefix='/api/expenses')
    app.register_blueprint(checklists_bp, url_prefix='/api/checklists')
    app.register_blueprint(session_plans_bp, url_prefix='/api/session-plans')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(outreach_bp, url_prefix='/api/outreach')

    # Stripe (optional — only if keys configured)
    if app.config.get('STRIPE_SECRET_KEY'):
        from .stripe_webhook import stripe_bp
        app.register_blueprint(stripe_bp, url_prefix='/api/stripe')

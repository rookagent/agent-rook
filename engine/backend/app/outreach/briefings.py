"""
Agent Rook — Proactive Outreach: Morning Briefing + Weekly Roundup.

Generates email content based on user data. Designed to be triggered by:
- APScheduler (in-process, dev/small deployments)
- Celery beat (production)
- External cron (Railway, Heroku Scheduler)

Configurable in agent.yaml under outreach:
  outreach:
    morning_briefing: true
    weekly_roundup: true
    briefing_hour: 7        # 7 AM in user's timezone
    roundup_day: "monday"   # Day of week for weekly roundup
"""
import logging
from datetime import date, timedelta
from sqlalchemy import func

logger = logging.getLogger(__name__)


def generate_morning_briefing(user):
    """
    Generate morning briefing content for a user.
    Returns a dict with subject and html_body, or None if nothing to report.
    """
    from app.extensions import db
    from app.models.schedule_event import ScheduleEvent
    from app.models.task import Task

    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Today's events
    todays_events = ScheduleEvent.query.filter(
        ScheduleEvent.user_id == user.id,
        ScheduleEvent.date == today,
    ).order_by(ScheduleEvent.start_time.asc()).all()

    # Tomorrow's events (heads-up)
    tomorrows_events = ScheduleEvent.query.filter(
        ScheduleEvent.user_id == user.id,
        ScheduleEvent.date == tomorrow,
    ).order_by(ScheduleEvent.start_time.asc()).all()

    # Overdue tasks
    overdue_tasks = Task.query.filter(
        Task.user_id == user.id,
        Task.status != 'done',
        Task.due_date < today,
        Task.due_date.isnot(None),
    ).all()

    # Tasks due today
    due_today = Task.query.filter(
        Task.user_id == user.id,
        Task.status != 'done',
        Task.due_date == today,
    ).all()

    # Nothing to report?
    if not todays_events and not tomorrows_events and not overdue_tasks and not due_today:
        return None

    from config.settings import Config
    agent_name = Config.AGENT_NAME

    # Build HTML
    sections = []

    if todays_events:
        event_lines = []
        for e in todays_events:
            time_str = " at " + e.start_time.strftime("%I:%M %p") if e.start_time else ""
            event_lines.append(f'<li><strong>{e.title}</strong>{time_str}</li>')
        items = "".join(event_lines)
        sections.append(f'<h3>Today\'s Schedule</h3><ul>{items}</ul>')

    if due_today:
        items = "".join(f'<li>{t.title}{f" ({t.priority} priority)" if t.priority == "high" else ""}</li>' for t in due_today)
        sections.append(f'<h3>Due Today</h3><ul>{items}</ul>')

    if overdue_tasks:
        items = "".join(f'<li>{t.title} — was due {t.due_date.isoformat()}</li>' for t in overdue_tasks)
        sections.append(f'<h3>Overdue</h3><ul style="color:#c0392b;">{items}</ul>')

    if tomorrows_events:
        tmrw_lines = []
        for e in tomorrows_events:
            time_str = " at " + e.start_time.strftime("%I:%M %p") if e.start_time else ""
            tmrw_lines.append(f'<li>{e.title}{time_str}</li>')
        items = "".join(tmrw_lines)
        sections.append(f'<h3>Tomorrow</h3><ul>{items}</ul>')

    body = "\n".join(sections)
    first_name = (user.name or user.email).split(' ')[0] if hasattr(user, 'name') and user.name else user.email.split('@')[0]

    html = f"""
    <div style="font-family: 'Quicksand', sans-serif; max-width: 500px; margin: 0 auto; padding: 20px;">
        <h2 style="margin-bottom: 4px;">Good morning, {first_name}</h2>
        <p style="color: #888; margin-top: 0;">Here's your day at a glance.</p>
        <hr style="border: none; border-top: 2px solid #ddd; margin: 16px 0;">
        {body}
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #aaa; font-size: 12px;">Sent by {agent_name} — Your AI assistant</p>
    </div>
    """

    return {
        'subject': f"Your morning briefing — {today.strftime('%A, %b %d')}",
        'html_body': html,
        'to_email': user.email,
    }


def generate_weekly_roundup(user):
    """
    Generate weekly roundup content for a user.
    Covers the past 7 days: completed tasks, expenses, upcoming week.
    """
    from app.extensions import db
    from app.models.schedule_event import ScheduleEvent
    from app.models.task import Task
    from app.models.expense import Expense

    today = date.today()
    week_ago = today - timedelta(days=7)
    week_ahead = today + timedelta(days=7)

    # Completed tasks this week
    completed = Task.query.filter(
        Task.user_id == user.id,
        Task.status == 'done',
        Task.completed_at >= week_ago.isoformat(),
    ).all()

    # Expenses this week
    expenses = Expense.query.filter(
        Expense.user_id == user.id,
        Expense.date >= week_ago,
        Expense.date <= today,
    ).all()
    total_expenses = sum(e.amount for e in expenses)

    # Upcoming events next 7 days
    upcoming = ScheduleEvent.query.filter(
        ScheduleEvent.user_id == user.id,
        ScheduleEvent.date >= today,
        ScheduleEvent.date <= week_ahead,
    ).order_by(ScheduleEvent.date.asc()).all()

    # Pending tasks
    pending_count = Task.query.filter(
        Task.user_id == user.id,
        Task.status != 'done',
    ).count()

    from config.settings import Config
    agent_name = Config.AGENT_NAME

    sections = []

    # Accomplishments
    if completed:
        items = "".join(f'<li>{t.title}</li>' for t in completed)
        sections.append(f'<h3>Completed This Week ({len(completed)})</h3><ul>{items}</ul>')
    else:
        sections.append('<h3>Completed This Week</h3><p style="color: #888;">Nothing marked as done. You\'ve got this week!</p>')

    # Expenses
    if expenses:
        items = "".join(f'<li>${e.amount:.2f} — {e.description} ({e.category})</li>' for e in expenses[:10])
        sections.append(f'<h3>Expenses: ${total_expenses:.2f}</h3><ul>{items}</ul>')

    # Upcoming
    if upcoming:
        up_lines = []
        for e in upcoming:
            date_str = e.date.strftime("%a %b %d")
            time_str = " at " + e.start_time.strftime("%I:%M %p") if e.start_time else ""
            up_lines.append(f'<li><strong>{date_str}</strong> — {e.title}{time_str}</li>')
        items = "".join(up_lines)
        sections.append(f'<h3>Coming Up This Week</h3><ul>{items}</ul>')
    else:
        sections.append('<h3>Coming Up</h3><p style="color: #888;">Clear week ahead. Time to book some work!</p>')

    # Pending
    if pending_count > 0:
        sections.append(f'<p><strong>{pending_count} tasks</strong> still pending.</p>')

    body = "\n".join(sections)
    first_name = (user.name or user.email).split(' ')[0] if hasattr(user, 'name') and user.name else user.email.split('@')[0]

    html = f"""
    <div style="font-family: 'Quicksand', sans-serif; max-width: 500px; margin: 0 auto; padding: 20px;">
        <h2 style="margin-bottom: 4px;">Your weekly roundup</h2>
        <p style="color: #888; margin-top: 0;">{first_name}, here's how last week went.</p>
        <hr style="border: none; border-top: 2px solid #ddd; margin: 16px 0;">
        {body}
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #aaa; font-size: 12px;">Sent by {agent_name} — Your AI assistant</p>
    </div>
    """

    return {
        'subject': f"Weekly roundup — {week_ago.strftime('%b %d')} to {today.strftime('%b %d')}",
        'html_body': html,
        'to_email': user.email,
    }


def send_email(to_email, subject, html_body):
    """
    Send an email via SendGrid.
    Returns True on success, False on failure.
    Falls back to logging if SendGrid isn't configured.
    """
    import os
    api_key = os.environ.get('SENDGRID_API_KEY')
    from_email = os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@agentrook.ai')

    if not api_key:
        logger.info(f"[OUTREACH] Would send email to {to_email}: {subject} (SendGrid not configured)")
        return False

    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail, Email, To, Content

        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        message = Mail(
            from_email=Email(from_email),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_body),
        )
        sg.client.mail.send.post(request_body=message.get())
        logger.info(f"[OUTREACH] Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"[OUTREACH] Email failed to {to_email}: {e}")
        return False


def run_morning_briefings():
    """
    Send morning briefings to all users. Called by scheduler.
    Only sends to users whose local time matches the configured briefing hour.
    """
    from app.models.user import User
    from config.settings import Config, AGENT_CONFIG
    import pytz
    from datetime import datetime

    outreach = AGENT_CONFIG.get('outreach', {})
    if not outreach.get('morning_briefing', False):
        return

    briefing_hour = outreach.get('briefing_hour', 7)
    users = User.query.filter_by(verified=True).all()

    for user in users:
        try:
            tz = pytz.timezone(user.timezone or 'US/Eastern')
            user_hour = datetime.now(tz).hour
            if user_hour != briefing_hour:
                continue

            briefing = generate_morning_briefing(user)
            if briefing:
                send_email(briefing['to_email'], briefing['subject'], briefing['html_body'])
        except Exception as e:
            logger.error(f"[OUTREACH] Briefing failed for user {user.id}: {e}")


def run_weekly_roundups():
    """
    Send weekly roundups to all users. Called by scheduler.
    Only sends on the configured roundup day.
    """
    from app.models.user import User
    from config.settings import AGENT_CONFIG

    outreach = AGENT_CONFIG.get('outreach', {})
    if not outreach.get('weekly_roundup', False):
        return

    roundup_day = outreach.get('roundup_day', 'monday').lower()
    today_day = date.today().strftime('%A').lower()

    if today_day != roundup_day:
        return

    users = User.query.filter_by(verified=True).all()

    for user in users:
        try:
            roundup = generate_weekly_roundup(user)
            if roundup:
                send_email(roundup['to_email'], roundup['subject'], roundup['html_body'])
        except Exception as e:
            logger.error(f"[OUTREACH] Roundup failed for user {user.id}: {e}")

"""Agent Rook — Dashboard overview API. Returns live data for the at-a-glance section."""
from datetime import date, timedelta
from sqlalchemy import func, extract
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.client import Client
from app.models.schedule_event import ScheduleEvent
from app.models.task import Task
from app.models.note import Note
from app.models.expense import Expense

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/overview', methods=['GET'])
@jwt_required()
def overview():
    """Rich overview data for the dashboard at-a-glance section."""
    user_id = int(get_jwt_identity())
    today = date.today()
    week_out = today + timedelta(days=7)
    month_start = today.replace(day=1)

    # Upcoming events — next 7 days
    upcoming_events = (
        ScheduleEvent.query
        .filter(ScheduleEvent.user_id == user_id, ScheduleEvent.date >= today, ScheduleEvent.date <= week_out)
        .order_by(ScheduleEvent.date.asc(), ScheduleEvent.start_time.asc())
        .limit(5)
        .all()
    )

    # Pending tasks — most urgent first (by due date, then priority)
    priority_order = db.case(
        (Task.priority == 'high', 0),
        (Task.priority == 'medium', 1),
        (Task.priority == 'low', 2),
        else_=3,
    )
    pending_tasks = (
        Task.query
        .filter(Task.user_id == user_id, Task.status != 'done')
        .order_by(Task.due_date.asc().nullslast(), priority_order)
        .limit(4)
        .all()
    )

    # Overdue tasks
    overdue_count = Task.query.filter(
        Task.user_id == user_id,
        Task.status != 'done',
        Task.due_date < today,
        Task.due_date.isnot(None),
    ).count()

    # Expenses this month
    expenses_month = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
        Expense.user_id == user_id,
        Expense.date >= month_start,
        Expense.date <= today,
    ).scalar()

    # Counts
    total_clients = Client.query.filter_by(user_id=user_id).count()
    total_upcoming = ScheduleEvent.query.filter(
        ScheduleEvent.user_id == user_id, ScheduleEvent.date >= today
    ).count()
    total_pending = Task.query.filter(Task.user_id == user_id, Task.status != 'done').count()
    total_notes = Note.query.filter_by(user_id=user_id).count()

    # Today's events specifically
    today_events = [e for e in upcoming_events if e.date == today]

    return jsonify(
        upcoming_events=[e.to_dict() for e in upcoming_events],
        today_events=[e.to_dict() for e in today_events],
        pending_tasks=[t.to_dict() for t in pending_tasks],
        overdue_count=overdue_count,
        expenses_month=round(float(expenses_month), 2),
        counts={
            'clients': total_clients,
            'upcoming': total_upcoming,
            'tasks_pending': total_pending,
            'notes': total_notes,
        },
    )

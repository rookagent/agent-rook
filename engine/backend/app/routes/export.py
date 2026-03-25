"""Agent Rook — Data export endpoint. Download all user data as JSON."""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.client import Client
from app.models.schedule_event import ScheduleEvent
from app.models.task import Task
from app.models.note import Note
from app.models.expense import Expense
from app.models.checklist import Checklist
from app.models.session_plan import SessionPlan

export_bp = Blueprint('export', __name__)


@export_bp.route('', methods=['GET'])
@jwt_required()
def export_all():
    """Export all user data as a single JSON object."""
    user_id = int(get_jwt_identity())

    data = {
        'clients': [c.to_dict() for c in Client.query.filter_by(user_id=user_id).all()],
        'schedule_events': [e.to_dict() for e in ScheduleEvent.query.filter_by(user_id=user_id).all()],
        'tasks': [t.to_dict() for t in Task.query.filter_by(user_id=user_id).all()],
        'notes': [n.to_dict() for n in Note.query.filter_by(user_id=user_id).all()],
        'expenses': [e.to_dict() for e in Expense.query.filter_by(user_id=user_id).all()],
        'checklists': [c.to_dict() for c in Checklist.query.filter_by(user_id=user_id).all()],
        'session_plans': [p.to_dict() for p in SessionPlan.query.filter_by(user_id=user_id).all()],
    }

    total = sum(len(v) for v in data.values())
    data['_meta'] = {'total_records': total, 'format': 'agent_rook_export_v1'}

    return jsonify(data)

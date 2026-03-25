"""Agent Rook — Schedule Events CRUD API."""
import json
from datetime import date, time, datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.schedule_event import ScheduleEvent

schedule_bp = Blueprint('schedule', __name__)


def _parse_date(s):
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _parse_time(s):
    if not s:
        return None
    try:
        return time.fromisoformat(s)
    except (ValueError, TypeError):
        return None


@schedule_bp.route('', methods=['GET'])
@jwt_required()
def list_events():
    user_id = int(get_jwt_identity())
    query = ScheduleEvent.query.filter_by(user_id=user_id)

    start = _parse_date(request.args.get('start'))
    end = _parse_date(request.args.get('end'))
    if start:
        query = query.filter(ScheduleEvent.date >= start)
    if end:
        query = query.filter(ScheduleEvent.date <= end)

    tag = request.args.get('tag', '').strip()
    if tag:
        query = query.filter(ScheduleEvent.tags.ilike(f'%"{tag}"%'))

    events = query.order_by(ScheduleEvent.date.asc(), ScheduleEvent.start_time.asc()).all()
    return jsonify(items=[e.to_dict() for e in events])


@schedule_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_event(id):
    user_id = int(get_jwt_identity())
    obj = ScheduleEvent.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404
    return jsonify(obj.to_dict())


@schedule_bp.route('', methods=['POST'])
@jwt_required()
def create_event():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get('title', '').strip():
        return jsonify(error="Title is required"), 400
    if not data.get('date'):
        return jsonify(error="Date is required"), 400

    d = _parse_date(data['date'])
    if not d:
        return jsonify(error="Invalid date format"), 400

    obj = ScheduleEvent(
        user_id=user_id,
        title=data['title'].strip(),
        description=data.get('description', '').strip() or None,
        date=d,
        start_time=_parse_time(data.get('start_time')),
        end_time=_parse_time(data.get('end_time')),
        all_day=data.get('all_day', False),
        tags=json.dumps(data['tags']) if data.get('tags') else None,
        color=data.get('color'),
    )
    db.session.add(obj)
    db.session.commit()
    return jsonify(obj.to_dict()), 201


@schedule_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_event(id):
    user_id = int(get_jwt_identity())
    obj = ScheduleEvent.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404

    data = request.get_json()
    if 'title' in data:
        obj.title = data['title'].strip()
    if 'description' in data:
        obj.description = data['description'].strip() or None
    if 'date' in data:
        obj.date = _parse_date(data['date']) or obj.date
    if 'start_time' in data:
        obj.start_time = _parse_time(data['start_time'])
    if 'end_time' in data:
        obj.end_time = _parse_time(data['end_time'])
    if 'all_day' in data:
        obj.all_day = data['all_day']
    if 'tags' in data:
        obj.tags = json.dumps(data['tags']) if data['tags'] else None
    if 'color' in data:
        obj.color = data['color']

    db.session.commit()
    return jsonify(obj.to_dict())


@schedule_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_event(id):
    user_id = int(get_jwt_identity())
    obj = ScheduleEvent.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404
    db.session.delete(obj)
    db.session.commit()
    return jsonify(message="Deleted"), 200

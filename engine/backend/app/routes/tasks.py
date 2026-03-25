"""Agent Rook — Tasks CRUD API."""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.task import Task

tasks_bp = Blueprint('tasks', __name__)


@tasks_bp.route('', methods=['GET'])
@jwt_required()
def list_tasks():
    user_id = int(get_jwt_identity())
    query = Task.query.filter_by(user_id=user_id)

    status = request.args.get('status')
    if status in ('pending', 'in_progress', 'done'):
        query = query.filter_by(status=status)

    priority = request.args.get('priority')
    if priority in ('low', 'medium', 'high'):
        query = query.filter_by(priority=priority)

    sort = request.args.get('sort', 'created_at')
    col = getattr(Task, sort, Task.created_at)
    query = query.order_by(col.desc())

    tasks = query.all()
    return jsonify(items=[t.to_dict() for t in tasks])


@tasks_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_task(id):
    user_id = int(get_jwt_identity())
    obj = Task.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404
    return jsonify(obj.to_dict())


@tasks_bp.route('', methods=['POST'])
@jwt_required()
def create_task():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get('title', '').strip():
        return jsonify(error="Title is required"), 400

    due = None
    if data.get('due_date'):
        try:
            from datetime import date
            due = date.fromisoformat(data['due_date'])
        except ValueError:
            pass

    obj = Task(
        user_id=user_id,
        title=data['title'].strip(),
        description=data.get('description', '').strip() or None,
        status=data.get('status', 'pending'),
        priority=data.get('priority', 'medium'),
        due_date=due,
    )
    db.session.add(obj)
    db.session.commit()
    return jsonify(obj.to_dict()), 201


@tasks_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_task(id):
    user_id = int(get_jwt_identity())
    obj = Task.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404

    data = request.get_json()
    if 'title' in data:
        obj.title = data['title'].strip()
    if 'description' in data:
        obj.description = data['description'].strip() or None
    if 'status' in data:
        obj.status = data['status']
        if data['status'] == 'done' and not obj.completed_at:
            obj.completed_at = datetime.utcnow()
        elif data['status'] != 'done':
            obj.completed_at = None
    if 'priority' in data:
        obj.priority = data['priority']
    if 'due_date' in data:
        try:
            from datetime import date
            obj.due_date = date.fromisoformat(data['due_date']) if data['due_date'] else None
        except ValueError:
            pass

    db.session.commit()
    return jsonify(obj.to_dict())


@tasks_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_task(id):
    user_id = int(get_jwt_identity())
    obj = Task.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404
    db.session.delete(obj)
    db.session.commit()
    return jsonify(message="Deleted"), 200

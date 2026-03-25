"""Agent Rook — Session Plans CRUD API."""
from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.session_plan import SessionPlan

session_plans_bp = Blueprint('session_plans', __name__)


@session_plans_bp.route('', methods=['GET'])
@jwt_required()
def list_plans():
    user_id = int(get_jwt_identity())
    plans = SessionPlan.query.filter_by(user_id=user_id).order_by(SessionPlan.updated_at.desc()).all()
    return jsonify(items=[p.to_dict() for p in plans])


@session_plans_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_plan(id):
    user_id = int(get_jwt_identity())
    obj = SessionPlan.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404
    return jsonify(obj.to_dict())


@session_plans_bp.route('', methods=['POST'])
@jwt_required()
def create_plan():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get('title', '').strip():
        return jsonify(error="Title is required"), 400

    d = None
    if data.get('date'):
        try:
            d = date.fromisoformat(data['date'])
        except ValueError:
            pass

    obj = SessionPlan(
        user_id=user_id,
        title=data['title'].strip(),
        session_type=data.get('session_type', '').strip() or None,
        date=d,
        location=data.get('location', '').strip() or None,
        client_name=data.get('client_name', '').strip() or None,
        notes=data.get('notes', '').strip() or None,
    )
    obj.set_blocks(data.get('blocks', []))
    db.session.add(obj)
    db.session.commit()
    return jsonify(obj.to_dict()), 201


@session_plans_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_plan(id):
    user_id = int(get_jwt_identity())
    obj = SessionPlan.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404

    data = request.get_json()
    if 'title' in data:
        obj.title = data['title'].strip()
    if 'session_type' in data:
        obj.session_type = data['session_type'].strip() or None
    if 'date' in data:
        try:
            obj.date = date.fromisoformat(data['date']) if data['date'] else None
        except ValueError:
            pass
    if 'location' in data:
        obj.location = data['location'].strip() or None
    if 'client_name' in data:
        obj.client_name = data['client_name'].strip() or None
    if 'blocks' in data:
        obj.set_blocks(data['blocks'])
    if 'notes' in data:
        obj.notes = data['notes'].strip() or None

    db.session.commit()
    return jsonify(obj.to_dict())


@session_plans_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_plan(id):
    user_id = int(get_jwt_identity())
    obj = SessionPlan.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404
    db.session.delete(obj)
    db.session.commit()
    return jsonify(message="Deleted"), 200

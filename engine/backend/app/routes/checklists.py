"""Agent Rook — Checklists CRUD API."""
import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.checklist import Checklist

checklists_bp = Blueprint('checklists', __name__)


@checklists_bp.route('', methods=['GET'])
@jwt_required()
def list_checklists():
    user_id = int(get_jwt_identity())
    items = Checklist.query.filter_by(user_id=user_id).order_by(Checklist.updated_at.desc()).all()
    return jsonify(items=[c.to_dict() for c in items])


@checklists_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_checklist(id):
    user_id = int(get_jwt_identity())
    obj = Checklist.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404
    return jsonify(obj.to_dict())


@checklists_bp.route('', methods=['POST'])
@jwt_required()
def create_checklist():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get('title', '').strip():
        return jsonify(error="Title is required"), 400

    obj = Checklist(
        user_id=user_id,
        title=data['title'].strip(),
        shoot_type=data.get('shoot_type', '').strip() or None,
        notes=data.get('notes', '').strip() or None,
    )
    obj.set_items(data.get('items', []))
    db.session.add(obj)
    db.session.commit()
    return jsonify(obj.to_dict()), 201


@checklists_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_checklist(id):
    user_id = int(get_jwt_identity())
    obj = Checklist.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404

    data = request.get_json()
    if 'title' in data:
        obj.title = data['title'].strip()
    if 'shoot_type' in data:
        obj.shoot_type = data['shoot_type'].strip() or None
    if 'items' in data:
        obj.set_items(data['items'])
    if 'notes' in data:
        obj.notes = data['notes'].strip() or None

    db.session.commit()
    return jsonify(obj.to_dict())


@checklists_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_checklist(id):
    user_id = int(get_jwt_identity())
    obj = Checklist.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404
    db.session.delete(obj)
    db.session.commit()
    return jsonify(message="Deleted"), 200

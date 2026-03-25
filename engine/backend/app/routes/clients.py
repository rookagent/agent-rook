"""Agent Rook — Clients CRUD API."""
import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.client import Client

clients_bp = Blueprint('clients', __name__)


def _get_or_404(id, user_id):
    obj = Client.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return None
    return obj


@clients_bp.route('', methods=['GET'])
@jwt_required()
def list_clients():
    user_id = int(get_jwt_identity())
    query = Client.query.filter_by(user_id=user_id)

    q = request.args.get('q', '').strip()
    if q:
        like = f'%{q}%'
        query = query.filter(db.or_(Client.name.ilike(like), Client.email.ilike(like)))

    tag = request.args.get('tag', '').strip()
    if tag:
        query = query.filter(Client.tags.ilike(f'%"{tag}"%'))

    sort = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')
    col = getattr(Client, sort, Client.created_at)
    query = query.order_by(col.desc() if order == 'desc' else col.asc())

    clients = query.all()
    return jsonify(items=[c.to_dict() for c in clients])


@clients_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_client(id):
    user_id = int(get_jwt_identity())
    obj = _get_or_404(id, user_id)
    if not obj:
        return jsonify(error="Not found"), 404
    return jsonify(obj.to_dict())


@clients_bp.route('', methods=['POST'])
@jwt_required()
def create_client():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get('name', '').strip():
        return jsonify(error="Name is required"), 400

    obj = Client(
        user_id=user_id,
        name=data['name'].strip(),
        email=data.get('email', '').strip() or None,
        phone=data.get('phone', '').strip() or None,
        notes=data.get('notes', '').strip() or None,
        tags=json.dumps(data['tags']) if data.get('tags') else None,
    )
    db.session.add(obj)
    db.session.commit()
    return jsonify(obj.to_dict()), 201


@clients_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_client(id):
    user_id = int(get_jwt_identity())
    obj = _get_or_404(id, user_id)
    if not obj:
        return jsonify(error="Not found"), 404

    data = request.get_json()
    if 'name' in data:
        obj.name = data['name'].strip()
    if 'email' in data:
        obj.email = data['email'].strip() or None
    if 'phone' in data:
        obj.phone = data['phone'].strip() or None
    if 'notes' in data:
        obj.notes = data['notes'].strip() or None
    if 'tags' in data:
        obj.tags = json.dumps(data['tags']) if data['tags'] else None

    db.session.commit()
    return jsonify(obj.to_dict())


@clients_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_client(id):
    user_id = int(get_jwt_identity())
    obj = _get_or_404(id, user_id)
    if not obj:
        return jsonify(error="Not found"), 404
    db.session.delete(obj)
    db.session.commit()
    return jsonify(message="Deleted"), 200

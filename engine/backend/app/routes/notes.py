"""Agent Rook — Notes CRUD API."""
import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.note import Note

notes_bp = Blueprint('notes', __name__)


@notes_bp.route('', methods=['GET'])
@jwt_required()
def list_notes():
    user_id = int(get_jwt_identity())
    query = Note.query.filter_by(user_id=user_id)

    q = request.args.get('q', '').strip()
    if q:
        like = f'%{q}%'
        query = query.filter(db.or_(Note.title.ilike(like), Note.content.ilike(like)))

    tag = request.args.get('tag', '').strip()
    if tag:
        query = query.filter(Note.tags.ilike(f'%"{tag}"%'))

    pinned = request.args.get('pinned')
    if pinned == 'true':
        query = query.filter_by(is_pinned=True)

    notes = query.order_by(Note.is_pinned.desc(), Note.updated_at.desc()).all()
    return jsonify(items=[n.to_dict() for n in notes])


@notes_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_note(id):
    user_id = int(get_jwt_identity())
    obj = Note.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404
    return jsonify(obj.to_dict())


@notes_bp.route('', methods=['POST'])
@jwt_required()
def create_note():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get('title', '').strip():
        return jsonify(error="Title is required"), 400

    obj = Note(
        user_id=user_id,
        title=data['title'].strip(),
        content=data.get('content', '').strip() or None,
        tags=json.dumps(data['tags']) if data.get('tags') else None,
        is_pinned=data.get('is_pinned', False),
    )
    db.session.add(obj)
    db.session.commit()
    return jsonify(obj.to_dict()), 201


@notes_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_note(id):
    user_id = int(get_jwt_identity())
    obj = Note.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404

    data = request.get_json()
    if 'title' in data:
        obj.title = data['title'].strip()
    if 'content' in data:
        obj.content = data['content'].strip() or None
    if 'tags' in data:
        obj.tags = json.dumps(data['tags']) if data['tags'] else None
    if 'is_pinned' in data:
        obj.is_pinned = data['is_pinned']

    db.session.commit()
    return jsonify(obj.to_dict())


@notes_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_note(id):
    user_id = int(get_jwt_identity())
    obj = Note.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404
    db.session.delete(obj)
    db.session.commit()
    return jsonify(message="Deleted"), 200

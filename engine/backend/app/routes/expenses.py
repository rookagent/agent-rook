"""Agent Rook — Expenses CRUD API."""
import json
from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.expense import Expense

expenses_bp = Blueprint('expenses', __name__)


@expenses_bp.route('', methods=['GET'])
@jwt_required()
def list_expenses():
    user_id = int(get_jwt_identity())
    query = Expense.query.filter_by(user_id=user_id)

    start = request.args.get('start')
    end = request.args.get('end')
    if start:
        try:
            query = query.filter(Expense.date >= date.fromisoformat(start))
        except ValueError:
            pass
    if end:
        try:
            query = query.filter(Expense.date <= date.fromisoformat(end))
        except ValueError:
            pass

    category = request.args.get('category')
    if category:
        query = query.filter_by(category=category)

    q = request.args.get('q', '').strip()
    if q:
        like = f'%{q}%'
        query = query.filter(db.or_(Expense.description.ilike(like), Expense.vendor.ilike(like)))

    expenses = query.order_by(Expense.date.desc()).all()

    total = sum(e.amount for e in expenses)
    return jsonify(items=[e.to_dict() for e in expenses], total=round(total, 2))


@expenses_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_expense(id):
    user_id = int(get_jwt_identity())
    obj = Expense.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404
    return jsonify(obj.to_dict())


@expenses_bp.route('', methods=['POST'])
@jwt_required()
def create_expense():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get('description', '').strip():
        return jsonify(error="Description is required"), 400
    if not data.get('amount'):
        return jsonify(error="Amount is required"), 400

    d = None
    if data.get('date'):
        try:
            d = date.fromisoformat(data['date'])
        except ValueError:
            return jsonify(error="Invalid date"), 400
    else:
        d = date.today()

    obj = Expense(
        user_id=user_id,
        description=data['description'].strip(),
        amount=float(data['amount']),
        category=data.get('category', 'other'),
        date=d,
        vendor=data.get('vendor', '').strip() or None,
        notes=data.get('notes', '').strip() or None,
        tags=json.dumps(data['tags']) if data.get('tags') else None,
        is_deductible=data.get('is_deductible', True),
    )
    db.session.add(obj)
    db.session.commit()
    return jsonify(obj.to_dict()), 201


@expenses_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_expense(id):
    user_id = int(get_jwt_identity())
    obj = Expense.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404

    data = request.get_json()
    if 'description' in data:
        obj.description = data['description'].strip()
    if 'amount' in data:
        obj.amount = float(data['amount'])
    if 'category' in data:
        obj.category = data['category']
    if 'date' in data:
        try:
            obj.date = date.fromisoformat(data['date'])
        except ValueError:
            pass
    if 'vendor' in data:
        obj.vendor = data['vendor'].strip() or None
    if 'notes' in data:
        obj.notes = data['notes'].strip() or None
    if 'tags' in data:
        obj.tags = json.dumps(data['tags']) if data['tags'] else None
    if 'is_deductible' in data:
        obj.is_deductible = data['is_deductible']

    db.session.commit()
    return jsonify(obj.to_dict())


@expenses_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_expense(id):
    user_id = int(get_jwt_identity())
    obj = Expense.query.filter_by(id=id, user_id=user_id).first()
    if not obj:
        return jsonify(error="Not found"), 404
    db.session.delete(obj)
    db.session.commit()
    return jsonify(message="Deleted"), 200

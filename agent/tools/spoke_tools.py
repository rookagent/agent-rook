"""
Spoke Tools — CRUD operations for all spoke models.
Called by the chat engine's tool dispatch loop so the AI agent
can create, read, update, and delete spoke data on behalf of the user.

Each handler supports: create, list, update, delete.
"""
import json
import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)


def execute_spoke_tool(params, user=None):
    """
    Universal spoke tool executor.

    params:
        resource: "expenses" | "clients" | "tasks" | "schedule" | "notes" | "checklists" | "session_plans"
        action: "create" | "list" | "update" | "delete"
        data: dict of fields for create/update
        id: int for update/delete
        filters: dict for list queries
    """
    from app.extensions import db

    resource = params.get('resource', '').lower()
    action = params.get('action', '').lower()
    record_id = params.get('id')
    data = params.get('data', {})
    filters = params.get('filters', {})

    if not user:
        return "Error: No authenticated user."
    if not resource or not action:
        return "Error: Both 'resource' and 'action' are required."

    handler = RESOURCE_HANDLERS.get(resource)
    if not handler:
        return f"Error: Unknown resource '{resource}'. Available: {', '.join(RESOURCE_HANDLERS.keys())}"

    try:
        return handler(action, user.id, data, record_id, filters, db)
    except Exception as e:
        logger.error(f"Spoke tool error: {resource}/{action} — {e}")
        return f"Error: {str(e)}"


# ── Expenses ──

def _handle_expenses(action, user_id, data, record_id, filters, db):
    from app.models.expense import Expense

    if action == 'create':
        d = _parse_date(data.get('date')) or date.today()
        obj = Expense(
            user_id=user_id,
            description=data.get('description', '').strip(),
            amount=float(data.get('amount', 0)),
            category=data.get('category', 'other'),
            date=d,
            vendor=data.get('vendor', '').strip() or None,
            notes=data.get('notes', '').strip() or None,
            tags=_encode_tags(data.get('tags')),
            is_deductible=data.get('is_deductible', True),
        )
        db.session.add(obj)
        db.session.commit()
        return f"Done — logged ${obj.amount:.2f} expense: {obj.description} ({obj.category}) on {obj.date.isoformat()}. ID: {obj.id}. It's now on your Expenses page."

    elif action == 'list':
        query = Expense.query.filter_by(user_id=user_id)
        if filters.get('category'):
            query = query.filter_by(category=filters['category'])
        expenses = query.order_by(Expense.date.desc()).limit(filters.get('limit', 20)).all()
        if not expenses:
            return "No expenses found."
        total = sum(e.amount for e in expenses)
        lines = [f"- ${e.amount:.2f} | {e.description} | {e.category} | {e.date.isoformat()} (ID: {e.id})" for e in expenses]
        return f"{len(expenses)} expenses (${total:.2f} total):\n" + "\n".join(lines)

    elif action == 'update' and record_id:
        obj = Expense.query.filter_by(id=record_id, user_id=user_id).first()
        if not obj:
            return f"Expense #{record_id} not found."
        if 'description' in data: obj.description = data['description'].strip()
        if 'amount' in data: obj.amount = float(data['amount'])
        if 'category' in data: obj.category = data['category']
        if 'date' in data: obj.date = _parse_date(data['date']) or obj.date
        if 'vendor' in data: obj.vendor = data['vendor'].strip() or None
        if 'notes' in data: obj.notes = data['notes'].strip() or None
        db.session.commit()
        return f"Updated expense #{obj.id}: ${obj.amount:.2f} — {obj.description}"

    elif action == 'delete' and record_id:
        obj = Expense.query.filter_by(id=record_id, user_id=user_id).first()
        if not obj:
            return f"Expense #{record_id} not found."
        desc = f"${obj.amount:.2f} — {obj.description}"
        db.session.delete(obj)
        db.session.commit()
        return f"Deleted expense: {desc}"

    return f"Unsupported: {action} on expenses. Need an id? Use 'list' first to find record IDs."


# ── Clients/Shoots ──

def _handle_clients(action, user_id, data, record_id, filters, db):
    from app.models.client import Client

    if action == 'create':
        obj = Client(
            user_id=user_id,
            name=data.get('name', '').strip(),
            email=data.get('email', '').strip() or None,
            phone=data.get('phone', '').strip() or None,
            notes=data.get('notes', '').strip() or None,
            tags=_encode_tags(data.get('tags')),
        )
        db.session.add(obj)
        db.session.commit()
        return f"Done — added shoot: {obj.name}. ID: {obj.id}. It's now on your Shoots page."

    elif action == 'list':
        query = Client.query.filter_by(user_id=user_id)
        if filters.get('q'):
            query = query.filter(Client.name.ilike(f"%{filters['q']}%"))
        clients = query.order_by(Client.created_at.desc()).limit(filters.get('limit', 20)).all()
        if not clients:
            return "No shoots found."
        lines = []
        for c in clients:
            tags = _decode_tags(c.tags)
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            lines.append(f"- {c.name}{tag_str}{f' — {c.email}' if c.email else ''} (ID: {c.id})")
        return f"{len(clients)} shoots:\n" + "\n".join(lines)

    elif action == 'update' and record_id:
        obj = Client.query.filter_by(id=record_id, user_id=user_id).first()
        if not obj:
            return f"Shoot #{record_id} not found."
        if 'name' in data: obj.name = data['name'].strip()
        if 'email' in data: obj.email = data['email'].strip() or None
        if 'phone' in data: obj.phone = data['phone'].strip() or None
        if 'notes' in data: obj.notes = data['notes'].strip() or None
        if 'tags' in data: obj.tags = _encode_tags(data['tags'])
        db.session.commit()
        return f"Updated shoot #{obj.id}: {obj.name}"

    elif action == 'delete' and record_id:
        obj = Client.query.filter_by(id=record_id, user_id=user_id).first()
        if not obj:
            return f"Shoot #{record_id} not found."
        name = obj.name
        db.session.delete(obj)
        db.session.commit()
        return f"Deleted shoot: {name}"

    return f"Unsupported: {action} on clients. Need an id? Use 'list' first."


# ── Tasks ──

def _handle_tasks(action, user_id, data, record_id, filters, db):
    from app.models.task import Task

    if action == 'create':
        obj = Task(
            user_id=user_id,
            title=data.get('title', '').strip(),
            description=data.get('description', '').strip() or None,
            status=data.get('status', 'pending'),
            priority=data.get('priority', 'medium'),
            due_date=_parse_date(data.get('due_date')),
        )
        db.session.add(obj)
        db.session.commit()
        due_str = f", due {obj.due_date.isoformat()}" if obj.due_date else ""
        return f"Done — task added: \"{obj.title}\" ({obj.priority} priority{due_str}). ID: {obj.id}. It's on your Tasks page."

    elif action == 'list':
        query = Task.query.filter_by(user_id=user_id)
        status = filters.get('status')
        if status:
            query = query.filter_by(status=status)
        else:
            query = query.filter(Task.status != 'done')
        tasks = query.order_by(Task.due_date.asc().nullslast()).limit(filters.get('limit', 20)).all()
        if not tasks:
            return "No pending tasks." if not status else f"No tasks with status '{status}'."
        lines = [f"- {'[done]' if t.status == 'done' else '[  ]'} {t.title} ({t.priority}{f', due {t.due_date.isoformat()}' if t.due_date else ''}) (ID: {t.id})" for t in tasks]
        return f"{len(tasks)} tasks:\n" + "\n".join(lines)

    elif action == 'update' and record_id:
        obj = Task.query.filter_by(id=record_id, user_id=user_id).first()
        if not obj:
            return f"Task #{record_id} not found."
        if 'status' in data:
            obj.status = data['status']
            if data['status'] == 'done' and not obj.completed_at:
                obj.completed_at = datetime.utcnow()
            elif data['status'] != 'done':
                obj.completed_at = None
        if 'title' in data: obj.title = data['title'].strip()
        if 'description' in data: obj.description = data['description'].strip() or None
        if 'priority' in data: obj.priority = data['priority']
        if 'due_date' in data: obj.due_date = _parse_date(data['due_date'])
        db.session.commit()
        return f"Updated task #{obj.id}: \"{obj.title}\" — {obj.status}"

    elif action == 'delete' and record_id:
        obj = Task.query.filter_by(id=record_id, user_id=user_id).first()
        if not obj:
            return f"Task #{record_id} not found."
        title = obj.title
        db.session.delete(obj)
        db.session.commit()
        return f"Deleted task: \"{title}\""

    return f"Unsupported: {action} on tasks. Need an id? Use 'list' first."


# ── Schedule/Calendar ──

def _handle_schedule(action, user_id, data, record_id, filters, db):
    from app.models.schedule_event import ScheduleEvent
    from datetime import time as time_type

    if action == 'create':
        d = _parse_date(data.get('date'))
        if not d:
            return "Error: date is required for calendar events."
        obj = ScheduleEvent(
            user_id=user_id,
            title=data.get('title', '').strip(),
            description=data.get('description', '').strip() or None,
            date=d,
            start_time=_parse_time(data.get('start_time')),
            end_time=_parse_time(data.get('end_time')),
            tags=_encode_tags(data.get('tags')),
            color=data.get('color'),
        )
        db.session.add(obj)
        db.session.commit()
        time_str = f" at {obj.start_time.isoformat()}" if obj.start_time else ""
        return f"Done — added to calendar: \"{obj.title}\" on {d.isoformat()}{time_str}. ID: {obj.id}. Check your Calendar page."

    elif action == 'list':
        query = ScheduleEvent.query.filter_by(user_id=user_id)
        if filters.get('upcoming'):
            query = query.filter(ScheduleEvent.date >= date.today())
        events = query.order_by(ScheduleEvent.date.asc()).limit(filters.get('limit', 20)).all()
        if not events:
            return "No calendar events found."
        lines = [f"- {e.date.isoformat()} | {e.title}{f' at {e.start_time.isoformat()}' if e.start_time else ''} (ID: {e.id})" for e in events]
        return f"{len(events)} events:\n" + "\n".join(lines)

    elif action == 'update' and record_id:
        obj = ScheduleEvent.query.filter_by(id=record_id, user_id=user_id).first()
        if not obj:
            return f"Event #{record_id} not found."
        if 'title' in data: obj.title = data['title'].strip()
        if 'description' in data: obj.description = data['description'].strip() or None
        if 'date' in data: obj.date = _parse_date(data['date']) or obj.date
        if 'start_time' in data: obj.start_time = _parse_time(data['start_time'])
        if 'end_time' in data: obj.end_time = _parse_time(data['end_time'])
        db.session.commit()
        return f"Updated event #{obj.id}: \"{obj.title}\" on {obj.date.isoformat()}"

    elif action == 'delete' and record_id:
        obj = ScheduleEvent.query.filter_by(id=record_id, user_id=user_id).first()
        if not obj:
            return f"Event #{record_id} not found."
        title = obj.title
        db.session.delete(obj)
        db.session.commit()
        return f"Deleted event: \"{title}\""

    return f"Unsupported: {action} on schedule. Need an id? Use 'list' first."


# ── Notes ──

def _handle_notes(action, user_id, data, record_id, filters, db):
    from app.models.note import Note

    if action == 'create':
        obj = Note(
            user_id=user_id,
            title=data.get('title', '').strip(),
            content=data.get('content', '').strip() or None,
            tags=_encode_tags(data.get('tags')),
        )
        db.session.add(obj)
        db.session.commit()
        return f"Done — note saved: \"{obj.title}\". ID: {obj.id}. It's on your Notes page."

    elif action == 'list':
        query = Note.query.filter_by(user_id=user_id)
        if filters.get('q'):
            like = f"%{filters['q']}%"
            from app.extensions import db as _db
            query = query.filter(_db.or_(Note.title.ilike(like), Note.content.ilike(like)))
        notes = query.order_by(Note.updated_at.desc()).limit(filters.get('limit', 20)).all()
        if not notes:
            return "No notes found."
        lines = [f"- {n.title} (ID: {n.id})" for n in notes]
        return f"{len(notes)} notes:\n" + "\n".join(lines)

    elif action == 'update' and record_id:
        obj = Note.query.filter_by(id=record_id, user_id=user_id).first()
        if not obj:
            return f"Note #{record_id} not found."
        if 'title' in data: obj.title = data['title'].strip()
        if 'content' in data: obj.content = data['content'].strip() or None
        if 'tags' in data: obj.tags = _encode_tags(data['tags'])
        db.session.commit()
        return f"Updated note #{obj.id}: \"{obj.title}\""

    elif action == 'delete' and record_id:
        obj = Note.query.filter_by(id=record_id, user_id=user_id).first()
        if not obj:
            return f"Note #{record_id} not found."
        title = obj.title
        db.session.delete(obj)
        db.session.commit()
        return f"Deleted note: \"{title}\""

    return f"Unsupported: {action} on notes. Need an id? Use 'list' first."


# ── Checklists ──

def _handle_checklists(action, user_id, data, record_id, filters, db):
    from app.models.checklist import Checklist

    if action == 'create':
        obj = Checklist(
            user_id=user_id,
            title=data.get('title', '').strip(),
            shoot_type=data.get('shoot_type', '').strip() or None,
            notes=data.get('notes', '').strip() or None,
        )
        obj.set_items(_normalize_items(data.get('items', [])))
        db.session.add(obj)
        db.session.commit()
        return f"Done — checklist created: \"{obj.title}\" with {len(obj.get_items())} items. ID: {obj.id}. Open Gear Checklists to check items off as you pack."

    elif action == 'list':
        lists = Checklist.query.filter_by(user_id=user_id).order_by(Checklist.updated_at.desc()).limit(10).all()
        if not lists:
            return "No checklists found."
        lines = []
        for cl in lists:
            items = cl.get_items()
            checked = sum(1 for i in items if i.get('checked'))
            lines.append(f"- {cl.title} ({checked}/{len(items)} packed) (ID: {cl.id})")
        return f"{len(lists)} checklists:\n" + "\n".join(lines)

    elif action == 'update' and record_id:
        obj = Checklist.query.filter_by(id=record_id, user_id=user_id).first()
        if not obj:
            return f"Checklist #{record_id} not found."
        if 'title' in data: obj.title = data['title'].strip()
        if 'shoot_type' in data: obj.shoot_type = data['shoot_type'].strip() or None
        if 'notes' in data: obj.notes = data['notes'].strip() or None
        if 'items' in data:
            # Replace items entirely
            obj.set_items(_normalize_items(data['items']))
        if 'add_items' in data:
            # Append new items to existing list
            existing = obj.get_items()
            new_items = _normalize_items(data['add_items'])
            obj.set_items(existing + new_items)
        if 'remove_item' in data:
            # Remove by name
            existing = obj.get_items()
            name_to_remove = data['remove_item'].lower()
            obj.set_items([i for i in existing if i['name'].lower() != name_to_remove])
        db.session.commit()
        count = len(obj.get_items())
        return f"Updated checklist #{obj.id}: \"{obj.title}\" — now has {count} items."

    elif action == 'delete' and record_id:
        obj = Checklist.query.filter_by(id=record_id, user_id=user_id).first()
        if not obj:
            return f"Checklist #{record_id} not found."
        title = obj.title
        db.session.delete(obj)
        db.session.commit()
        return f"Deleted checklist: \"{title}\""

    return f"Unsupported: {action} on checklists. Need an id? Use 'list' first."


# ── Session Plans ──

def _handle_session_plans(action, user_id, data, record_id, filters, db):
    from app.models.session_plan import SessionPlan

    if action == 'create':
        obj = SessionPlan(
            user_id=user_id,
            title=data.get('title', '').strip(),
            session_type=data.get('session_type', '').strip() or None,
            date=_parse_date(data.get('date')),
            location=data.get('location', '').strip() or None,
            client_name=data.get('client_name', '').strip() or None,
            notes=data.get('notes', '').strip() or None,
        )
        obj.set_blocks(data.get('blocks', []))
        db.session.add(obj)
        db.session.commit()
        return f"Done — session plan created: \"{obj.title}\" with {len(obj.get_blocks())} time blocks. ID: {obj.id}. Edit it in Session Plans."

    elif action == 'list':
        plans = SessionPlan.query.filter_by(user_id=user_id).order_by(SessionPlan.updated_at.desc()).limit(10).all()
        if not plans:
            return "No session plans found."
        lines = [f"- {p.title}{f' ({p.session_type})' if p.session_type else ''}{f' — {p.date.isoformat()}' if p.date else ''} — {len(p.get_blocks())} blocks (ID: {p.id})" for p in plans]
        return f"{len(plans)} session plans:\n" + "\n".join(lines)

    elif action == 'update' and record_id:
        obj = SessionPlan.query.filter_by(id=record_id, user_id=user_id).first()
        if not obj:
            return f"Session plan #{record_id} not found."
        if 'title' in data: obj.title = data['title'].strip()
        if 'session_type' in data: obj.session_type = data['session_type'].strip() or None
        if 'date' in data: obj.date = _parse_date(data['date'])
        if 'location' in data: obj.location = data['location'].strip() or None
        if 'client_name' in data: obj.client_name = data['client_name'].strip() or None
        if 'notes' in data: obj.notes = data['notes'].strip() or None
        if 'blocks' in data: obj.set_blocks(data['blocks'])
        if 'add_blocks' in data:
            existing = obj.get_blocks()
            obj.set_blocks(existing + data['add_blocks'])
        db.session.commit()
        return f"Updated session plan #{obj.id}: \"{obj.title}\" — {len(obj.get_blocks())} blocks."

    elif action == 'delete' and record_id:
        obj = SessionPlan.query.filter_by(id=record_id, user_id=user_id).first()
        if not obj:
            return f"Session plan #{record_id} not found."
        title = obj.title
        db.session.delete(obj)
        db.session.commit()
        return f"Deleted session plan: \"{title}\""

    return f"Unsupported: {action} on session_plans. Need an id? Use 'list' first."


# ── Helpers ──

def _parse_date(s):
    if not s: return None
    try: return date.fromisoformat(s)
    except (ValueError, TypeError): return None

def _parse_time(s):
    if not s: return None
    from datetime import time as time_type
    try: return time_type.fromisoformat(s)
    except (ValueError, TypeError): return None

def _encode_tags(tags):
    if not tags: return None
    if isinstance(tags, list): return json.dumps(tags)
    return None

def _decode_tags(tags_json):
    if not tags_json: return []
    try: return json.loads(tags_json)
    except: return []

def _normalize_items(items):
    """Accept list of strings or list of {name, checked} dicts."""
    parsed = []
    for item in (items or []):
        if isinstance(item, str):
            parsed.append({'name': item.strip(), 'checked': False})
        elif isinstance(item, dict):
            parsed.append({'name': item.get('name', '').strip(), 'checked': item.get('checked', False)})
    return parsed


# ── Router ──

RESOURCE_HANDLERS = {
    'expenses': _handle_expenses,
    'clients': _handle_clients,
    'shoots': _handle_clients,
    'tasks': _handle_tasks,
    'schedule': _handle_schedule,
    'calendar': _handle_schedule,
    'notes': _handle_notes,
    'checklists': _handle_checklists,
    'session_plans': _handle_session_plans,
}

# Agent Rook ♟️

**Your Strategic AI Scaffold.** An open-source framework for building AI agents with tool use, persistent memory, and a credit system — powered by Claude.

Drop your knowledge into markdown files, define your tools, deploy. Your agent is ready.

## Quick Start

```bash
git clone https://github.com/agentrook/agentrook.git
cd agentrook
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY

cd engine/backend
pip install -r requirements.txt
flask db upgrade
flask run
```

Your agent is running at `http://localhost:5000/api/health`.

## How It Works

1. **Edit `agent.yaml`** — name your agent, write its personality, configure tools
2. **Add knowledge** — drop markdown files in `agent/knowledge/`
3. **Add tools** — write Python functions in `agent/tools/`
4. **Deploy** — push to Railway, Render, or any Docker host

## Project Structure

```
agentrook/
├── agent.yaml              ← Your agent's config (name, personality, tools)
├── agent/
│   ├── knowledge/          ← Drop markdown files here (auto-loaded)
│   ├── tools/              ← Custom tool executors (Python)
│   └── prompts/            ← Personality overrides
├── engine/                 ← Framework (don't edit)
│   ├── backend/            ← Flask + Claude API
│   └── frontend/           ← React chat UI (coming soon)
└── .env.example            ← Environment variables template
```

## What You Get

- **Tool dispatch loop** — Claude calls your tools, you execute them, results feed back automatically (up to 3 rounds)
- **Smart routing** — Simple messages use Haiku (cheap), complex ones use Sonnet (smart)
- **Persistent memory** — Your agent remembers preferences, facts, and goals across sessions
- **Credit system** — Free daily messages + pay-as-you-go credits via Stripe
- **Knowledge bases** — Drop markdown files in a folder, agent searches them automatically
- **Self-diagnosis** — When something goes wrong, the agent explains what happened

## Knowledge Files

Knowledge is just markdown with YAML frontmatter:

```markdown
---
name: cooking_techniques
keywords:
  - sauté
  - braise
  - roast
  - technique
description: "Cooking techniques and methods"
---

# Cooking Techniques

## Sautéing
High heat, small amount of fat, constant movement...
```

Drop it in `agent/knowledge/` — the router picks it up automatically.

## Custom Tools

Define tools in `agent.yaml`, implement in Python:

```yaml
# agent.yaml
tools:
  - name: "meal_planner"
    module: "agent.tools.meal_planner"
    function: "execute_meal_planner"
    description: "Plan weekly meals with nutritional balance"
    schema:
      type: object
      properties:
        action:
          type: string
          enum: [plan, suggest]
      required: [action]
```

```python
# agent/tools/meal_planner.py
def execute_meal_planner(params, user=None):
    action = params.get('action')
    if action == 'plan':
        return "Here's a balanced meal plan for the week..."
    return "Unknown action"
```

## Deploy to Railway

1. Push to GitHub
2. Connect repo to Railway
3. Set environment variables (see `.env.example`)
4. Deploy

## Built With

- **Backend:** Flask + SQLAlchemy + Alembic
- **AI:** Claude API (Anthropic) with tool_use
- **Memory:** Redis + PostgreSQL
- **Payments:** Stripe
- **Frontend:** React + MUI (coming in v2)

## License

MIT — use it for anything.

---

*Built by [Kelly Smith](https://findmidaycare.com) — a daycare owner who built an AI assistant for her business, then open-sourced the engine for everyone.*

*Disclaimer: Agent Rook is provided as-is. AI agents can forget, hallucinate, or miss context. You are responsible for verifying outputs and the security of your deployment.*

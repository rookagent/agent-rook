# Agent Rook

**Your Strategic AI Scaffold.** Open-source framework for building AI agents with tool use, persistent memory, knowledge bases, and a full app UI.

Drop your knowledge into markdown files. Define your personality. Deploy. Your agent is ready.

---

## What Makes It Different

Most AI agent frameworks give you a chatbot. Agent Rook gives you a **full application** — dashboard, spoke pages, CRUD tools, streaming chat, proactive outreach, and multi-model support. All configurable from one YAML file.

| Feature | Agent Rook | AnythingLLM | Dify | LangChain |
|---------|-----------|-------------|------|-----------|
| Full app UI (dashboard + pages) | Yes | No | Partial | No |
| Config-driven (one YAML) | Yes | No | Partial | No |
| Chat + keyboard CRUD | Yes | Chat only | Chat only | Chat only |
| Multi-model (Claude/GPT/Gemini) | Yes | Yes | Yes | Yes |
| Persistent memory | Yes | Partial | No | No |
| Knowledge base (markdown) | Yes | Yes | Yes | Requires code |
| Proactive outreach (email) | Yes | No | No | No |
| Credit/billing system | Yes | No | No | No |
| One-command agent swap | Yes | No | No | No |
| Open source (MIT) | Yes | Yes | Yes | Yes |

---

## Three Example Agents, One Framework

### Lens Cap — Freelance Photographer
Warm amber palette. Shoots tracker, calendar, gear checklists, session plans, expenses, notes. 13 knowledge files covering composition, lighting, posing, weddings, families, newborns, pets, seniors, headshots, business, and post-processing.

### Ledger — Small Business Bookkeeper
Navy/green palette. Expense tracker, client manager, task list, calendar. 11 deep knowledge files covering Schedule C line-by-line, tax deductions, quarterly estimated taxes, entity types, depreciation, 1099 rules, audit defense, payroll, sales tax, and year-end planning.

### Sparky — Personal Tutor
Blue/yellow palette. Assignments tracker, study notes, test dates. 6 knowledge files covering arithmetic, fractions/decimals, geometry, earth/space science, life science, and study skills. Patient, encouraging personality that adapts to the student's level.

**Switch agents in 10 seconds:**
```bash
cp -r examples/lens-cap/* agent/    # Photographer
cp -r examples/bookkeeper/* agent/  # Bookkeeper
cp -r examples/tutor/* agent/       # Personal tutor
python3 scripts/build_config.py     # Sync config to frontend
```

---

## Architecture

```
agent.yaml                    <- THE BRAIN: personality, branding, tools, knowledge
agent/
  knowledge/*.md              <- Markdown files with YAML frontmatter
  tools/*.py                  <- Custom Python tool executors
  prompts/personality.md      <- Optional personality override
engine/
  backend/                    <- Flask + SQLAlchemy + Claude/GPT/Gemini
    app/
      chat/                   <- Chat engine, streaming, prompts, routing, diagnostics
      knowledge/              <- Markdown loader + keyword router
      models/                 <- User, Memory, Client, Task, Expense, Note, etc.
      routes/                 <- REST API: auth, chat, CRUD for all models
      outreach/               <- Morning briefing + weekly roundup emails
      utils/ai_client.py      <- Multi-provider: Anthropic, OpenAI, Gemini
  frontend/                   <- React 18 + MUI v5
    src/
      pages/                  <- Dashboard, Chat, 7 spoke pages
      components/             <- ChatWidget, AgentLayout, shared spoke components
      services/               <- API client with SSE streaming
examples/
  lens-cap/                   <- Photographer agent
  bookkeeper/                 <- Bookkeeper agent
  tutor/                      <- Personal tutor agent
```

---

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/agentrook/agent-rook.git
cd agent-rook
cp .env.example engine/backend/.env
# Edit engine/backend/.env — add your ANTHROPIC_API_KEY
```

### 2. Choose your agent

```bash
cp -r examples/lens-cap/* agent/   # or bookkeeper, or tutor
python3 scripts/build_config.py
```

### 3. Start the backend

```bash
cd engine/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python3 -c "
from dotenv import load_dotenv; load_dotenv()
from app import create_app; from app.extensions import db
app = create_app()
with app.app_context(): db.create_all()
"
PYTHONPATH=. python3 run.py
```

### 4. Start the frontend

```bash
cd engine/frontend
npm install
npm start
```

Open http://localhost:3000 — sign up, log in, start using your agent.

---

## How It Works

### Knowledge = Markdown Files
Drop `.md` files in `agent/knowledge/`. Each file has YAML frontmatter with `name`, `keywords`, and `description`. The engine automatically routes user queries to the most relevant knowledge module.

```yaml
---
name: Lighting
keywords: [flash, natural light, golden hour, bounce, OCF]
description: Natural light, flash techniques, and studio setups.
---

# Lighting for Photographers
...your content here...
```

### Tools = Python Functions
Define tools in `agent.yaml` and implement them in `agent/tools/`. The chat engine dispatches tool calls from the AI model to your executor functions.

```yaml
tools:
  - name: "manage_data"
    description: "Create, list, update, or delete app data"
    module: "agent.tools.spoke_tools"
    function: "execute_spoke_tool"
    schema: { ... }
```

### Branding = Config
One `agent.yaml` controls everything: agent name, personality, colors, fonts, dashboard cards, spoke page labels, AI model, access limits.

### Multi-Model
Switch AI providers by changing one line:
```yaml
ai:
  provider: "anthropic"   # or "openai" or "gemini"
  smart_model: "claude-sonnet-4-20250514"
  fast_model: "claude-haiku-4-20250514"
```

### Proactive Outreach
Configure morning briefings and weekly roundups:
```yaml
outreach:
  morning_briefing: true
  weekly_roundup: true
  briefing_hour: 7
  roundup_day: "monday"
```

---

## Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/agentrook)

Or manually:
```bash
railway login
railway init
railway up
```

Set environment variables in Railway dashboard:
- `ANTHROPIC_API_KEY`
- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `DATABASE_URL` (Railway provides PostgreSQL)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask, SQLAlchemy, Alembic |
| AI | Claude (Anthropic), GPT (OpenAI), Gemini (Google) |
| Database | PostgreSQL (prod) / SQLite (dev) |
| Cache | Redis (optional) |
| Frontend | React 18, MUI v5, React Router |
| Payments | Stripe (credit packs) |
| Email | SendGrid (outreach) |
| Deploy | Railway, Docker |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The easiest way to contribute is adding a new example agent.

---

## License

MIT. Use it, modify it, ship it.

---

Built by [Kelly Smith](https://github.com/agentrook) (Curiosity's Child LLC) with Claude Code.

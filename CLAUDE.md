# Agent Rook — AI Agent Framework

## What This Is
Open-source framework for building AI agents with tool use, persistent memory, and a credit system. Extracted from Daisy (Kelly's daycare AI assistant). The engine is generic — users bring their own knowledge bases and tools.

**Owner:** Kelly Smith (Curiosity's Child LLC)
**Repo:** github.com/agentrook/agent-rook (was rookagent/agentrook, redirected)
**Domain:** agentrook.ai (purchased, not yet configured)
**Status:** Session 1 complete (backend engine). Sessions 2-4 remaining.

## Tech Stack
- **Backend:** Flask + SQLAlchemy + Alembic (Python 3.11)
- **AI:** Claude API (Anthropic) with tool_use — Haiku (fast) + Sonnet (smart)
- **Database:** PostgreSQL (prod) / SQLite (dev)
- **Cache:** Redis (rate limiting, memory cache, daily limits)
- **Payments:** Stripe (credit packs)
- **Frontend:** React + MUI (Session 2 — not built yet)
- **Deploy:** Railway (Dockerfile + Procfile)

## Project Structure
```
agentrook/
├── agent.yaml                  # Config — defines the agent
├── agent/                      # User's domain code
│   ├── knowledge/              # Markdown files with YAML frontmatter
│   ├── tools/                  # Custom Python tool executors
│   └── prompts/                # Personality overrides
├── engine/                     # Framework — generic, don't hardcode domain stuff here
│   ├── backend/
│   │   ├── app/
│   │   │   ├── chat/           # Chat engine, access control, prompts, routing
│   │   │   ├── knowledge/      # Markdown loader + keyword router
│   │   │   ├── models/         # User, AgentMemory, Subscription, PromoCode
│   │   │   ├── routes/         # auth.py, chat.py (stripe_webhook.py pending)
│   │   │   └── utils/          # ai_client.py (complete, stream, JSON + retry)
│   │   ├── config/settings.py  # Reads agent.yaml + env vars
│   │   └── run.py
│   └── frontend/               # Session 2 — React chat UI
└── .env.example
```

## Key Patterns
- **Config-driven:** agent.yaml defines everything (name, personality, tools, knowledge, branding)
- **Tool dispatch loop:** Max 3 rounds. Claude calls tools → engine executes → results fed back
- **Smart routing:** _is_simple_query() routes greetings to Haiku (cheap), complex to Sonnet
- **Knowledge = markdown:** YAML frontmatter (name, keywords, description) + content body
- **Memory:** AgentMemory model with fuzzy dedup (pg_trgm), Redis hot cache
- **Credits:** 3 free messages/day, then pay-as-you-go via Stripe
- **Self-diagnosis:** Agent reviews its own tool calls when user says "that wasn't right"

## Relationship to Daisy (daycarespot/)
Agent Rook was EXTRACTED from Daisy. The two codebases are independent:
- **Rook** = generic engine (open source, MIT license)
- **Daisy** = daycare-specific implementation (private, proprietary knowledge)
- Never copy Daisy's knowledge bases, system prompts, or tool executors into Rook
- Daisy's CACFP rules, ELOF domains, state regulations, curriculum frameworks = trade secrets

## Build Plan (4 Sessions)
- ✅ Session 1: Backend engine (models, chat engine, auth, knowledge, config)
- ⬜ Session 2: Frontend (ChatWidget, AgentLayout, auth pages, Stripe checkout)
- ⬜ Session 3: Chef Rook example agent + custom tool + polished README
- ⬜ Session 4: Railway deploy, Alembic migration, end-to-end test, push

## Important Notes
- Kelly is the sole developer (non-technical, builds with Claude Code)
- Example knowledge files (cooking) are demos, NOT proprietary content
- MIT license — anyone can use, modify, distribute
- agent.yaml is the "brain" — if it's not in the config, it shouldn't be hardcoded
- All dates/times use user timezone via pytz (never bare UTC)

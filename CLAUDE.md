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

### ✅ Session 1: Backend Engine (COMPLETE)
Models, chat engine, auth routes, knowledge system, config. All in `engine/backend/`.

### ⬜ Session 2: Frontend Chat UI
**Goal:** A working React frontend where users can sign up, chat, and buy credits.

**Source files to reference (READ from daycarespot, WRITE to agentrook):**
- `daycarespot/frontend/src/components/ChatWidget.js` (1589 lines) → `engine/frontend/src/components/ChatWidget.js`
  - Keep: streaming SSE, markdown rendering, Web Speech STT (free), message history, print button, expand/collapse
  - Remove: parent mode vs provider mode branching, provider card rendering, ElevenLabs TTS, Hey Daisy mode
  - Parameterize: welcome message, suggestion chips, agent name (all from agentConfig.json)
- `daycarespot/frontend/src/services/chatApi.js` (384 lines) → `engine/frontend/src/services/chatApi.js`
  - Nearly verbatim. Change token key from 'access_token' to configurable. Agent name in error messages.
  - Keep: SSE parser, retry logic, heartbeat handling, error classification
- `daycarespot/frontend/src/pages/DaisyLayout.js` (250 lines) → `engine/frontend/src/components/AgentLayout.js`
  - Keep: flex layout, nav bar, credit display, footer
  - Parameterize: brand name, logo, nav items, colors (all from agentConfig.json)
  - Remove: "View My Listing" link, teacher/shadow checks, Curiosity's Child LLC copyright
- `daycarespot/frontend/src/context/AuthContext.js` → `engine/frontend/src/context/AuthContext.js`
  - Simplify: just isLoggedIn, user, credits, updateCredits(), logout()
  - Remove: isProviderLoggedIn/isParentLoggedIn split, providerUser, staff token handling

**New files to create:**
- `engine/frontend/src/pages/ChatPage.js` — Full-page chat (ChatWidget centered, not floating widget)
- `engine/frontend/src/pages/LoginPage.js` — Email + password, agent-branded
- `engine/frontend/src/pages/SignupPage.js` — Email + password + name, agent-branded
- `engine/frontend/src/pages/UpgradePage.js` — Credit pack purchase, Stripe checkout redirect
- `engine/frontend/src/App.js` — Routes: /, /login, /signup, /upgrade, /chat
- `engine/frontend/src/theme.js` — MUI theme reading colors from agentConfig.json
- `engine/frontend/src/agentConfig.json` — Generated from agent.yaml at build time (or manual for now)
- `engine/frontend/package.json` — React 18 + MUI v5 + react-router-dom + axios + react-markdown

**Build-time config injection:**
- Script reads `agent.yaml`, writes `engine/frontend/src/agentConfig.json`
- Components import from agentConfig: name, welcome_message, suggestions, colors, fonts
- No REACT_APP_ env vars needed for branding

**Verify:** `cd engine/frontend && npm start` → app compiles → can sign up → can chat → messages stream

### ⬜ Session 3: Chef Rook Example + Polish
**Goal:** The example agent works end-to-end with a custom tool. README is polished with screenshots.

**Tasks:**
1. Create `agent/tools/meal_planner.py` — Example custom tool executor:
   - `execute_meal_planner(params, user=None)`
   - Actions: plan (generate weekly meal plan), suggest (suggest meals from ingredients), substitute (dietary substitutions)
   - Returns formatted text (not DB-backed — pure demo)
2. Update `agent.yaml` — Wire the meal_planner tool with full schema
3. Add `agent/tools/__init__.py`
4. Test the full tool flow: user asks "plan my meals" → Claude calls meal_planner → executor returns plan → Claude presents it
5. Polish README.md with:
   - Architecture diagram (text-based)
   - Screenshots of chat working
   - "How to add your own knowledge" tutorial section
   - "How to add your own tools" tutorial section
   - Comparison table: Agent Rook vs AnythingLLM vs Dify vs OpenClaw
   - Contributing guidelines (basic)
6. Add `.gitignore` (Python + Node standard ignores)

**Verify:** Clone fresh → `pip install` → `flask run` → sign up → "plan this week's meals" → tool executes → response with meal plan

### ⬜ Session 4: Deploy + Launch Prep
**Goal:** Someone can deploy Agent Rook to Railway in under 10 minutes.

**Tasks:**
1. Create `railway.json` — Pre-configured for backend service
2. Fix Dockerfile COPY paths for Railway's build context
3. Create initial Alembic migration: `flask db init` + `flask db migrate` (generic schema: users, agent_memories, subscriptions, promo_codes)
4. Test full deployment flow:
   - Fresh clone → set env vars → Railway deploy → health check passes
   - Sign up → chat → buy credits (Stripe test mode) → knowledge lookup → memory persists
5. Create `CONTRIBUTING.md` — How to contribute (fork, branch, PR)
6. Create GitHub issues for v2 features:
   - Hub-and-spoke dashboard
   - Sub-accounts / team members
   - OpenAI / Gemini provider support
   - Document upload + RAG
   - Celery async tasks
   - ElevenLabs voice
7. Set up GitHub repo metadata:
   - Description: "Your Strategic AI Scaffold — open-source AI agent framework"
   - Topics: ai, agent, framework, claude, llm, open-source, python, flask, react
   - Website: agentrook.ai
8. Optional: Record a 2-minute Loom/screen recording showing the full flow

**Verify:** Fresh `git clone` on a clean machine → Railway deploy → end-to-end works

## Launch Strategy (Post-Session 4)
1. Reddit: r/SideProject, r/selfhosted, r/ClaudeAI, r/SaaS, r/opensource
   - Title: "I built an AI assistant for my daycare. Then I open-sourced the engine."
   - Story-driven, not feature-driven. Kelly's journey is the hook.
2. Hacker News: "Show HN: Agent Rook — open-source AI agent framework for solo operators"
3. X/Twitter: Tag @AnthropicAI, share the story
4. Product Hunt: Schedule for a Tuesday/Wednesday launch
5. Dev.to / Hashnode: Technical blog post about the extraction process

## Important Notes
- Kelly is the sole developer (non-technical, builds with Claude Code)
- Example knowledge files (cooking) are demos, NOT proprietary content
- MIT license — anyone can use, modify, distribute
- agent.yaml is the "brain" — if it's not in the config, it shouldn't be hardcoded
- All dates/times use user timezone via pytz (never bare UTC)

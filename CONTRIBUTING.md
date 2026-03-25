# Contributing to Agent Rook

Thanks for your interest in Agent Rook! Here's how to contribute.

## Quick Start

```bash
git clone https://github.com/agentrook/agent-rook.git
cd agent-rook

# Backend
cd engine/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../../.env.example .env  # Fill in your API keys
PYTHONPATH=. python3 -c "from dotenv import load_dotenv; load_dotenv(); from app import create_app; app = create_app(); app.app_context().push(); from app.extensions import db; db.create_all()"
PYTHONPATH=. python3 run.py

# Frontend (new terminal)
cd engine/frontend
npm install
npm start
```

## How to Contribute

### Report Bugs
Open an issue with:
- What you expected
- What actually happened
- Steps to reproduce
- Your environment (OS, Python version, Node version)

### Suggest Features
Open an issue with the `enhancement` label. Describe the use case, not just the feature.

### Submit Code
1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Test: backend starts, frontend compiles, your feature works
5. Commit with a clear message
6. Push and open a PR

### Add a New Example Agent
This is the easiest way to contribute! Create a folder in `examples/`:
```
examples/your-agent/
├── agent.yaml           # Config: name, personality, branding, dashboard cards
├── knowledge/           # Markdown files with YAML frontmatter
│   ├── topic_one.md
│   └── topic_two.md
└── tools/               # Optional custom tool executors
    └── your_tool.py
```

See `examples/lens-cap/` or `examples/bookkeeper/` for reference.

## Code Style
- Python: Follow existing patterns. No strict linter enforced yet.
- React: Functional components, hooks, MUI v5.
- Keep it simple. No over-engineering.

## License
MIT. Your contributions will be under the same license.

# Mul-Agent Project Guide

> A multi-agent collaboration system

---

## Quick Start

### Start Agent Service

```bash
# Activate virtual environment
source .venv/bin/activate

# Start core brain
python -m mul_agent.main
```

### Development

```bash
# Install dependencies
pnpm install

# Start frontend dev server
cd ui && pnpm dev

# Run tests
pnpm test
pytest
```

---

## Project Structure

```
mul-agent/
├── mul_agent/              # Core Python backend
│   ├── api/                # FastAPI server
│   ├── brain/              # Agent brain system
│   ├── handlers/           # Route handlers
│   ├── tools/              # Built-in tools
│   └── commands/           # Command system
│
├── ui/                     # React + TypeScript UI
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   └── utils/
│   ├── tests/
│   └── package.json
│
├── docs/                   # Documentation (Mintlify)
├── tests/                  # Python tests
├── skills/                 # Custom skills
└── storage/                # Runtime data (gitignored)
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.13, FastAPI |
| **Frontend** | React 19, TypeScript, Vite |
| **Testing** | pytest, Vitest, Playwright |
| **Linting** | Ruff (Python), Oxlint (TS) |
| **Formatting** | Ruff (Python), Oxfmt (TS) |
| **Docs** | Mintlify |
| **CI/CD** | GitHub Actions |

---

## Development Guidelines

### Code Quality

**Python:**
```bash
ruff check mul_agent/
ruff format mul_agent/
pytest tests/
```

**TypeScript:**
```bash
pnpm lint
pnpm format:check
pnpm test:run
```

### Pre-commit Hooks

Install pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

Hooks will run on every commit:
- Trailing whitespace removal
- End-of-file fixer
- YAML check
- Secret detection
- Ruff linting (Python)
- Oxlint (TypeScript)
- Oxfmt check (TypeScript)

---

## Testing

### Python Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=mul_agent --cov-report=html

# Run specific test file
pytest tests/test_router.py -v
```

### Frontend Tests

```bash
# Run tests
cd ui && pnpm test

# Run once and exit
pnpm test:run

# Run with coverage
pnpm test:coverage

# E2E tests
pnpm test:e2e
```

---

## Documentation

### Setup

```bash
# Install Mintlify
npm install -g mintlify

# Start local docs server
npx mintlify dev
```

### Add New Documentation

1. Create `.mdx` file in `docs/` directory
2. Register in `mint.json` navigation

---

## Configuration Files

| File | Purpose |
|------|---------|
| `package.json` | Node.js project config |
| `pnpm-workspace.yaml` | pnpm workspace definition |
| `tsconfig.json` | TypeScript configuration |
| `oxlint.json` | Oxlint rules |
| `oxfmt.config.json` | Oxfmt settings |
| `ruff.toml` | Ruff (Python) config |
| `pyproject.toml` | Python project config |
| `vitest.config.ts` | Vitest test config |
| `.pre-commit-config.yaml` | Pre-commit hooks |
| `mint.json` | Mintlify docs config |

---

## Available Scripts

### Root Level

```bash
pnpm lint              # Run Oxlint
pnpm lint:fix          # Fix Oxlint issues
pnpm format:check      # Check formatting
pnpm format:write      # Format code
pnpm check             # Run lint + format check
pnpm typecheck         # TypeScript type check
pnpm clean             # Clean build artifacts
```

### Frontend

```bash
pnpm dev              # Start dev server
pnpm build            # Build for production
pnpm preview          # Preview production build
pnpm test             # Run tests
pnpm test:e2e         # Run E2E tests
```

### Backend (Python)

```bash
python -m mul_agent.main       # Start agent
pytest tests/                  # Run tests
ruff check mul_agent/          # Lint Python
ruff format mul_agent/         # Format Python
```

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

---

## Deployment

### Docker

```bash
docker build -t mul-agent .
docker run -p 8000:8000 mul-agent
```

### Production

1. Build frontend: `cd ui && pnpm build`
2. Install Python deps: `pip install -e .`
3. Set environment variables
4. Start: `python -m mul_agent.main`

---

## Contributing

1. Create a branch: `git checkout -b feature/xxx`
2. Make changes
3. Run quality checks: `./scripts/quality-check.sh`
4. Commit: `git commit -m "feat: description"`
5. Push: `git push origin feature/xxx`
6. Create Pull Request

---

## Related Resources

- [OpenClaw](https://github.com/openclaw/openclaw) - Reference architecture
- [Mintlify Docs](https://mintlify.com/docs)
- [Oxlint](https://oxc.rs/docs/guide/usage/linter.html)
- [Ruff](https://docs.astral.sh/ruff/)
- [Vitest](https://vitest.dev/)

# Mul-Agent

> A multi-agent collaboration system powered by AI

[![CI](https://github.com/your-org/mul-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/mul-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🤖 **Multi-Agent Collaboration** - Multiple agents working together with specialized roles
- 🧠 **Intelligent Routing** - Automatic task routing to appropriate agents
- 🛠️ **Extensible Tools** - Rich built-in tool system
- 📝 **Memory Management** - Persistent state and memory
- 💻 **Web UI** - React-based frontend for agent interaction

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 22+
- pnpm

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/mul-agent.git
cd mul-agent

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
pnpm install
```

### Usage

```bash
# Start the agent service
python -m mul_agent.main

# Start the frontend (in another terminal)
cd frontend && pnpm dev
```

## Documentation

Visit our [documentation](https://docs.your-org.com/mul-agent) for detailed guides.

- [Getting Started](docs/getting-started.mdx)
- [Installation Guide](docs/installation.mdx)
- [Agent Concepts](docs/concepts/agent.mdx)

## Development

### Code Quality

```bash
# Run all checks
./scripts/quality-check.sh

# Individual checks
pnpm lint              # TypeScript lint
pnpm format:check      # TypeScript format
ruff check mul_agent/  # Python lint
```

### Testing

```bash
# Python tests
pytest tests/

# Frontend tests
pnpm test

# E2E tests
pnpm test:e2e
```

## Project Structure

```
mul-agent/
├── mul_agent/          # Python backend
├── frontend/           # React frontend
├── docs/               # Documentation
├── tests/              # Tests
├── scripts/            # Utility scripts
└── storage/            # Runtime data
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.13, FastAPI |
| Frontend | React 19, TypeScript, Vite |
| Testing | pytest, Vitest, Playwright |
| Linting | Ruff, Oxlint, Oxfmt |
| Docs | Mintlify |

## License

MIT © [your-org](https://github.com/your-org)

## Acknowledgments

- Inspired by [OpenClaw](https://github.com/openclaw/openclaw) project

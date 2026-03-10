# Mul-Agent

> A multi-agent collaboration system powered by AI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🤖 **Multi-Agent Collaboration** - Multiple agents working together with specialized roles
- 🧠 **Intelligent Routing** - Automatic task routing to appropriate agents
- 🛠️ **Extensible Tools** - Rich built-in tool system based on OpenClaw architecture
- 📝 **Memory Management** - Persistent state and memory with embedding support
- 💻 **Web UI** - React-based frontend for agent interaction
- 📚 **Skill System** - 50+ pre-built skills for common tasks

## Quick Start

### Prerequisites

- Node.js 22+
- pnpm
- Python 3.10+ (optional, for memory embeddings)

### Installation

```bash
# Clone the repository
git clone https://github.com/mul-agent/mul-agent.git
cd mul-agent

# Install Node.js dependencies
pnpm install

# (Optional) Install Python dependencies for memory features
pip install -e .
```

### Usage

```bash
# Start the development server
pnpm dev

# The agent will be available at http://localhost:5173
```

## Documentation

Visit our [documentation](docs/) for detailed guides.

- [快速开始](docs/快速开始.md)
- [架构说明](docs/ARCHITECTURE.md)
- [技能系统](docs/skills/)

## Development

### Code Quality

```bash
# Run all checks
pnpm check

# Individual checks
pnpm lint              # TypeScript lint
pnpm format:check      # TypeScript format check
pnpm format:write      # Format code
pnpm typecheck         # TypeScript type check
```

### Testing

```bash
# Frontend tests
pnpm test

# E2E tests
pnpm test:e2e
```

## Project Structure

```
mul-agent/
├── src/                # Main TypeScript codebase (OpenClaw-based)
│   ├── agents/         # Agent system
│   ├── memory/         # Memory and embeddings
│   ├── skills/         # Skill definitions
│   ├── tools/          # Tool implementations
│   └── ...
├── skills/             # Skill definitions (52 skills)
├── ui/                 # React frontend
├── docs/               # Documentation
├── tests/              # Tests
├── scripts/            # Utility scripts
└── storage/            # Runtime data
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Core** | TypeScript, Node.js |
| **Frontend** | React 19, TypeScript, Vite |
| **Memory** | Python embeddings, SQLite-vec |
| **Testing** | Vitest, Playwright, pytest |
| **Linting** | Oxlint, Oxfmt, Ruff |
| **Docs** | Mintlify |

## Skills System

The project includes 52+ pre-built skills:

- **Development**: github, git, coding-agent
- **Communication**: discord, slack, telegram, whatsapp
- **Productivity**: notion, obsidian, trello, things-mac
- **Media**: openai-image-gen, openai-whisper, video-frames
- **System**: tmux, 1password, bear-notes, apple-reminders

See [skills/](skills/) for the full list.

## License

MIT © mul-agent team

## Acknowledgments

- Based on [OpenClaw](https://github.com/openclaw/openclaw) architecture
- Inspired by Claude Code and Pi coding agent

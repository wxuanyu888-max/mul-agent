"""
mul-agent - Multi-Agent Collaboration System

Project Structure (inspired by OpenClaw):

```
mul_agent/
├── src/                      # Core source code
│   ├── cli/                  # CLI entry point
│   ├── commands/             # Command system
│   ├── agents/               # Agent system
│   ├── hooks/                # Hook system
│   ├── memory/               # Memory system
│   ├── plugins/              # Plugin system
│   ├── plugin_sdk/           # Plugin SDK
│   ├── tools/                # Tool system
│   ├── channels/             # Channel system
│   ├── skills/               # Skill system
│   ├── config/               # Configuration system
│   ├── logging/              # Logging system
│   ├── shared/               # Shared utilities
│   ├── types/                # Type definitions
│   ├── routing/              # Routing system
│   ├── sessions/             # Session management
│   ├── gateway/              # Gateway (optional)
│   ├── infra/                # Infrastructure
│   └── context_engine/       # Context engine
│
├── extensions/               # Standalone extensions
├── skills/                   # Standalone skills
├── packages/                 # Internal packages
└── tests/                    # Tests (colocated with source)
```

Key Design Principles:
1. **Modularity**: High cohesion, low coupling
2. **Extensibility**: Plugin-based architecture
3. **Testability**: Tests colocated with source
4. **Type Safety**: Comprehensive type hints
5. **Documentation**: Docs in docs/ directory
"""

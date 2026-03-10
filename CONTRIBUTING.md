# Contributing to mul-agent

Thank you for your interest in contributing to mul-agent! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Coding Standards](#coding-standards)
- [Testing](#testing)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/mul-agent.git`
3. Add the upstream remote: `git remote add upstream https://github.com/original-org/mul-agent.git`
4. Create a branch: `git checkout -b feature/your-feature-name`

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 22+ (for frontend development)
- pnpm (for frontend dependencies)

### Install Dependencies

```bash
# Python dependencies
pip install -e ".[dev]"

# Frontend dependencies
cd ui
pnpm install
```

### Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

## Making Changes

1. Make your changes in a feature branch
2. Follow the coding standards
3. Write or update tests as needed
4. Run the test suite
5. Check for linting issues

## Pull Request Guidelines

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests have been added or updated
- [ ] Documentation has been updated (if needed)
- [ ] No linting errors
- [ ] All tests pass

### PR Title Format

Use conventional commits format:

```
feat: add new feature
fix: resolve bug with router
docs: update installation guide
refactor: improve error handling
test: add tests for agent
chore: update dependencies
```

### PR Description

Include:
- Summary of changes
- Related issues (link with `Fixes #123`)
- Testing done
- Any breaking changes

## Coding Standards

### Python

- Follow PEP 8
- Use type hints
- Write docstrings for public APIs
- Keep functions focused (< 50 lines ideal)

```bash
# Lint Python code
ruff check mul_agent/

# Format Python code
ruff format mul_agent/
```

### TypeScript

- Use strict mode
- Avoid `any` type
- Write interfaces for data structures
- Keep components focused

```bash
# Lint TypeScript code
pnpm lint

# Format TypeScript code
pnpm format:write
```

## Testing

### Running Tests

```bash
# Python tests
pytest tests/

# With coverage
pytest tests/ --cov=mul_agent

# Frontend tests
cd ui && pnpm test

# E2E tests
pnpm test:e2e
```

### Writing Tests

- Aim for 80%+ code coverage
- Test edge cases
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)

## Documentation

- Update README.md for user-facing changes
- Add inline comments for complex logic
- Update API documentation for endpoint changes
- Include examples where helpful

## Questions?

Feel free to open an issue with the `question` label if you have any questions about contributing.

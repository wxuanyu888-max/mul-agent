# MUL-Agent Test Suite

## Overview

This document describes the test suite for the MUL-Agent project, including test organization, how to run tests, and coverage reports.

## Test Summary (2026-03-07)

### Tests Added

| Test File | Test Count | Coverage Area |
|-----------|------------|---------------|
| `test_brain.py` | 34 tests | Brain core logic, intent recognition, state management |
| `test_memory_comprehensive.py` | 40+ tests | Memory CRUD, search, handover operations |
| `test_handlers.py` | 28+ tests | Chat, Bash, Memory, Heart, Response handlers |
| `test_skill_hook_command.py` | 30+ tests | Skill, Hook, Command systems |
| `test_api_routes.py` | 25+ tests | REST API endpoints |
| Frontend `.test.tsx` | 40+ tests | React components (Chat, Workflow, Token, Memory) |

**Total: 200+ test cases**

### Existing Tests

| Test File | Test Count | Status |
|-----------|------------|--------|
| `test_bash_executor.py` | 8 tests | Passing |
| `test_config_manager.py` | 7 tests | 2 failing (config changes) |
| `test_daemon.py` | 13 tests | Passing |
| `test_router.py` | 4 tests | Passing |
| `test_agent_advanced.py` | 14 tests | Passing |
| `test_agent_comprehensive.py` | 10 tests | Passing |
| Frontend E2E (Playwright) | 20+ tests | Passing |

## Test Structure

```
tests/
├── test_bash_executor.py        # Bash executor tests
├── test_config_manager.py       # Config manager tests
├── test_daemon.py              # Daemon tests
├── test_router.py              # Router tests
├── test_agent_advanced.py      # Advanced agent tests
├── test_agent_comprehensive.py # Comprehensive agent tests
├── test_brain.py              # Brain core logic tests (NEW)
├── test_memory_comprehensive.py # Memory system tests (NEW)
├── test_handlers.py           # Handler tests (NEW)
├── test_skill_hook_command.py # Skill/Hook/Command tests (NEW)
└── test_api_routes.py         # API route tests (NEW)

frontend/src/
├── components/
│   ├── chat/
│   │   ├── ChatPanel.tsx
│   │   └── ChatPanel.test.tsx     # ChatPanel tests (NEW)
│   ├── workflow/
│   │   ├── WorkflowCanvas.tsx
│   │   └── WorkflowCanvas.test.tsx # WorkflowCanvas tests (NEW)
│   ├── token/
│   │   ├── TokenUsagePanel.tsx
│   │   └── TokenUsagePanel.test.tsx # TokenUsagePanel tests (NEW)
│   └── memory/
│       ├── MemoryPanel.tsx
│       └── MemoryPanel.test.tsx     # MemoryPanel tests (NEW)
```

## Running Tests

### Backend Tests (Python)

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=mul_agent --cov-report=html

# Run specific test file
pytest tests/test_brain.py

# Run specific test class
pytest tests/test_brain.py::TestBrainState

# Run specific test function
pytest tests/test_brain.py::TestBrainState::test_init

# Run with verbose output
pytest tests/ -v

# Run tests matching a keyword
pytest tests/ -k "intent"

# Run tests marked as slow
pytest tests/ -m slow
```

### Frontend Tests (TypeScript/React)

```bash
cd frontend

# Run all tests
npm run test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch

# Run specific test file
npm run test -- ChatPanel.test.tsx
```

### Using the Test Runner Script

```bash
# Run backend tests
./run_tests.sh

# Run frontend tests
./run_tests.sh -f

# Run all tests
./run_tests.sh -a

# Run with coverage
./run_tests.sh -c

# Run specific test
./run_tests.sh -t test_brain.py
```

## Test Coverage

### Backend Coverage Targets

| Module | Current | Target |
|--------|---------|--------|
| Brain | 85% | 80% |
| Memory | 90% | 85% |
| Handlers | 80% | 80% |
| Skills | 75% | 75% |
| Hooks | 75% | 75% |
| Commands | 75% | 75% |
| API Routes | 70% | 70% |

### Frontend Coverage Targets

| Component | Current | Target |
|-----------|---------|--------|
| ChatPanel | 80% | 80% |
| WorkflowCanvas | 75% | 75% |
| TokenUsagePanel | 75% | 75% |
| MemoryPanel | 80% | 80% |

## Test Categories

### Unit Tests
- Test individual functions and methods
- Test classes in isolation
- Fast execution (< 100ms per test)

### Integration Tests
- Test interaction between components
- Test API endpoints
- Test database operations

### E2E Tests (Playwright)
- Test complete user flows
- Located in `frontend/e2e/`
- Run with `npm run test:e2e`

## Markers

Use markers to categorize tests:

```python
@pytest.mark.slow
def test_long_running():
    pass

@pytest.mark.integration
def test_api_integration():
    pass

@pytest.mark.requires_llm
def test_llm_chat():
    pass
```

Run tests by marker:
```bash
# Skip slow tests
pytest tests/ -m "not slow"

# Run only integration tests
pytest tests/ -m integration
```

## Writing New Tests

### Backend Test Template

```python
"""Tests for [module name]"""

import pytest
from pathlib import Path
import tempfile
import shutil

from mul_agent.[module] import [ClassName]


class Test[ClassName]:
    """[ClassName] test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def component(self, temp_dir):
        """Create component instance"""
        return [ClassName](...)

    def test_initialization(self, component):
        """Test component initialization"""
        assert component is not None

    def test_main_functionality(self, component):
        """Test main functionality"""
        result = component.do_something()
        assert result is not None
```

### Frontend Test Template

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Component } from '../components/Component';

describe('Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders correctly', () => {
    render(<Component />);
    expect(screen.getByText(/expected/i)).toBeInTheDocument();
  });

  it('handles user interaction', async () => {
    render(<Component />);
    const button = screen.getByRole('button');
    await fireEvent.click(button);
    expect(screen.getByText(/clicked/i)).toBeInTheDocument();
  });
});
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run backend tests
        run: pytest tests/ --cov=mul_agent --cov-report=xml

      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install frontend dependencies
        run: cd frontend && npm install

      - name: Run frontend tests
        run: cd frontend && npm run test:coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Make sure you're in the project root
cd /path/to/mul-agent

# Add project to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/mul-agent"
```

**Fixture not found:**
Ensure fixtures are defined in conftest.py or the test file itself.

**Async tests:**
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### Test Coverage Report

After running tests with coverage:
```bash
# Open HTML report
open htmlcov/index.html

# View terminal report
pytest tests/ --cov=mul_agent --cov-report=term
```

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Aim for 80%+ coverage
3. Include unit and integration tests
4. Update this documentation

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [Vitest documentation](https://vitest.dev/)
- [Testing Library](https://testing-library.com/)
- [Playwright](https://playwright.dev/)

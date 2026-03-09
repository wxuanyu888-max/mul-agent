# Skills

This directory contains skill definitions for mul-agent.

## Skill Structure

Each skill is a directory containing:
- `SKILL.md` - Skill definition with frontmatter metadata
- `references/` - (optional) Reference materials
- `scripts/` - (optional) Helper scripts

## Available Skills

- `bash/` - Shell command execution
- `read/` - File reading
- `write/` - File writing
- `edit/` - File editing
- `glob/` - File pattern matching
- `grep/` - Text search
- `git/` - Git operations
- `memory/` - Memory management
- `search/` - Code search
- `web_fetch/` - Web content fetching
- `web_git/` - Git web operations

## SKILL.md Format

```markdown
---
name: skill-name
description: "Skill description"
metadata:
  {
    "emoji": "🔧",
    "requires": { "bins": ["command"] },
    "install": [...],
  }
---

# Skill Name

Skill documentation and usage guidelines.
```

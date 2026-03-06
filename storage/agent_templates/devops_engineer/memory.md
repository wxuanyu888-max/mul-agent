---
version: '1.0'
agent_id: devops_engineer
memory_strategy:
  short_term:
    storage: session
    max_size: 1MB
    auto_cleanup: true
    ttl_seconds: 3600
  long_term:
    storage: file
    path: storage/memory/long_term/devops_engineer
    compression: false
    auto_archive: true
    archive_interval: daily
handover:
  required_fields:
  - task_summary
  - context
  - next_steps
  - infrastructure_state
  format: markdown
  auto_generate: true
retrieval:
  default_limit: 10
  relevance_threshold: 0.7
  search_method: keyword

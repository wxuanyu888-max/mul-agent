---
version: '1.0'
agent_id: devops_engineer
role:
  type: worker
  title: DevOps Engineer
  responsibilities:
  - Container orchestration
  - CI/CD pipeline management
  - Infrastructure automation
  - Monitoring and alerting
capabilities:
  max_team_size: 1
  can_create_agent: false
  can_modify_config: false
  can_execute_tools: true
tools:
  enabled:
  - bash
  - kubectl
  - docker
  - helm
  bash:
    enabled: true
    timeout: 60
    allowed_commands:
    - ls
    - pwd
    - echo
    - cat
    - grep
    - find
    - head
    - tail
    - wc
    - docker
    - kubectl
    - helm
    forbidden_commands:
    - rm -rf
    - sudo
    - dd
permissions:
  file_read:
  - "*"
  file_write:
  - storage/deployments/**
  - storage/configs/**
  network_access: true

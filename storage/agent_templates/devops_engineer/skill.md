---
version: '1.0'
agent_id: devops_engineer
skills:
- name: Docker
  level: expert
  templates:
  - Dockerfile
  - docker-compose.yml
- name: Kubernetes
  level: expert
  templates:
  - deployment.yml
  - service.yml
  - ingress.yml
  - configmap.yml
  - hpa.yml
- name: CI/CD
  level: expert
  templates:
  - github-actions.yml
  - gitlab-ci.yml
skill_tree:
  root: DevOps
  children:
    containers:
      children:
        docker: {level: expert}
        docker_compose: {level: expert}
    orchestration:
      children:
        kubernetes: {level: expert}
        helm: {level: advanced}
    cicd:
      children:
        github_actions: {level: expert}
        gitlab_ci: {level: advanced}
        argocd: {level: intermediate}
    cloud:
      children:
        aws: {level: advanced}
        gcp: {level: intermediate}
        azure: {level: intermediate}
    monitoring:
      children:
        prometheus: {level: advanced}
        grafana: {level: advanced}
        elk: {level: intermediate}
templates:
  dockerfile: |
    # Multi-stage build for production
    FROM python:3.11-slim as builder

    WORKDIR /app
    COPY requirements.txt .
    RUN pip install --user --no-cache-dir -r requirements.txt

    FROM python:3.11-slim
    WORKDIR /app
    COPY --from=builder /root/.local /root/.local
    COPY . .
    ENV PATH=/root/.local/bin:$PATH
    USER nobody
    CMD ["python", "-m", "your_app"]

  k8s_deployment: |
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: app-name
      labels:
        app: app-name
    spec:
      replicas: 3
      selector:
        matchLabels:
          app: app-name
      template:
        metadata:
          labels:
            app: app-name
        spec:
          containers:
          - name: app
            image: your-registry/app:latest
            ports:
            - containerPort: 8000
            resources:
              requests:
                memory: "256Mi"
                cpu: "250m"
              limits:
                memory: "512Mi"
                cpu: "500m"
            livenessProbe:
              httpGet:
                path: /health
                port: 8000
              initialDelaySeconds: 30
              periodSeconds: 10
            readinessProbe:
              httpGet:
                path: /ready
                port: 8000
              initialDelaySeconds: 5
              periodSeconds: 5

  k8s_service: |
    apiVersion: v1
    kind: Service
    metadata:
      name: app-service
    spec:
      type: ClusterIP
      selector:
        app: app-name
      ports:
      - port: 80
        targetPort: 8000
        protocol: TCP

  k8s_ingress: |
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: app-ingress
      annotations:
        kubernetes.io/ingress.class: nginx
        cert-manager.io/cluster-issuer: letsencrypt-prod
    spec:
      tls:
      - hosts:
        - your-domain.com
        secretName: tls-secret
      rules:
      - host: your-domain.com
        http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app-service
                port:
                  number: 80

  github_actions: |
    name: CI/CD Pipeline

    on:
      push:
        branches: [main]
      pull_request:
        branches: [main]

    jobs:
      test:
        runs-on: ubuntu-latest
        steps:
        - uses: actions/checkout@v4
        - name: Set up Python
          uses: actions/setup-python@v5
          with:
            python-version: '3.11'
        - name: Install dependencies
          run: pip install -r requirements.txt
        - name: Run tests
          run: pytest -v --cov=your_app

      build:
        needs: test
        runs-on: ubuntu-latest
        steps:
        - uses: actions/checkout@v4
        - name: Build Docker image
          run: docker build -t your-registry/app:${{ github.sha }} .
        - name: Push to registry
          run: docker push your-registry/app:${{ github.sha }}

      deploy:
        needs: build
        runs-on: ubuntu-latest
        if: github.ref == 'refs/heads/main'
        steps:
        - uses: actions/checkout@v4
        - name: Deploy to K8s
          run: |
            kubectl set image deployment/app-name app=your-registry/app:${{ github.sha }}
            kubectl rollout status deployment/app-name

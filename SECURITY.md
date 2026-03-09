# Security Policy

## Reporting a Vulnerability

We take the security of mul-agent seriously. If you believe you have found a security vulnerability, please report it to us as described below.

**Please do NOT report security issues through public GitHub issues.**

Instead, please report them via email to security@mul-agent.local or create a private vulnerability report using GitHub's private vulnerability reporting feature.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Security Best Practices

### For Contributors

- Never commit secrets, API keys, or credentials to the repository
- Use environment variables for sensitive configuration
- Validate all user inputs
- Follow secure coding practices
- Run security scans before submitting PRs

### For Users

- Keep your API keys and credentials secure
- Use environment variables instead of hardcoding secrets
- Regularly update to the latest version
- Review security advisories

## Security Measures

The mul-agent project implements the following security measures:

1. **Secret Detection**: Automated scanning for leaked credentials
2. **Dependency Scanning**: Regular audits of third-party dependencies
3. **Code Review**: All changes undergo security review
4. **Access Control**: Principle of least privilege applied throughout

## Recognition

We believe in coordinated disclosure and will acknowledge contributors who help improve our security (with their permission).

## Contact

For security-related questions, please contact: security@mul-agent.local

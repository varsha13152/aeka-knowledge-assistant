---
name: image-security-lint
description: Security-focused Dockerfile linter for container hardening. Use when scanning Dockerfiles for security vulnerabilities, compliance issues, CIS Docker Benchmark violations, or container security best practices. Supports text, JSON, JUnit XML, and SARIF output formats.
metadata:
  version: 1.0.0
  category: code-analysis
  tags: security, docker, container, dockerfile, linting, cis-benchmark
  status: active
---

# Image Security Lint

Security-focused Dockerfile linter with 34 built-in rules (SEC001-SEC034) covering CIS Docker Benchmark, container hardening standards, and security best practices.

## Overview

Pure JavaScript/Node.js implementation with zero binary dependencies. Checks for:
- Running containers as root
- Hardcoded secrets and credentials
- Use of `:latest` tags
- Missing HEALTHCHECK instructions
- Privilege escalation patterns
- Package version pinning
- Unsafe download patterns (curl | sh)

## Installation

```bash
# Global install
npm install -g @paypalcorp/image-security-lint@latest

# Project dependency
npm install --save-dev @paypalcorp/image-security-lint@latest

# One-time use
npx @paypalcorp/image-security-lint@latest Dockerfile
```

## CLI Usage

### Basic Commands

```bash
# Lint default Dockerfile
image-security-lint

# Lint specific file
image-security-lint Dockerfile.prod

# Output formats
image-security-lint --format json         # JSON output
image-security-lint --format junit        # JUnit XML
image-security-lint --format sarif        # SARIF 2.1.0

# Write to file
image-security-lint --json > results.json
image-security-lint --junit-output results.xml
image-security-lint --sarif-output results.sarif
```

### Filtering Rules

```bash
# Security rules only
image-security-lint --only-security

# Base linting rules only
image-security-lint --only-base

# Ignore specific rules
image-security-lint --ignore SEC005,SEC008

# Enable only specific rules
image-security-lint --enable SEC001,SEC003,SEC014
```

### Output Control

```bash
# Only show errors
image-security-lint --quiet

# Detailed output with info messages
image-security-lint --verbose

# No color (for logs/CI)
image-security-lint --no-color
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed |
| 1 | Security issues found |
| 2 | Runtime error |

## Security Rules Reference

### Core Rules (SEC001-SEC008)

| ID | Name | Severity | Description |
|----|------|----------|-------------|
| SEC001 | no-root-user | error | Container must not run as root |
| SEC002 | no-sudo-install | warning | Avoid installing sudo |
| SEC003 | no-secrets | error | No hardcoded credentials/API keys |
| SEC004 | no-latest-tags | error | Use specific version tags |
| SEC005 | require-healthcheck | warning | Define HEALTHCHECK |
| SEC006 | no-unnecessary-privileges | error | Avoid privileged operations |
| SEC007 | multi-stage-secrets | warning | Don't copy secrets between stages |
| SEC008 | package-cache-cleanup | warning | Clean package manager cache |

### CIS Docker Benchmark Rules (SEC009-SEC019)

| ID | Name | Severity | Description |
|----|------|----------|-------------|
| SEC009 | require-copy-chown | warning | Use COPY --chown |
| SEC010 | no-setuid-setgid | error | No SETUID/SETGID bits |
| SEC011 | require-metadata-labels | info | Include version/description labels |
| SEC012 | no-apt-upgrade | warning | Avoid apt-get upgrade |
| SEC013 | require-workdir | warning | Use WORKDIR not cd |
| SEC014 | no-curl-wget-pipe | error | Don't pipe downloads to interpreters |
| SEC015 | pin-package-versions | warning | Pin all package versions |
| SEC016 | no-unnecessary-packages | info | Use --no-install-recommends |
| SEC017 | non-root-container | warning | Proper file ownership |
| SEC018 | scan-requirement | info | Document scanning compliance |
| SEC019 | source-attribution | info | OCI metadata labels |

### Compatibility Rules (SEC020-SEC034)

| ID | Name | Severity | Source |
|----|------|----------|--------|
| SEC020 | trusted-registries-only | error | DL3026 |
| SEC021 | prefer-copy-over-add | warning | DL3020 |
| SEC022 | no-sensitive-volume-mounts | error | DKL-DI-0002 |
| SEC023 | shell-pipefail-option | warning | DL4006 |
| SEC024 | combine-update-with-install | error | CIS-DI-0007 |
| SEC025 | require-y-flag | warning | DL3014 |
| SEC026 | use-apt-get-not-apt | warning | DL3027 |
| SEC027 | absolute-paths-in-workdir | error | DL3000 |
| SEC031 | single-entrypoint-only | error | DL4004 |
| SEC033 | exec-form-for-cmd-entrypoint | warning | DL3025 |
| SEC034 | valid-expose-port-numbers | error | DL3011 |

## Configuration File

```json
// .image-security-lint.json
{
  "rules": {
    "SEC001": "error",
    "SEC002": "warning",
    "SEC005": "warning"
  },
  "ignore": ["SEC011"],
  "customRules": {
    "PAYPAL001": "error"
  },
  "rulesPath": "./custom-rules"
}
```

## CI/CD Integration

### Harness Pipeline

```yaml
- step:
    type: Run
    name: "Dockerfile Security Lint"
    identifier: image_security_lint
    spec:
      shell: Sh
      command: |
        npx @paypalcorp/image-security-lint@latest Dockerfile \
          --sarif-output dockerfile-security.sarif \
          --quiet
```

### Harness STO (Security Testing Orchestration)

```bash
# Generate SARIF for STO ingestion
image-security-lint --sarif-output dockerfile-security.sarif
```

### JUnit for Test Reports

```bash
image-security-lint --junit-output test-results.xml
```

## Secure Dockerfile Example

```dockerfile
FROM node:18.17.0-alpine

WORKDIR /usr/src/app

RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

COPY package*.json ./

RUN npm ci --only=production && \
    npm cache clean --force

COPY --chown=nodejs:nodejs . .

USER nodejs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node healthcheck.js

CMD ["node", "server.js"]
```

## Programmatic Usage

```javascript
import { ImageSecurityLinter } from '@paypalcorp/image-security-lint';
import fs from 'fs';

const linter = new ImageSecurityLinter({
  enabledRules: ['SEC001', 'SEC003', 'SEC014'],
});

const content = fs.readFileSync('Dockerfile', 'utf-8');
const results = await linter.lint(content);

if (!results.valid) {
  console.error('Errors:', results.errors);
}
```

---
name: api-security-lint
description: Validate OpenAPI and Swagger specifications against PayPal API security policies using Spectral rules. Use when linting API specs, checking security compliance, validating x-visibility/x-serviceName/x-permissions, reviewing webhook authentication, or integrating security checks into CI/CD pipelines.
metadata:
  version: 1.0.0
  category: code-analysis
  tags: security, api, openapi, spectral, linting, compliance
  status: active
---

# API Security Lint

Spectral-based linting tool that validates OpenAPI/Swagger specifications against API security policies. Enforces Architecture Building Code (ABC) security standards directly from IDE, CI/CD, or CLI.

## Overview

API Security Lint uses Spectral rules to check API specifications for security issues including:
- Missing or misconfigured API visibility declarations
- Improper authentication/authorization setup
- Missing security classifications on data fields
- Webhook authentication gaps
- Input validation issues (string/array/number constraints)

## Installation

```bash
# Install Spectral CLI and security rules
npm install --save-dev @stoplight/spectral-cli
npm install --save-dev @paypalcorp/api-security-lint

# Create ruleset config
echo 'extends: ["@paypalcorp/api-security-lint"]' > .spectral.yaml
```

## CLI Usage

### Basic Linting

```bash
# Lint a single spec file
spectral lint openapi.yaml
spectral lint swagger.json

# With specific ruleset extension levels
echo 'extends: [["@paypalcorp/api-security-lint", recommended]]' > .spectral.yaml
echo 'extends: [["@paypalcorp/api-security-lint", all]]' > .spectral.yaml
```

### Output Formats

```bash
# JSON output for CI/CD parsing
spectral lint openapi.yaml --format json > results.json

# Pretty/stylish output (default)
spectral lint openapi.yaml --format stylish

# Exit codes: 0 = pass, non-zero = violations
```

## Security Rules

### ABC Policy Rules

| Rule | Policy | Description |
|------|--------|-------------|
| `x-serviceName-truthy` | Service ID | Services must declare x-serviceName |
| `x-serviceName-pattern` | Service ID | Comma-separated, no whitespace |
| `x-visibility-truthy-oas3` | Visibility | API must declare visibility level |
| `x-visibility-extent-pattern-oas3` | Visibility | Valid values: PUBLIC, COMPANY, PARTNER, INTERNAL, DOMAIN |
| `x-visibility-descendant-exposure` | Visibility | Child operations can't exceed parent visibility |
| `x-securityClassification-primitive-types-parameters` | Data Classification | Sensitive fields must be classified |
| `external-scopes` | OAuth2 | External APIs require OAuth2 scopes |
| `external-authorization` | Authorization | External APIs require proper auth |
| `x-permissions-required` | Permissions | Operations must declare permissions |
| `x-permissions-scope-pattern` | Permissions | Scope format validation |

### Input Validation Rules

| Rule | Description |
|------|-------------|
| `parameter-structure` | Validates parameter structure |
| `string-constraints` | String fields must have maxLength, pattern |
| `array-constraints` | Arrays must have maxItems |
| `number-constraints` | Numbers must have min/max bounds |
| `regex-pattern` | Validates regex patterns (ReDoS prevention) |
| `integer-minimum-maximum-required` | Integer ranges required |

### Webhook Security Rules

| Rule | Description |
|------|-------------|
| `webhook-requires-approved-auth` | Webhooks must use approved authentication |
| `webhook-jwt-valid-format` | JWT format validation |
| `webhook-hmac-has-header` | HMAC must specify header |
| `webhook-security-not-empty` | Security definitions required |
| `webhook-no-api-key-only` | API key alone not sufficient |

## Configuration

### Custom Ruleset Override

```yaml
# .spectral.yaml
extends: ["@paypalcorp/api-security-lint"]

rules:
  # Override severity
  x-serviceName-function: warn
  webhook-requires-approved-auth: error

  # Disable rules
  x-visibility-truthy-oas2: false
```

### Brand/BU-Specific Config

```yaml
# Venmo (disable x-serviceName)
extends: [["@paypalcorp/api-security-lint", all]]
rules:
  x-serviceName-function: false

# Release checklist (strict mode)
extends: [["@paypalcorp/api-security-lint", all]]
rules:
  x-serviceName-function: error
  x-visibility-truthy-oas3: error
```

## CI/CD Integration

### Harness Pipeline

```yaml
- step:
    type: Run
    name: "API Security Lint"
    identifier: api_security_lint
    spec:
      shell: Sh
      command: |
        npm install -g @stoplight/spectral-cli @paypalcorp/api-security-lint
        echo 'extends: ["@paypalcorp/api-security-lint"]' > .spectral.yaml
        spectral lint openapi.yaml --format json > lint-results.json
```

### Jenkins

```groovy
stage('API Security Lint') {
    steps {
        sh 'npx spectral lint swagger.json'
    }
}
```

## Batch Linting

```bash
# Lint multiple specs
for spec in specs/*.yaml; do
  spectral lint "$spec" --format json >> all-results.json
done

# Parallel linting (with GNU Parallel)
parallel --jobs 30 spectral lint {} ::: specs/*.yaml
```

## IDE Integration

- **VS Code**: Install Spectral VS Code extension, auto-detects `.spectral.yaml`
- **IntelliJ/PyCharm**: Spectral plugin available
- **NeoVim**: Spectral LSP configuration

## Supported Formats

- OpenAPI 3.x (OAS3) - Preferred
- Swagger 2.0 (OAS2) - Legacy support
- JSON and YAML input formats

## References

- ABC Policies: https://go/abc
- API Security Lint: https://go/api-security-lint
- Spectral Docs: https://docs.stoplight.io/docs/spectral

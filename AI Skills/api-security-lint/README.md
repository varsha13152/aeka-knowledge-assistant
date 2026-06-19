# API Security Lint Skill

Spectral-based linting tool that validates OpenAPI/Swagger specifications against PayPal's Architecture Building Code (ABC) security policies. Enforces security standards directly from IDE, CI/CD, or CLI.

## Quick Start

- "Lint my OpenAPI spec for security issues"
- "Check if my API meets ABC security policies"
- "Validate OAuth scopes and data classification in swagger.json"
- "Run API security lint on this spec"

## Version

**Current: 1.0.0** | Part of [prodsec-toolkit](https://go/prodsec-toolkit)

## Capabilities

| Feature | Description |
|---------|-------------|
| Spec formats | OpenAPI 3.x (OAS3), Swagger 2.0 (OAS2), JSON and YAML |
| Engine | Spectral CLI with `@paypalcorp/api-security-lint` ruleset |
| Policy enforcement | ABC security standards (visibility, scopes, data classification, input validation) |
| Webhook security | Authentication pattern validation for callbacks |
| IDE support | VS Code, IntelliJ/PyCharm, NeoVim via Spectral plugin |
| CI/CD | Harness, Jenkins, GitHub Actions pipeline integration |
| Output formats | Stylish (default), JSON, for CI/CD parsing |

## How to Use API Security Lint

Multiple options are available depending on your workflow:

1. **PPaaS Portal** - Request maturity review for rules 704, 705, 706 via the PPaaS Portal. Reviews take about 1 hour.
2. **PR GitHub Checks (Early Adopter Pilot)** - Enable automated lint checks on pull requests. Request access via DM to @asrour or #help-product-security.
3. **IDE Integration** - Real-time feedback using the Spectral plugin for VS Code, IntelliJ, or NeoVim.
4. **CI/CD Integration** - Jenkins, Harness, and GitHub Actions examples available.
5. **MCP Server** - Use the API Security MCP in Copilot, Claude Code, or Cursor for AI-assisted validation.

For full details see the [Options for Using API Security Lint](https://paypal.atlassian.net/wiki/spaces/DSH/pages/2587004689) guide.

## Installation

```bash
# Install Spectral CLI and security rules
npm install --save-dev @stoplight/spectral-cli
npm install --save-dev @paypalcorp/api-security-lint

# Create ruleset config
echo 'extends: ["@paypalcorp/api-security-lint"]' > .spectral.yaml
```

## Security Rules

### ABC Policy Rules

| Rule | Policy | Description |
|------|--------|-------------|
| `x-serviceName-truthy` | Service ID | Services must declare x-serviceName |
| `x-serviceName-pattern` | Service ID | Comma-separated, no whitespace |
| `x-visibility-truthy-oas3` | Visibility | API must declare visibility level |
| `x-visibility-extent-pattern-oas3` | Visibility | Valid: PUBLIC, COMPANY, PARTNER, INTERNAL, DOMAIN |
| `x-visibility-descendant-exposure` | Visibility | Child operations cannot exceed parent visibility |
| `x-securityClassification-primitive-types-parameters` | Data Classification | Sensitive fields must be classified |
| `external-scopes` | OAuth2 | External APIs require OAuth2 scopes |
| `external-authorization` | Authorization | External APIs require proper auth |
| `x-permissions-required` | Permissions | Operations must declare permissions |
| `x-permissions-scope-pattern` | Permissions | Scope format validation |

### Input Validation Rules

| Rule | Description |
|------|-------------|
| `string-constraints` | String fields must have maxLength, pattern |
| `array-constraints` | Arrays must have maxItems |
| `number-constraints` | Numbers must have min/max bounds |
| `integer-minimum-maximum-required` | Integer ranges required |
| `regex-pattern` | Validates regex patterns (ReDoS prevention) |
| `parameter-structure` | Validates parameter structure |

### Webhook Security Rules

| Rule | Description |
|------|-------------|
| `webhook-requires-approved-auth` | Webhooks must use approved authentication |
| `webhook-jwt-valid-format` | JWT format validation |
| `webhook-hmac-has-header` | HMAC must specify header |
| `webhook-security-not-empty` | Security definitions required |
| `webhook-no-api-key-only` | API key alone not sufficient |

## Prerequisites

Before running API Security Lint, ensure your OpenAPI spec passes JSON Schema and OAS Schema validations:

```bash
# Install redocly
npm i -g @redocly/cli@latest

# Validate schema and dereferencing
redocly lint v2/schema/swagger.json && redocly bundle v2/schema/swagger.json
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

## Configuration

```yaml
# .spectral.yaml - Override severity or disable rules
extends: ["@paypalcorp/api-security-lint"]
rules:
  x-serviceName-function: warn
  webhook-requires-approved-auth: error
  x-visibility-truthy-oas2: false
```

## Rule-Specific FAQs

- [704 - Scopes](https://paypal.atlassian.net/wiki/spaces/CloudSecurity/pages/912534786)
- [705 - Data Classification](https://go/api-security-lint/x-securityClassification)
- [706 - Data Validation](https://paypal.atlassian.net/wiki/spaces/DSH/pages/2083800955)

## Resources

| Resource | Link |
|----------|------|
| Changelog | [CHANGELOG.md](https://github.com/OnePayPal/prodsec-toolkit/blob/main/CHANGELOG.md) |
| ProdSec Toolkit | [https://go/prodsec-toolkit](https://go/prodsec-toolkit) |
| API Security Lint Docs | [https://go/prodsec-toolkit/docs/api-security-lint](https://go/prodsec-toolkit/docs/api-security-lint) |
| Options for Using API Security Lint | [Confluence](https://paypal.atlassian.net/wiki/spaces/DSH/pages/2587004689) |
| API-Security-Lint FAQ | [Confluence](https://paypal.atlassian.net/wiki/spaces/DSH/pages/2083888211) |
| Maturity Review (704/705/706) | [Confluence](https://paypal.atlassian.net/wiki/spaces/DSH/pages/2586995574) |
| ABC Policies | [https://go/abc](https://go/abc) |
| Source Repository | [github.paypal.com/paypalcorp/api-security-lint](https://github.paypal.com/paypalcorp/api-security-lint) |
| Spectral Docs | [docs.stoplight.io](https://docs.stoplight.io/docs/spectral) |
| Support | #help-product-security on Slack |

---
name: api-security-expert
description: Context-aware API security guidance based on PayPal's ABC policies and security documentation. Use when asking about authentication patterns (OAuth 2.0, mTLS), authorization (RBAC, scopes), data classification, input validation, API visibility, OWASP API Security Top 10, or reviewing API implementations for security compliance.
metadata:
  version: 1.1.0
  category: security
  tags: security, api, guidance, compliance, owasp, authentication, authorization
  status: active
---

# API Security Expert

Context-aware API security guidance powered by PayPal's comprehensive security documentation and Architecture Building Code (ABC) policies. Provides intelligent recommendations, documentation search, implementation checklists, and resource lookup.

## Overview

The API Security Expert analyzes your context, identifies the security domain and task type, and provides tailored recommendations with relevant documentation. It complements the API Security Lint (validation) by focusing on guidance and learning.

| API Security Expert | API Security Lint |
|---------------------|-------------------|
| **Purpose**: Guidance and learning | **Purpose**: Validation and compliance |
| **Focus**: "Learn how to make it correct" | **Focus**: "Check if it's correct" |
| **Tools**: Implementation guidance, docs search | **Tools**: Spec validation, policy enforcement |
| **Best For**: Learning, troubleshooting, implementation | **Best For**: CI/CD, real-time validation |

## Installation

```json
{
  "mcpServers": {
    "api-security-expert": {
      "command": "npx",
      "args": ["@paypalcorp/mcp-api-security-expert@1.1.0"]
    }
  }
}
```

Requires PayPal internal npm registry access:
```bash
npm config set @paypalcorp:registry https://npm.dev.paypalinc.com/
```

## Tools

### 1. `get-contextual-guidance`

Provides intelligent, context-aware guidance based on your query and work context. Automatically detects task type (implementation, troubleshooting, compliance, learning), security domain (authentication, authorization, data-protection, etc.), and urgency level.

```json
{
  "query": "How do I implement OAuth2 authentication for my external API?",
  "fileContext": "OpenAPI specification with PARTNER visibility",
  "taskType": "implementation"
}
```

### 2. `search-documentation`

Fast search across all API security documentation with category filtering.

Categories: `authentication`, `data-protection`, `input-validation`, `visibility-access`, `implementation`, `reference`, `abc-policies`, `troubleshooting`

```json
{
  "query": "x-securityClassification data protection",
  "category": "data-protection",
  "includeContent": true
}
```

### 3. `get-implementation-checklist`

Generates customized implementation checklists with validation commands.

Domains: `authentication`, `authorization`, `data-protection`, `input-validation`, `api-visibility`, `encryption`, `monitoring`

```json
{
  "securityDomain": "authentication",
  "taskType": "implementation"
}
```

### 4. `get-security-resources`

Retrieves organized security resources including tools, documentation, contacts, and links.

## Example Workflow

1. **Learn**: Use `get-contextual-guidance` to understand OAuth2 requirements for external APIs
2. **Plan**: Use `get-implementation-checklist` for authentication domain steps
3. **Implement**: Follow the guidance to update your OpenAPI spec
4. **Validate**: Use API Security Lint (`spectral lint`) to verify compliance
5. **Fix**: Use `get-contextual-guidance` with troubleshooting context for any violations

## Key Capabilities

- **Task Type Detection**: Identifies implementation, troubleshooting, compliance, learning, validation, or reference tasks
- **Security Domain Analysis**: Recognizes authentication, authorization, data-protection, input-validation, api-visibility, encryption, and monitoring domains
- **Smart Document Routing**: Serves primary and secondary documentation with relevant sections
- **ABC Policy Knowledge**: Full coverage of PayPal Architecture Building Code security standards
- **Tool Integration**: Commands for API Security Lint, SecDef, and other security tools

## References

- ABC Policies: https://go/abc
- API Security Expert MCP Server: https://paypal.atlassian.net/wiki/spaces/DSH/pages/2632392930
- MCP Security User Guide: https://paypal.atlassian.net/wiki/spaces/DSH/pages/2617302657
- ProdSec Toolkit: https://go/prodsec-toolkit
- Source Repository: https://github.paypal.com/AppSec/api-security-expert
- Support: #help-product-security on Slack

# API Security Expert Skill

Context-aware API security guidance powered by PayPal's Architecture Building Code (ABC) policies. Provides intelligent recommendations, implementation checklists, documentation search, and security resource lookup via 4 MCP tools.

## Quick Start

- "What authentication method should I use for my external API?"
- "How do I add data classification to my OpenAPI spec?"
- "Help me understand the x-visibility requirements"
- "Give me an implementation checklist for OAuth2"

## Version

**Current: 1.1.0** | See [Confluence](https://paypal.atlassian.net/wiki/spaces/DSH/pages/2632392930) for release history.

## Capabilities

| Feature | Description |
|---------|-------------|
| Context analysis | Detects task type, security domain, document type, urgency |
| Security domains | Authentication, authorization, data-protection, input-validation, api-visibility, encryption, monitoring |
| Task types | Implementation, troubleshooting, compliance, learning, validation, reference |
| Documentation | Full ABC policy coverage, implementation guides, tool integration commands |
| Test suite | 58 comprehensive tests (unit, integration, MCP protocol, performance) |

## Complementary Pairing

Use together with **API Security Lint** for comprehensive API security coverage:

| API Security Expert | API Security Lint |
|---------------------|-------------------|
| Guidance and learning | Validation and compliance |
| "Learn how to make it correct" | "Check if it's correct" |
| Implementation guidance, docs search | Spec validation, policy enforcement |
| Learning, troubleshooting | CI/CD, real-time validation |

Combined, they provide **8 tools** covering all aspects of API security.

## Installation

### Prerequisites

- Node.js 18+
- PayPal internal npm registry access

```bash
# Configure PayPal npm registry (required first step)
npm config set @paypalcorp:registry https://npm.dev.paypalinc.com/
```

### Claude Code / Claude Desktop

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

### Recommended: Both MCP Servers

```json
{
  "mcpServers": {
    "mcp-security": {
      "command": "npx",
      "args": ["@paypalcorp/mcp-security@1.1.0"]
    },
    "api-security-expert": {
      "command": "npx",
      "args": ["@paypalcorp/mcp-api-security-expert@1.1.0"]
    }
  }
}
```

## Available Tools

### 1. `get-contextual-guidance`

Intelligent, context-aware guidance based on your query and work context. Automatically identifies the security domain, task type, and urgency.

**Parameters**: `query` (required), `fileContext`, `taskType`, `maxResults`

### 2. `search-documentation`

Fast search across all API security documentation.

**Parameters**: `query` (required), `category`, `maxResults`, `includeContent`

**Categories**: authentication, data-protection, input-validation, visibility-access, implementation, reference, abc-policies, troubleshooting

### 3. `get-implementation-checklist`

Customized checklists with validation commands for a given security domain.

**Parameters**: `securityDomain`, `taskType`

**Domains**: authentication, authorization, data-protection, input-validation, api-visibility, encryption, monitoring

### 4. `get-security-resources`

Organized resources including tools, documentation, contacts, and links.

## Example Workflows

### OAuth2 Implementation

1. `get-contextual-guidance` - "I need to add OAuth2 for my external partner API"
2. `get-implementation-checklist` - domain: authentication, task: implementation
3. Implement the changes in your OpenAPI spec
4. Validate with API Security Lint: `spectral lint openapi.yaml`

### Troubleshooting Lint Violations

1. Run `spectral lint` and note the violations
2. `get-contextual-guidance` - "x-serviceName is missing from my spec" (taskType: troubleshooting)
3. Apply the fix
4. Re-validate

### Data Classification

1. `search-documentation` - "x-securityClassification" (category: data-protection)
2. `get-implementation-checklist` - domain: data-protection
3. Apply classifications to your spec fields
4. Validate Rule 705 compliance

## Troubleshooting

**"Package not found"** - Configure PayPal npm registry first (see Installation).

**"MCP server not connecting"** - Verify Claude Desktop config syntax, restart Claude Desktop, check Node.js 18+.

**Debug mode**:
```bash
DEBUG=mcp:* npx @paypalcorp/mcp-api-security-expert@1.1.0
```

## Resources

| Resource | Link |
|----------|------|
| Changelog | [CHANGELOG.md](https://github.com/OnePayPal/prodsec-toolkit/blob/main/CHANGELOG.md) |
| ProdSec Toolkit | [https://go/prodsec-toolkit](https://go/prodsec-toolkit) |
| API Security Expert MCP Docs | [Confluence](https://paypal.atlassian.net/wiki/spaces/DSH/pages/2632392930) |
| MCP Security User Guide | [Confluence](https://paypal.atlassian.net/wiki/spaces/DSH/pages/2617302657) |
| ABC Policies | [https://go/abc](https://go/abc) |
| Source Repository | [github.paypal.com/AppSec/api-security-expert](https://github.paypal.com/AppSec/api-security-expert) |
| Support | #help-product-security on Slack |
| Maintainer | DT-PCIS-SCANAPAC |

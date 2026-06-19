# Dockerfile Security Lint Skill

Security-focused Dockerfile linter with 46 built-in rules (SEC001-SEC046) covering CIS Docker Benchmark, supply-chain risks, privilege escalation, and container hardening best practices.

## Quick Start

- "Lint this Dockerfile for security issues"
- "Check my Dockerfile against CIS Docker Benchmark"
- "Scan Dockerfile.prod for hardcoded secrets"
- "Run image security lint on this container config"

## Version

**Current: 1.0.0** | Part of [prodsec-toolkit](https://go/prodsec-toolkit)

## Capabilities

| Feature | Description |
|---------|-------------|
| Rules | 46 security rules (SEC001-SEC046) |
| Standards | CIS Docker Benchmark, container hardening best practices |
| Language | Pure JavaScript/Node.js, zero binary dependencies |
| Output formats | Text (default), JSON, JUnit XML, SARIF 2.1.0 |
| MCP server | AI-assisted linting via Cosmos-hosted SSE endpoint |
| CI/CD | Harness STO (SARIF), Jenkins (JUnit), GitHub Actions |
| Exit codes | 0 = pass, 1 = security issues, 2 = runtime error |

## Installation

```bash
# Global install
npm install -g @paypalcorp/image-security-lint@latest

# Project dependency
npm install --save-dev @paypalcorp/image-security-lint@latest

# One-time use
npx @paypalcorp/image-security-lint@latest Dockerfile
```

### MCP Server

```bash
# Claude Code
claude mcp add --transport sse image-security-lint https://aiplatform.dev51.cbf.dev.paypalinc.com/byoa/image-security--0243a/sse

# VS Code (GitHub Copilot)
code --add-mcp '{"name":"image-security-lint","url":"https://aiplatform.dev51.cbf.dev.paypalinc.com/byoa/image-security--0243a/sse","type":"http"}'
```

Requires PayPal VPN. Also available for Cursor, Codex, and Claude Desktop.

## CLI Usage

```bash
# Lint default Dockerfile
image-security-lint

# Lint specific file with output format
image-security-lint Dockerfile.prod --format json
image-security-lint --format sarif > results.sarif
image-security-lint --format junit > results.xml

# Filter rules
image-security-lint --only-security          # Security rules only
image-security-lint --ignore SEC005,SEC008   # Skip specific rules
image-security-lint --quiet                  # Errors only
```

## Security Rules

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

### CIS Docker Benchmark Rules (SEC009-SEC020)

| ID | Name | Severity | Description |
|----|------|----------|-------------|
| SEC009 | require-copy-chown | warning | Use COPY --chown |
| SEC010 | no-setuid-setgid | error | No SETUID/SETGID bits |
| SEC014 | no-curl-wget-pipe | error | Don't pipe downloads to interpreters |
| SEC015 | pin-package-versions | warning | Pin all package versions |
| SEC017 | non-root-container | warning | Proper file ownership |
| SEC020 | trusted-registries-only | error | Use trusted registries only |

### Additional Rules (SEC021-SEC046)

Covers compatibility with Hadolint (DL series), shell pipefail, WORKDIR validation, ENTRYPOINT constraints, EXPOSE port validation, and more. See the [full rules documentation](https://go/prodsec-toolkit/docs/image-security-lint) for details.

## CI/CD Integration

### Harness STO (SARIF)

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

## MCP Server Tools

| Tool | Description |
|------|-------------|
| `prodsec_lint_dockerfile` | Lint Dockerfile content for security issues |
| `prodsec_lint_get_rules` | List available rules with severity/tag filtering |
| `prodsec_lint_explain_rule` | Detailed explanation and remediation for a rule |
| `prodsec_lint_version` | Installed engine version and rule count |

## Resources

| Resource | Link |
|----------|------|
| Changelog | [CHANGELOG.md](https://github.com/OnePayPal/prodsec-toolkit/blob/main/CHANGELOG.md) |
| ProdSec Toolkit | [https://go/prodsec-toolkit](https://go/prodsec-toolkit) |
| Image Security Lint Docs | [https://go/prodsec-toolkit/docs/image-security-lint](https://go/prodsec-toolkit/docs/image-security-lint) |
| Source Repository | [github.com/OnePayPal/prodsec-toolkit](https://github.com/OnePayPal/prodsec-toolkit) |
| Support | #help-product-security on Slack |
| Maintainer | DT-PCIS-SCANAPAC |

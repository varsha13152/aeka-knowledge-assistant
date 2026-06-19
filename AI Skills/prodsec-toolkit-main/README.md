# prodsec-toolkit

ProdSec API Security toolkit - a collection of Claude Code skills, subagents, and MCP server configurations for security engineering workflows. Published to the [PayPal AI Hub](https://onepaypal.github.io/paypal-sdlc-assistant/).

## Skills

| Skill | Description |
|-------|-------------|
| [nuclei-template-creator](skills/nuclei-template-creator/) | Create Nuclei security templates for vulnerability detection |
| [modelscan-cli](skills/modelscan-cli/) | Scan ML/AI models for malicious code and serialization attacks |
| [vault-goblin](skills/vault-goblin/) | HashiCorp Vault secrets management via AppRole |
| [harness-pipeline-creator](skills/harness-pipeline-creator/) | Harness CI/CD pipeline creation and template design |
| [api-security-lint](skills/api-security-lint/) | API specification security linting with Spectral |
| [image-security-lint](skills/image-security-lint/) | Dockerfile security linting for container hardening |

## Subagents

| Subagent | Description |
|----------|-------------|
| [api-security-agent](subagents/api-security-agent.md) | API security guidance, design review, and best practices |
| [api-security-standards-expert](subagents/api-security-standards-expert.md) | Policy-backed API security standards and compliance |
| [harness-template-engineer](subagents/harness-template-engineer.md) | Harness CI/CD template creation and management |
| [autosec-branch-manager](subagents/autosec-branch-manager.md) | Automated security remediation branch workflow |
| [cve-autofix](subagents/cve-autofix.md) | Automated CVE patching across repositories |

## Installation

### Claude Code (CLI)
```bash
# Clone and add to your skills directory
git clone https://github.com/OnePayPal/prodsec-toolkit.git
cp -r prodsec-toolkit/skills/* ~/.claude/skills/
cp prodsec-toolkit/subagents/* ~/.claude/agents/
```

### Via AI Hub
Browse and install from the [AI Hub marketplace](https://onepaypal.github.io/paypal-sdlc-assistant/).

## Contributing

1. Create your skill/subagent following the templates in `CLAUDE.md`
2. Validate with `node scripts/validate.js`
3. Submit a PR to this repo
4. Changes auto-sync to the AI Hub on merge

## Team

**DT-PCIS-SCANAPAC** - Product Security, API Security team

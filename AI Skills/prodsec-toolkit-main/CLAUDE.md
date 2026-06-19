# prodsec-toolkit

ProdSec API Security toolkit for Claude Code - skills, subagents, and MCP servers published to the PayPal AI Hub.

## Structure

```
prodsec-toolkit/
├── skills/                  # Claude Code skills (SKILL.md per directory)
├── subagents/               # Claude Code subagents (*.md with frontmatter)
├── mcp-servers/             # MCP server configs (*.yaml)
├── commands/                # Slash commands (*.md with frontmatter)
├── scripts/                 # Validation and sync scripts
└── .harness/                # CI/CD pipeline for ai-hub sync
```

## Publishing to AI Hub

This repo is the source of truth for ProdSec security tools published to [OnePayPal/paypal-sdlc-assistant](https://github.com/OnePayPal/paypal-sdlc-assistant).

### Validation
Before committing, validate your changes:
```bash
# Validate skills
node scripts/validate.js skills

# Validate subagents
node scripts/validate.js subagents
```

### Manual Publish
To manually sync to ai-hub:
```bash
./scripts/sync-to-aihub.sh
```

### Automated Publish
The Harness pipeline in `.harness/` automatically:
1. Validates all content on push to `main`
2. Syncs changed files to the ai-hub repo
3. Creates/updates a PR on `OnePayPal/paypal-sdlc-assistant`

## Adding Content

### New Skill
```bash
mkdir skills/<skill-name>
# Create skills/<skill-name>/SKILL.md with required frontmatter:
# name, description, metadata (version, category, tags, status)
```

### New Subagent
```bash
# Create subagents/<name>.md with required frontmatter:
# name, description, category
```

### New MCP Server
```bash
# Create mcp-servers/<name>.yaml following the ai-hub schema
```

## Categories

### Skill Categories
code-analysis, testing, framework, development, utilities, miscellaneous

### Subagent Categories
development-architecture, language-specialists, infrastructure-operations, quality-security, data-ai, specialized-domains

### MCP Server Categories
productivity, developer-tools, data-integration, security, analytics, automation

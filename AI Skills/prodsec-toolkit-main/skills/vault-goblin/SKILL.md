---
name: vault-goblin
description: Secure HashiCorp Vault helper for listing, adding, and modifying secrets via AppRole authentication. Use when managing secrets in Vault, rotating credentials, or performing secret CRUD operations. Requires VAULT_SECRET_ID in environment or .env file. Never exposes secrets in CLI output.
metadata:
  version: 1.0.0
  category: utilities
  tags: security, vault, secrets-management, hashicorp
  status: active
---

# Vault Goblin

A secure HashiCorp Vault helper skill that manages secrets without exposing them in CLI output or logs.

## Security Requirements

**CRITICAL:**
- Never echo, print, or log the `VAULT_SECRET_ID` or `VAULT_ROLE_ID`
- Never include secrets in command output that will be visible to user
- Always mask secret values when listing (show only length and first/last 2 chars)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `VAULT_ADDR` | Yes | Primary Vault API endpoint |
| `VAULT_ADDR_SECONDARY` | No | Failover endpoint |
| `VAULT_ROLE_ID` | Yes | AppRole role ID |
| `VAULT_SECRET_ID` | Yes | AppRole secret ID (KEEP SECURE) |

## Vault Path Structure

**Base Path:** `secret/KV/data/prodsec/<SECRET_NAME>`
**Metadata Path:** `secret/KV/metadata/prodsec/<SECRET_NAME>`

## Secret Naming Convention

Use the format: `<type>-<service>-<purpose>`

### Types (Prefix)

| Prefix | Type | Example |
|--------|------|---------|
| `tok` | Token (short-lived, rotatable) | `tok-harness-api` |
| `key` | API Key (long-lived) | `key-datadog-ingest` |
| `cred` | Credentials (user/pass pair) | `cred-github-svc` |
| `cert` | Certificate or private key | `cert-mtls-client` |
| `env` | Environment config | `env-prod-db-conn` |
| `hook` | Webhook secret | `hook-slack-alerts` |

## Operations

### Authenticate and Perform Operation (Combined)

```bash
bash -c 'VAULT_ADDR=$(grep "^VAULT_ADDR=" .env | head -1 | cut -d"=" -f2-); VAULT_ROLE_ID=$(grep "^VAULT_ROLE_ID=" .env | cut -d"=" -f2-); VAULT_SECRET_ID=$(grep "^VAULT_SECRET_ID=" .env | cut -d"=" -f2-); VAULT_TOKEN=$(curl -s --request POST --header "Content-Type: application/json" --data "{\"role_id\": \"$VAULT_ROLE_ID\", \"secret_id\": \"$VAULT_SECRET_ID\"}" "$VAULT_ADDR/v1/auth/approle/login" | jq -r ".auth.client_token"); echo "Authenticated: $([[ -n $VAULT_TOKEN && $VAULT_TOKEN != null ]] && echo yes || echo no)"'
```

### List Secrets

```bash
bash -c '... VAULT_TOKEN=$(curl -s ...); curl -s --header "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/secret/KV/metadata/prodsec?list=true" | jq ".data.keys"'
```

### Read Secret (Masked)

Replace `<SECRET_NAME>` with the secret name. Output shows only length and first/last 2 chars.

### Create/Update Secret

Replace `<SECRET_NAME>` and `<SECRET_VALUE>` with actual values.

### Delete Secret

Replace `<SECRET_NAME>` with the secret to delete.

## Troubleshooting

| HTTP Code | Meaning | Action |
|-----------|---------|--------|
| 200 | Success | Proceed |
| 403 | Permission denied | Check AppRole policies |
| 404 | Path not found | Verify path exists |
| 503 | Vault sealed | Try VAULT_ADDR_SECONDARY |

## Security Reminders

- **NEVER** display `VAULT_SECRET_ID` or `VAULT_TOKEN` in output
- **ALWAYS** mask secret values (show length + first/last 2 chars max)
- **ALWAYS** use `-s` (silent) flag with curl
- Use `bash -c '...'` to avoid zsh parsing issues

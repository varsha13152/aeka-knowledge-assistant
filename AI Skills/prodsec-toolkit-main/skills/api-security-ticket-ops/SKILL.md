---
name: api-security-ticket-ops
description: |
  Create Jira LI (Live Issues) tickets from API Security Lint maturity violations (criteria 704,
  705, 706). This skill should be used when lint results show maturity failures, PPaaS review
  requests are rejected, API specs fail security validation, or remediation tracking tickets are
  needed. It maps violation data (rule ID, severity, API visibility, ownership) to Jira ticket
  fields using a decision tree for priority, issue type, labels, summary, description, and
  assignee. Recovers API ownership and external-ability from Stargate/PPaaS metadata. Triggers
  include "create ticket for lint violation", "file security ticket", "704/705/706 violation",
  "maturity failure ticket", or any request to track API security lint findings in Jira.
metadata:
  version: 1.0.0
  category: security
  tags: jira, tickets, api-security, maturity, lint, vulnerability-management
  status: active
---

# API Security Ticket Ops

Create and manage Jira LI tickets from API Security Lint maturity violations (704, 705, 706) with correct priority, ownership, and traceability.

All tickets target **Project: LI**, **Issue Type: Security Vulnerability**.

---

## Phase 1: Gather Violation Context

Before creating any ticket, collect data from three sources.

### 1a. Lint Results (Spectral JSON Output)

Extract from the Spectral lint run:
- Rule IDs that fired (e.g., `string-constraints`, `external-scopes`)
- Severity per rule (`error`, `warning`, `info`)
- Total error count and warning count
- File paths with violations
- Spectral artifact URL (if available from pipeline)

### 1b. PPaaS Metadata

Look up the API via PPaaS metadata service or MCP tools. Extract:

| Field | Source | Example |
|-------|--------|---------|
| `api_id` | PPaaS MDS | `3719176155274713` |
| `title` | PPaaS MDS | `Payment Evaluation` |
| `github_url` | PPaaS MDS | `https://github.paypal.com/ApiSpecifications-R/risk.PaymentEvaluationSpecification` |
| `github_branch` | PPaaS MDS | `master` or `v1.15` |
| `version` | PPaaS MDS | `v2` |
| `schema_url` | PPaaS MDS | Full path to swagger.json |
| `lifecycle_state` | PPaaS MDS | `PLANNED`, `LIVE` |
| `owners` | PPaaS MDS | List of owner objects (name, email) |

### 1c. Ownership Recovery Chain

Resolve the API owner using this ordered fallback. Stop at first success.

1. **PPaaS `owners` field** - Use the first owner's email from PPaaS metadata
2. **Stargate / CAL lookup** - Extract `x-serviceName` from the spec's `info` block, query Stargate CLI (`stargate get-service {x-serviceName}`) or CAL for the owning team
3. **CODEOWNERS file** - Check the GitHub repo root for a CODEOWNERS file, match the spec file path
4. **PayPal Ownership platform** - Search [go/ownership](https://go/ownership) by service name
5. **git blame** - Run `git blame` on the swagger/schema file to identify the last editor

If all five fail: leave ticket unassigned. Add a comment:
> Ownership could not be determined for this API. See [API Ownership](https://paypal.atlassian.net/wiki/spaces/CloudSecurity/pages/329556189) for resolution steps.

### 1d. External-Ability (x-visibility)

Extract `x-visibility` from the OpenAPI spec's `info` block or operation level. Possible values:

| Value | Meaning | Impact on Priority |
|-------|---------|-------------------|
| `PUBLIC` | Internet-facing, external consumers | Highest priority |
| `PARTNER` | Partner-facing, limited external | Highest priority |
| `COMPANY` | Internal cross-domain | Medium priority |
| `INTERNAL` | Same domain only | Lower priority |
| `DOMAIN` | Domain-scoped | Lower priority |

If `x-visibility` is absent: treat as `INTERNAL` (conservative default).

### 1e. Rule-to-Criterion Mapping

Map each violated rule to its maturity criterion:

| Criterion | Maturity ID | Rule IDs |
|-----------|-------------|----------|
| **704 - OAuth2 Scopes** | 1923 | `external-scopes` (033), `external-authorization` (034), `x-permissions-required` (035) |
| **705 - Data Classification** | 1924 | `x-securityClassification-primitive-types-parameters`, `x-securityClassification-*` |
| **706 - Input Validation** | 1925 | `parameter-structure`, `string-constraints`, `array-constraints`, `number-constraints`, `object-constraints`, `readonly-required`, `unique-parameters`, `file-parameters`, `allow-empty-value`, `non-body-types`, `regex-pattern`, `regex-pattern-schema` |

Create one ticket per criterion. If an API fails multiple criteria, create separate tickets for each.

---

## Phase 2: Decision Tree - Determine Ticket Fields

### 2a. Priority

Combine the highest severity of violations with the API's `x-visibility`:

| Violation Severity | PUBLIC / PARTNER | COMPANY | INTERNAL / DOMAIN |
|--------------------|------------------|---------|-------------------|
| error | **P1** | **P2** | **P3** |
| warning | **P2** | **P3** | **P3** |
| info | **P3** | **P3** | **P3** |

**Error count modifier:** If total errors for the criterion >= 10, escalate by one level (P3 -> P2, P2 -> P1). P1 stays P1.

Priority field values: P1 = `{"name": "P1"}`, P2 = `{"name": "P2"}`, P3 = `{"name": "P3"}`

### 2b. Summary

Use these templates per criterion (one ticket per criterion per API):

| Criterion | Summary Template |
|-----------|-----------------|
| 704 | `[API Security Lint] Add OAuth2 scopes - {api_title} {version} ({x-visibility})` |
| 705 | `[API Security Lint] Add x-securityClassification - {api_title} {version}` |
| 706 | `[API Security Lint] Add input validation - {api_title} {version} ({error_count} violations)` |

### 2c. Labels

Always apply all of:
- `maturity-704`, `maturity-705`, or `maturity-706` (matching criterion)
- `api-security-lint`
- `visibility-{x-visibility}` (e.g., `visibility-PUBLIC`)

Conditional:
- If `x-visibility` is `PUBLIC` or `PARTNER`: add `external-api`

### 2d. Assignee

Use the owner resolved from the ownership recovery chain (Phase 1c).
Look up the Jira account ID via `lookupJiraAccountId(cloudId: "paypal.atlassian.net", searchString: "{owner_email_prefix}")`.

### 2e. Links

Add these as remote links or in the description:

| Link Type | URL Template |
|-----------|-------------|
| GitHub Repository | `{github_url}/tree/{github_branch}` |
| PPaaS Portal | `https://ppaas.paypalinc.com/api/{api_id}#apiReference` |
| Remediation Guide | Per criterion (see Confluence References below) |
| Lint Artifact | GCS/pipeline artifact URL (if available) |

### 2f. Components

If `x-serviceName` is present in the spec, set it as the component value.

---

## Phase 3: Ticket Creation

### 3a. Duplicate Check

Before creating, search for existing tickets:

```
project = LI AND summary ~ "{api_title}" AND labels = "maturity-{criterion_number}" AND status != Closed
```

If a match exists, present options:
- Update the existing ticket with new violation counts
- Create a new ticket and link as related
- Skip creation

### 3b. Create Ticket

Use `createJiraIssue` with:

```
projectKey: LI
issueTypeName: Security Vulnerability
summary: [from 2b]
description: [from description template below]
priority: [from 2a]
labels: [from 2c]
assignee_account_id: [from 2d]
```

### 3c. Description Template

Use this structure for all three criteria. Swap the Remediation section per criterion.

```markdown
## Objective
Resolve {criterion_name} violations on {api_title} {version} to pass PPaaS maturity criterion {criterion_number}.

## Violation Details
- **API**: {api_title} ({api_id})
- **Repository**: {github_url}/tree/{github_branch}
- **Schema**: {schema_url}
- **Visibility**: {x-visibility}
- **Service**: {x-serviceName}
- **Lifecycle State**: {lifecycle_state}
- **Errors**: {error_count} | **Warnings**: {warning_count}

## Rules Violated
{for each rule: "- **{rule_id}**: {rule_message} ({severity}) - {file_path}:{line}"}

## Remediation
{criterion-specific remediation - see below}

## References
- [API Security Lint](https://paypal.atlassian.net/wiki/spaces/DSH/pages/1155041921)
- [FAQ](https://paypal.atlassian.net/wiki/spaces/DSH/pages/2083888211)
- [Maturity Review Process](https://paypal.atlassian.net/wiki/spaces/DSH/pages/2586995574)
- PPaaS Portal: https://ppaas.paypalinc.com/api/{api_id}#apiReference
```

#### 704 Remediation Section
```markdown
Add OAuth2 security definitions with valid scopes to all operations where x-visibility is PUBLIC, PARTNER, or COMPANY.

1. Define `securityDefinitions` (OAS2) or `components.securitySchemes` (OAS3) with OAuth2 type
2. Add `security` requirement to each operation with at least one scope
3. Ensure scopes in operation security match those defined in securitySchemes

See: [OAuth2 Scopes Guide](https://paypal.atlassian.net/wiki/spaces/CloudSecurity/pages/912534786)
ABC Policy: [OAuth2 Scope Definition](https://github.paypal.com/pages/Engineering-Documentation-R/architecturebuildingcode/docs/abc-v2/design-standards/api-design-standards/api-security/#oauth2-scope-definition-and-provisioning)
```

#### 705 Remediation Section
```markdown
Tag all data fields with x-securityClassification including data_class (security level) and data_category.

1. Add `x-securityClassification` to all primitive type properties and parameters
2. Set `data_class` to the appropriate security level
3. Set `data_category` to the data type (e.g., ConsumerPersonal, Financial)

See: [Data Classification Guide](https://go/api-security-lint/x-securityClassification)
ABC Policy: [REST: x-securityClassification](https://paypal.atlassian.net/wiki/spaces/CloudSecurity/pages/795150584)
```

#### 706 Remediation Section
```markdown
Add input validation constraints to all parameters and schema properties.

Key rules to address:
- **string-constraints**: Add minLength, maxLength, and pattern to all string types
- **number-constraints**: Add minimum and maximum to all number/integer types
- **array-constraints**: Add items, minItems, and maxItems to all array types
- **object-constraints**: Add minProperties, maxProperties when additionalProperties is used
- **parameter-structure**: Ensure all parameters have name, in, and required:true for path params
- **regex-pattern**: Validate regex patterns are not vulnerable to ReDoS

See: [706 Data Validation Guide](https://paypal.atlassian.net/wiki/spaces/DSH/pages/2083800955)
ABC Policy: [Request Validation](https://github.paypal.com/pages/Engineering-Documentation-R/architecturebuildingcode/docs/abc-v2/design-standards/api-design-standards/api-security/#request-validation)
```

### 3d. Add Links

After ticket creation, add remote links via Jira API:
- GitHub repo URL
- PPaaS portal URL
- Lint artifact URL (if available)

---

## Phase 4: Verification

After creation, confirm:
- Ticket exists in LI project with type Security Vulnerability
- Priority matches the decision tree output
- Labels include criterion, source, and visibility tags
- Assignee is set (or gap is documented in a comment)
- Description contains all violation details and remediation guidance
- Links to GitHub, PPaaS portal, and Confluence are present
- No duplicate ticket was created

---

## Three Default High-Priority Scenarios

These are the three canonical ticket types. Each represents a common, high-priority violation.

### Scenario A: 704 - Missing OAuth Scopes on External API

**Trigger**: `external-scopes` rule fires on an operation with `x-visibility: PUBLIC`

| Field | Value |
|-------|-------|
| Project | LI |
| Type | Security Vulnerability |
| Priority | P1 |
| Summary | `[API Security Lint] Add OAuth2 scopes - Payment API v2 (PUBLIC)` |
| Labels | `maturity-704`, `api-security-lint`, `visibility-PUBLIC`, `external-api` |
| Remediation | Define OAuth2 securitySchemes, add security requirement with scopes |

**Why P1**: External-facing API without authentication scopes is a direct exposure risk.

### Scenario B: 705 - Missing Data Classification

**Trigger**: `x-securityClassification-primitive-types-parameters` rule fires

| Field | Value |
|-------|-------|
| Project | LI |
| Type | Security Vulnerability |
| Priority | P1 (if PUBLIC/PARTNER) or P2 (if COMPANY) |
| Summary | `[API Security Lint] Add x-securityClassification - User Profile API v1` |
| Labels | `maturity-705`, `api-security-lint`, `visibility-{x-visibility}` |
| Remediation | Tag all primitive properties with data_class and data_category |

**Why High**: Unclassified data fields cannot be properly protected by downstream controls.

### Scenario C: 706 - Missing Input Validation

**Trigger**: `string-constraints`, `number-constraints`, or other input validation rules fire

| Field | Value |
|-------|-------|
| Project | LI |
| Type | Security Vulnerability |
| Priority | P2 (default for error severity on COMPANY API) |
| Summary | `[API Security Lint] Add input validation - Checkout API v3 (14 violations)` |
| Labels | `maturity-706`, `api-security-lint`, `visibility-COMPANY` |
| Remediation | Add minLength/maxLength/pattern to strings, min/max to numbers, items/minItems/maxItems to arrays |

**Why P2**: Missing input validation enables injection attacks and resource abuse. Escalate to P1 if >= 10 errors on a PUBLIC API.

---

## Confluence References

| Topic | URL |
|-------|-----|
| API Security Lint (main) | https://paypal.atlassian.net/wiki/spaces/DSH/pages/1155041921 |
| FAQ | https://paypal.atlassian.net/wiki/spaces/DSH/pages/2083888211 |
| 704 - OAuth2 Scopes | https://paypal.atlassian.net/wiki/spaces/CloudSecurity/pages/912534786 |
| 705 - Data Classification | https://go/api-security-lint/x-securityClassification |
| 706 - Input Validation | https://paypal.atlassian.net/wiki/spaces/DSH/pages/2083800955 |
| Maturity Review Process | https://paypal.atlassian.net/wiki/spaces/DSH/pages/2586995574 |
| API Ownership | https://paypal.atlassian.net/wiki/spaces/CloudSecurity/pages/329556189 |
| PPaaS Maturity Model | https://ppaas.paypalinc.com/maturity-model/2.1_ext |
| ABC - OAuth2 Scopes | https://github.paypal.com/pages/Engineering-Documentation-R/architecturebuildingcode/docs/abc-v2/design-standards/api-design-standards/api-security/#oauth2-scope-definition-and-provisioning |
| ABC - Request Validation | https://github.paypal.com/pages/Engineering-Documentation-R/architecturebuildingcode/docs/abc-v2/design-standards/api-design-standards/api-security/#request-validation |
| ABC - x-visibility | https://github.paypal.com/pages/Engineering-Documentation-R/architecturebuildingcode/docs/abc-v2/design-standards/api-design-standards/api-security/x-visibility-property |

## Attribution

All tickets attributed to the API owner or relevant team lead. Never include AI co-author attribution.

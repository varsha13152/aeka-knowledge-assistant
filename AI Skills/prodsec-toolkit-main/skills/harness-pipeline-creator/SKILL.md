---
name: harness-pipeline-creator
description: Create, modify, and optimize Harness CI/CD YAML pipelines with comprehensive template design, schema validation, security best practices, and governance. Use when working with Harness pipelines, templates, CI/CD configurations, deployment stages, triggers (webhook, scheduled, artifact), or needing advanced validation patterns.
metadata:
  version: 2.3.0
  category: development
  tags: ci-cd, harness, pipelines, templates, security
  status: active
---

# Harness Pipeline Creator

Expert assistance in creating, modifying, and optimizing Harness CI/CD YAML pipelines with comprehensive template management, advanced schema validation, and security governance.

## Capabilities

- Create complete Harness pipeline YAML configurations with validation
- Design reusable templates (Step, Stage, Pipeline) with proper versioning
- Implement advanced schema validation rules and patterns
- Apply security-focused validation and governance
- Configure triggers (Webhook, Scheduled/Cron, Artifact)

## Pipeline Structure

```yaml
pipeline:
  name: "Pipeline Display Name"
  identifier: unique_identifier_no_spaces
  projectIdentifier: <project_id>
  orgIdentifier: <org_id>
  tags:
    team: owner_team
    environment: target_env
  variables:
    - name: var_name
      type: String
      default: "default_value"
      value: <+input>
  stages:
    - stage:
        # Stage configuration
```

## Template Types

### Step Templates
**Use for**: Reusable individual actions (build, test, deploy steps)

### Stage Templates
**Use for**: Complete workflow phases (CI stage, security stage, deployment stage)

### Pipeline Templates
**Use for**: Complete end-to-end workflows

## Naming Conventions

```yaml
# Template Hierarchy:
{purpose}_{type}_{version}
{team}_{purpose}_{type}_{version}

# Examples:
docker_build_step_v1
security_scan_stage_v2
api_deployment_pipeline_v1
```

## Schema Validation

```yaml
# Required input
parameter: <+input>.required()

# Optional with default
parameter: <+input>.default(defaultValue)

# Allowed values
environment: <+input>.allowedValues(dev,staging,prod).required()

# Regex validation
version: <+input>.regex(^v[0-9]+\.[0-9]+\.[0-9]+$).required()

# Security validation
password: <+input>.regex(^<\+secrets\.get\(.+\)>$).required()
```

## Versioning Strategy

```yaml
# MAJOR: Breaking changes to template interface
# MINOR: New features, backward compatible
# PATCH: Bug fixes, no interface changes
versionLabel: "v2.1.3"
```

## Stage Types

- **CI Stage**: Build/Test (`type: CI`)
- **CD Stage**: Deployment (`type: Deployment`)
- **Security Stage**: SAST/DAST scanning

## Triggers

| Type | Purpose | Example |
|------|---------|---------|
| Webhook | Event-driven from SCM | PR opened, push to main |
| Scheduled | Cron-based execution | Nightly security scans |
| Artifact | Container image updates | Auto-deploy on new tag |

## Common Step Types

- `BuildAndPushDockerRegistry`: Docker build & push
- `K8sRollingDeploy`: Kubernetes rolling deployment
- `Security`: Security scanning (SAST/DAST)
- `HelmDeploy`: Helm chart deployment
- `TerraformPlan`/`TerraformApply`: Infrastructure as Code
- `Http`: HTTP API calls
- `Policy`: Policy evaluation

## Security Best Practices

- No hardcoded secrets or credentials
- Use Harness secrets manager for sensitive data
- Trusted container images from approved registries
- Principle of least privilege for permissions
- Input validation and sanitization
- Audit logging for compliance

## Integration Points

- API Security Lint (Spectral for OpenAPI validation)
- SecDef (Security defect tracking)
- Traceable (API monitoring and testing)
- JFrog Xray (Dependency scanning)
- SonarQube (Code quality gates)
- Wiz (Cloud security scanning)

## Resources

- Harness Documentation: https://developer.harness.io/docs
- Community: https://community.harness.io

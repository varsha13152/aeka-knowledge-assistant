---
name: nuclei-template-creator
description: Create high-quality Nuclei security templates for vulnerability detection. This skill should be used when users want to create, review, or improve Nuclei YAML templates for scanning security vulnerabilities, misconfigurations, or exposures. Triggers include requests like "create a nuclei template", "write a detection for CVE-XXXX", "help me scan for [vulnerability]", or "review this nuclei template".
metadata:
  version: 1.0.0
  category: code-analysis
  tags: security, vulnerability-detection, nuclei, scanning
  status: active
---

# Nuclei Template Creator

## Overview

This skill enables creation of production-quality Nuclei security templates that detect vulnerabilities with minimal false positives. Nuclei templates are YAML-based definitions describing how to detect security issues across protocols like HTTP, DNS, TCP, and more.

## Template Creation Workflow

### Step 1: Research the Vulnerability

Before writing any template:
- Read the original vulnerability disclosure/advisory
- Understand the root cause and exploitation method
- Identify unique indicators that prove vulnerability exists
- Document vulnerable versions and affected components
- Find specific error messages, headers, or response patterns

### Step 2: Template Structure

Every template requires this structure:

```yaml
id: vendor-product-vulnerability-type

info:
  name: Vendor Product - Vulnerability Type
  author: template-author,vulnerability-discoverer
  severity: critical|high|medium|low|info
  description: |
    Clear explanation of what this template detects,
    including affected versions and components.
  reference:
    - https://nvd.nist.gov/vuln/detail/CVE-XXXX-XXXX
    - https://vendor-advisory-link
  classification:
    cvss-metrics: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
    cvss-score: 9.8
    cve-id: CVE-XXXX-XXXX
    cwe-id: CWE-XX
  metadata:
    verified: true
    shodan-query: 'relevant-shodan-query'
    fofa-query: 'relevant-fofa-query'
  tags: cve,cveYYYY,vuln-type,vendor,product

http:
  - method: GET
    path:
      - "{{BaseURL}}/vulnerable-endpoint"

    matchers-condition: and
    matchers:
      - type: word
        words:
          - "specific_vulnerability_indicator"
        part: body
      - type: status
        status:
          - 200
```

### Step 3: Write Effective Matchers

**Avoid weak matchers** - Generic patterns cause false positives:
```yaml
# BAD - matches many innocent systems
matchers:
  - type: word
    words:
      - "error"
      - "admin"
      - "login"
```

**Use multi-layer verification** - Combine application identification, version detection, and exploitation proof:

```yaml
# GOOD - specific and layered
matchers-condition: and
matchers:
  # Layer 1: Application identification
  - type: word
    words:
      - "VulnApp Management Console"
    part: body

  # Layer 2: Version detection
  - type: regex
    regex:
      - 'Version: ([0-2]\.[0-9]\.[0-9])'
    part: body

  # Layer 3: Exploitation proof
  - type: word
    words:
      - "INJECTION_SUCCESS_{{randstr}}"
    part: body
```

### Step 4: Severity Classification

| Severity | CVSS Score | Impact Examples |
|----------|------------|-----------------|
| Critical | 9.0-10.0 | RCE, full system compromise |
| High | 7.0-8.9 | Data breach, privilege escalation |
| Medium | 4.0-6.9 | Information disclosure, limited access |
| Low | 0.1-3.9 | Minor leakage, requires authentication |
| Info | N/A | Version detection, technology fingerprinting |

### Step 5: Validate and Test

```bash
# Validate YAML syntax
nuclei -validate -t template.yaml

# Test against vulnerable instance
nuclei -t template.yaml -target http://vulnerable.local -debug

# Test against patched/non-vulnerable systems (must NOT trigger)
nuclei -t template.yaml -target http://patched.local -debug
```

**Validation checklist:**
- [ ] Template detects vulnerability on vulnerable systems
- [ ] NO false positives on patched versions
- [ ] NO false positives on similar applications
- [ ] NO matches on generic error pages
- [ ] YAML syntax validates correctly
- [ ] All references are valid and accessible

## Quality Requirements

Templates must achieve:
- **False positive rate**: < 2%
- **Detection coverage**: > 95% on vulnerable instances
- **Metadata completeness**: 100% of required fields

**Required fields:**
- `id` - Descriptive, kebab-case (max 3-4 words)
- `info.name` - Format: "Vendor Product - Vulnerability Type"
- `info.author` - Credit template author AND vulnerability discoverer
- `info.severity` - Aligned with CVSS score
- `info.description` - Specific affected versions and components
- `info.reference` - At least one valid advisory link
- `info.tags` - Comprehensive, comma-separated

**For CVEs additionally require:**
- `classification.cve-id`
- `classification.cwe-id`
- `classification.cvss-metrics`
- `classification.cvss-score`

## Advanced Features

### Variables and Payloads
```yaml
variables:
  marker: "{{rand_base(8)}}"
  cmd: "id"

http:
  - method: POST
    path:
      - "{{BaseURL}}/execute"
    body: |
      command={{cmd}}; echo {{marker}}

    matchers:
      - type: word
        words:
          - "{{marker}}"
```

### Extractors
```yaml
extractors:
  - type: regex
    name: version
    regex:
      - 'Version: ([0-9\.]+)'
    group: 1
```

### DSL Conditions
```yaml
matchers:
  - type: dsl
    dsl:
      - 'status_code == 200'
      - 'contains(body, "vulnerable")'
      - 'len(body) > 100'
    condition: and
```

### Network Templates (Non-HTTP)
```yaml
network:
  - inputs:
      - data: "{{hex_decode('...')}}"
    host:
      - "{{Hostname}}"
    port: 8080

    matchers:
      - type: word
        words:
          - "VulnServer/1.0"
        part: data
```

## Resources

- **Official Docs**: https://docs.projectdiscovery.io/templates/introduction
- **HTTP Protocol**: https://docs.projectdiscovery.io/templates/protocols/http
- **Template Repository**: https://github.com/projectdiscovery/nuclei-templates

# Attribution

This plugin bundles skills and agent personas adapted from the open-source project [`addyosmani/agent-skills`](https://github.com/addyosmani/agent-skills), licensed under the MIT License.

The following components are taken (with edits where noted) from that project:

| Component | Source path in upstream |
| --- | --- |
| `skills/code-review-and-quality/` | `skills/code-review-and-quality/` |
| `skills/code-simplification/` | `skills/code-simplification/` |
| `skills/security-and-hardening/` | `skills/security-and-hardening/` |
| `skills/performance-optimization/` | `skills/performance-optimization/` |
| `skills/frontend-ui-engineering/` | `skills/frontend-ui-engineering/` |
| `agents/code-reviewer.md` | `agents/code-reviewer.md` |
| `agents/security-auditor.md` | `agents/security-auditor.md` |
| `agents/test-engineer.md` | `agents/test-engineer.md` |

The following are original to this plugin:

- `skills/review-frontend/SKILL.md` — thin orchestration skill that runs the five upstream review skills with PR / repo / file scope, frontend-aware file selection, deduplication of overlapping findings, and a consolidated severity-tagged report
- `README.md`, `INSTALL.md`, `NOTICE.md`

The upstream MIT License is included as `LICENSE`. The upstream copyright notice (Copyright (c) 2025 Addy Osmani) is preserved.

# pp-frontend-review

Staff-engineer code review for React, Next.js, and Node frontend repos. Bundles the **Review-phase quality-gate skills** from [`addyosmani/agent-skills`](https://github.com/addyosmani/agent-skills) (MIT-licensed) plus a `frontend-ui-engineering` correctness lens, three subagent personas, and a thin orchestrator that drives all of them with PR / repo / file scope.

The plugin enforces a single review standard across the team: every change is evaluated across correctness, readability/simplification, architecture, security, performance, and UI correctness, with severity-tagged findings and an explicit verdict.

**See it in action:** [Enhancing Frontend PR Reviews with pp-frontend-review](https://paypal.atlassian.net/wiki/x/LKhFrw) — three real PayPal PRs reviewed with the plugin alongside Claude's built-in `/review`, showing exactly what each side caught and missed.

## What you get

### Skills (6)

| Skill | Purpose |
| --- | --- |
| `code-review-and-quality` | Master five-axis review (correctness, readability, architecture, security, performance). Severity labels: Critical / Required / Optional / Nit / FYI. |
| `code-simplification` | Reduce complexity without changing behavior. Five principles, project-convention-aware. |
| `security-and-hardening` | OWASP-aligned security depth: input validation, secrets, auth, output encoding, untrusted data flow. |
| `performance-optimization` | Measure-before-optimize: N+1, unbounded loops, render hygiene, bundle/payload size, pagination. |
| `frontend-ui-engineering` | Is the UI written correctly? Component architecture, design system, state patterns, responsive, a11y, anti-AI-UI-smell. |
| `pp-react-suggestion` | Detects native HTML elements that have a pp-react replacement, and hardcoded values that map to pp-react design tokens. Driven by static reference maps that ship with the plugin. Default Optional, `PP_REACT_SUGGESTION_STRICT=true` for Required. |

### Orchestrator skill

| Skill | Purpose |
| --- | --- |
| `review-frontend` | Runs all six skills with PR / repo / file scope and emits a single consolidated severity-tagged report. Triggers on phrases like "review my PR", "audit this repo", "review components/X.tsx". |

### Agents (3)

| Agent | Purpose |
| --- | --- |
| `code-reviewer` | Staff-engineer review persona for thorough single-perspective review. |
| `security-auditor` | Security-focused subagent for vulnerability detection. |
| `test-engineer` | Test strategy and coverage subagent. |

## Severity model and merge gate

| Label | Meaning | Effect |
| --- | --- | --- |
| **Critical** | Security vuln, data loss, broken functionality, a11y blocker | **Blocks merge** |
| *(no prefix)* | Required change before merge | **Blocks merge** |
| **Optional / Consider** | Worth considering, not required | Advisory |
| **Nit** | Minor / style | Advisory |
| **FYI** | Informational | Advisory |

This matches the team's "blocking on critical issues" policy: any Critical or Required finding fails the review; everything else is advisory.

## Quick start

After installing the plugin (see `INSTALL.md`):

```
You: review my PR
Claude: [invokes review-frontend, detects branch diff vs main, runs the six skills, emits report]

You: audit the whole repo for frontend issues
Claude: [invokes review-frontend in repo scope]

You: review components/Checkout.tsx
Claude: [invokes review-frontend in file scope]
```

Or invoke a specific skill directly:

```
You: run a security review on app/api/users/route.ts
Claude: [invokes security-and-hardening directly]
```

## Detecting framework

The orchestrator reads `package.json`, the directory layout, and the lint config to detect:

- React version and rendering target
- Next.js App Router vs Pages Router (or hybrid)
- State and data libraries (React Query, SWR, Zustand, Redux, Jotai)
- Test stack (Vitest, Jest, Playwright, Cypress)
- Lint/TS config

The six skills then apply with the right framework lens. Plain Node services without a UI surface skip `frontend-ui-engineering` and `pp-react-suggestion` automatically.

## Verification step

When repo commands are available, the orchestrator runs them and includes results in the report:

- `npm run lint`
- `npm run typecheck` (or `tsc --noEmit`)
- `npm test --run`
- `npm run build`
- `npm audit --omit=dev`

Failures count as evidence backing the relevant findings.

## Standard practice rollout

1. **Install** for individuals (see `INSTALL.md`).
2. **Publish** to a private team marketplace and add to repo `.claude/settings.json` so all developers auto-load it on a frontend repo.
3. **Reference** in `CLAUDE.md` and `CONTRIBUTING.md` so the bar is documented.
4. **CI follow-up (later)** — wrap `review-frontend` in a GitHub Action that posts results as PR comments and fails the check on Critical / Required findings. Held for a future minor release.

## Attribution

Skills and agents are adapted from [`addyosmani/agent-skills`](https://github.com/addyosmani/agent-skills) under MIT. See `NOTICE.md` and `LICENSE`.

## Status

`v1.0.0` — first stable release. Six skills, three agents, orchestrator, static reference maps, real-PR documentation. See `CHANGELOG.md` for history.

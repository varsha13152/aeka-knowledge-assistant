---
name: review-frontend
description: >
  This skill should be used when the user asks to "review this frontend",
  "review the PR", "review my React/Next.js code", "review this repo",
  "run a quality gate", or any phrasing requesting a code review on a
  React, Next.js, or Node frontend codebase. Orchestrates the six review
  skills (code-review-and-quality, code-simplification,
  security-and-hardening, performance-optimization, frontend-ui-engineering,
  pp-react-suggestion) and produces a single consolidated, severity-tagged
  report. Supports PR-scope (branch diff), repo-scope (whole working tree),
  and file-scope (a specific file).
metadata:
  version: "1.0.0"
  category: orchestration
---

# Review Frontend

Orchestrate a staff-engineer-grade code review on a React, Next.js, or Node frontend codebase by sequentially applying the six review skills and consolidating findings into one report.

## When to invoke

Trigger when the user asks for a code review on a frontend codebase. Detect scope from the request:

- **PR scope** — phrases like "review this PR", "review the diff", "review my branch", "review against main". Default base branch is `main`. Falls back to `master` if `main` does not exist.
- **Repo scope** — phrases like "review the whole repo", "review the codebase", "audit this repo". Walks the working tree.
- **File scope** — phrases like "review this file", "review components/Foo.tsx". Limits to the named files.

If the user does not specify, ask once: "Review the current branch diff against `main`, the whole repo, or a specific file?"

## Process

Run these phases in order. Do not skip the verification step.

### Phase 1 — Determine scope and file set

1. **PR scope:**
   - Run: `git rev-parse --verify main >/dev/null 2>&1 && BASE=main || BASE=master`
   - Run: `git diff --name-only $BASE...HEAD`
   - Filter to frontend-relevant extensions: `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.css`, `.scss`, `.json` (only `package.json`, `next.config.*`, `tsconfig.json`, `.eslintrc*`, `tailwind.config.*`).
   - If the diff is empty, report "No frontend changes found between $BASE...HEAD" and stop.

2. **Repo scope:**
   - Walk the working tree. Skip `node_modules`, `.next`, `.turbo`, `dist`, `build`, `out`, `.git`, `coverage`, `.cache`, `storybook-static`.
   - Honor `.gitignore`.
   - If repo size is large (> 500 reviewable files), warn the user and offer: (a) review the top-level structure plus highest-risk areas (auth, route handlers, Server Actions, `next.config.*`, middleware), or (b) proceed in full, which may take many minutes.

3. **File scope:**
   - Read the files the user named.

### Phase 2 — Detect framework and project context

Identify what kind of frontend this is so the four review skills are applied with the right lens:

- Read `package.json`. Note `react`, `next`, `vite`, `remix`, `astro`, `preact`, `node` versions.
- Detect Next.js router: `app/` present → App Router; `pages/` present → Pages Router; both → hybrid.
- Note state libraries (`@tanstack/react-query`, `swr`, `zustand`, `redux`, `jotai`).
- Note test stack (`vitest`, `jest`, `playwright`, `cypress`).
- Note lint config (`eslint`, `@next/eslint-config-next`, `eslint-plugin-react`, `eslint-plugin-jsx-a11y`).
- Read `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `README.md` if present — capture project conventions.

This context shapes how the upstream skills evaluate findings.

### Phase 3 — Run the six review skills

Apply the six review skills in order. Each produces its own findings. Track each finding with: file path, line number, axis (correctness / readability / architecture / security / performance / simplification / ui-correctness), severity, and a concrete fix.

1. **`code-review-and-quality`** — five-axis review (correctness, readability, architecture, security, performance). Use this skill's review process and checklist as the master frame. Read tests first.

2. **`code-simplification`** — independent pass focused on complexity reduction without behavior change. Cross-reference with code-review-and-quality's readability findings; do not double-count.

3. **`security-and-hardening`** — security depth: input validation at boundaries, secret handling, auth/session, output encoding, dependency risk, untrusted data flow. Treat all external data as untrusted.

4. **`performance-optimization`** — performance depth: N+1, unbounded loops, hot-path allocations, render hygiene, bundle/payload size, missing pagination.

5. **`frontend-ui-engineering`** — "is the UI written correctly" lens: component architecture, design-system adherence, state management patterns, responsive design, accessibility (WCAG 2.1 AA), avoidance of generic AI-UI smell. Particularly important for repo-scope reviews to assess whether UI conventions are consistent.

6. **`pp-react-suggestion`** — pp-react-specific design-system pass. Detects native HTML interactive elements that have a pp-react replacement, plus hardcoded colors/spacing that map to pp-react design tokens. Driven by static reference maps shipped with the plugin (`references/component-map.md` and `references/token-map.md`). Default severity is Optional. Set `PP_REACT_SUGGESTION_STRICT=true` to elevate. Always-Required for broken-keyboard a11y (`<div onClick>`) and failing-contrast colors regardless of mode.

For React/Next.js specifically, apply the upstream skills with these sharpening lenses (these are conventions, not new rules — they tell the upstream skills where to look):

| Area | What to look for |
| --- | --- |
| React hooks | Hooks called conditionally, missing exhaustive deps, missing cleanup on subscriptions, mutating state |
| Re-render hygiene | Unmemoized context values, inline object/function props on memoized children, missing `key` props or index keys on reorderable lists |
| Accessibility | `<div onClick>` without role/keyboard, `<img>` / `<Image>` without `alt`, inputs without labels, focus management on dialogs |
| Next.js boundaries | Server-only code in client components, secrets passed as props, `'use client'` on layout root, server actions without input validation or auth |
| Caching | Mixed `cache: 'no-store'` and `revalidate`, missing `revalidatePath`/`revalidateTag` after mutation, default fetch on routes that need fresh data |
| Env exposure | `NEXT_PUBLIC_*` on values that should be server-only, `process.env.X` in client components without `NEXT_PUBLIC_` |
| CWV | Missing `width`/`height` or `fill` on `next/image` (CLS), `priority` overuse, web fonts not via `next/font`, render-blocking third-party scripts |

### Phase 4 — Run available local checks

Where possible, gather objective evidence to back findings. If the command is unavailable, note it and continue.

- `npm run lint --silent` (or `pnpm lint`, `yarn lint`)
- `npm run typecheck --silent` (or `tsc --noEmit`)
- `npm test --silent --run` (or equivalent)
- `npm run build` (catches RSC boundary errors and many config issues)
- `npm audit --omit=dev` (security)

Capture output. Treat failures as evidence, not noise.

### Phase 5 — Consolidate and emit the report

Before emitting the final report, **route findings without losing them**.

#### Routing rules

1. Group all findings from the six passes by `file:line`.

2. For each group, designate **one primary owner** using this specificity ladder:
   - **`security-and-hardening`** wins on security-axis findings.
   - **`frontend-ui-engineering`** wins on a11y, design system, UX state, responsive, state-management strategy, and AI-aesthetic findings.
   - **`pp-react-suggestion`** wins when a native element has a concrete pp-react replacement that resolves an a11y or design-system concern flagged by another skill (the suggestion is the actionable fix; cross-reference the original finding in the rationale).
   - **`code-simplification`** wins on complexity / nesting / naming findings.
   - **`performance-optimization`** wins on perf-axis findings *unless* security claimed the same line.
   - **`code-review-and-quality`** wins on correctness, architecture, and anything the others did not claim.

3. **Do not drop secondary flags.** When more than one skill flagged the same `file:line`:
   - Render the full finding once, in the section corresponding to the primary owner's severity (Critical / Required / Optional / Nit / FYI).
   - In each non-primary skill's "Notes from Skills" subsection, add a short cross-reference pointing to the primary entry, e.g. `→ ShieldApp.js:11 — see Critical Issues (security primary; perf cost noted in fix)`.

4. **Cross-list when severity warrants.** If a primary security or correctness finding *also* has a measurable performance cost (or vice versa), include a one-line entry in the secondary section's body (not just in Notes), referring back to the full finding. Rule of thumb: any time the recommended fix changes runtime behavior in a way the perf skill would have flagged independently — cross-list it.

5. **Severity disagreement** — if two skills disagree on severity for the same `file:line`, take the more severe label.

#### Output rules

- **Always render every "Notes from Skills" entry, even when the skill has no primary findings.** When a skill found nothing standalone but contributed to deferred findings elsewhere, list each cross-reference. When a skill found nothing at all, write `no findings`. Never write a misleading empty string that suggests the pass didn't run.
- **Performance, security, and a11y sections must never look silent when the corresponding pass flagged something.** If the pass surfaced any finding (even one that was deferred to another section's primary), the relevant Notes subsection MUST list it by `file:line` with a one-line summary and a "see X" pointer.

This keeps each pass's contribution visible. A reader scanning the Performance notes should never see an empty section when perf actually had findings.

Use the severity scheme from `code-review-and-quality`:

| Label | Meaning | Gate |
| --- | --- | --- |
| **Critical** | Must fix before merge — security vuln, data loss, broken functionality, accessibility blocker | Blocks |
| *(no prefix)* | Required change — wrong abstraction, missing test, poor error handling | Blocks |
| **Optional / Consider** | Worth considering, not required | Advisory |
| **Nit** | Minor / style | Advisory |
| **FYI** | Informational | Advisory |

Final verdict:

- **REQUEST CHANGES** if any Critical or unprefixed (Required) finding exists.
- **APPROVE** otherwise.

This matches the team's "blocking on critical issues" policy: Critical (and Required) findings gate merge; Optional / Nit / FYI are advisory.

## Output format

```markdown
# Frontend Review — <PR title | repo path | file>

**Scope:** <PR diff vs main | full repo | files: x.tsx, y.ts>
**Framework:** <e.g. Next.js 14 App Router, React 18>
**Files reviewed:** <count>

## Verdict
**REQUEST CHANGES** | **APPROVE**

## Critical Issues (must fix)
- `path/to/file.tsx:42` — [Description] — **Fix:** [concrete fix]

## Required Issues
- `path/to/file.tsx:118` — [Description] — **Fix:** [concrete fix]

## Optional / Consider
- `path/to/file.tsx:24` — [Description]

## Nit
- ...

## FYI
- ...

## What's Done Well
- [At least one positive observation, specific]

## Verification Story
- Lint: <pass | fail | not run> [details]
- Typecheck: <pass | fail | not run>
- Tests: <pass | fail | not run> [count]
- Build: <pass | fail | not run>
- npm audit: <clean | N high | N critical>

## Notes from Skills

For each skill, list (a) findings owned (already in the severity sections above) and (b) findings the skill flagged that were routed elsewhere via the dedup ladder. Never leave a subsection silent when the pass actually surfaced something.

- **code-review-and-quality** —
  - Owned: <list `file:line` entries with one-line summaries, or "no issues">
  - Cross-referenced elsewhere: <list deferred findings as `→ file:line — see [section] (primary: [skill])`, or "none">
- **code-simplification** —
  - Owned: ...
  - Cross-referenced elsewhere: ...
- **security-and-hardening** —
  - Owned: ...
  - Cross-referenced elsewhere: ...
- **performance-optimization** —
  - Owned: ...
  - Cross-referenced elsewhere: ...
- **frontend-ui-engineering** —
  - Owned: ...
  - Cross-referenced elsewhere: ...
```

## Subagent delegation (optional, large reviews)

For repo-scope reviews on large codebases, delegate to subagents in parallel:

- `code-reviewer` agent — runs `code-review-and-quality` and `code-simplification` together
- `security-auditor` agent — runs `security-and-hardening`
- For test gaps surfaced during review, optionally invoke `test-engineer` agent

The agents return their reports; this skill consolidates them into the final output above.

## Anti-rationalization

Do not let any of these excuses skip a finding the upstream skills would flag:

- "It's just internal code." Internal code ships to users via dependencies.
- "We'll fix it later." Later rarely comes; this skill is the gate.
- "Tests pass." Tests don't catch architecture, accessibility, or re-render bugs.
- "It's a small PR." Small PRs hide critical issues all the time.

## Related skills

- `code-review-and-quality` — the five-axis review framework this skill invokes.
- `code-simplification` — complexity reduction without behavior change.
- `security-and-hardening` — security depth, OWASP-aligned.
- `performance-optimization` — perf depth, profiling-first.
- `frontend-ui-engineering` — UI correctness, design-system adherence, a11y.
- `pp-react-suggestion` — pp-react component and token suggestions, MCP-backed.

## Related agents

- `code-reviewer` — staff-engineer code review persona.
- `security-auditor` — security-focused review persona.
- `test-engineer` — test strategy and coverage persona.

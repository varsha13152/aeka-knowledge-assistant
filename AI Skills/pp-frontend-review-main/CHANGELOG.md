# Changelog

All notable changes to this plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-05-08

### Released

- **First stable release.** The plugin has been used internally on real PayPal frontend repos (`boaiconsolenodeweb`, `scmlimitationnodeweb`) and produced verified findings the standard `/review` missed. Six skills, three subagent personas, the orchestrator, the static reference maps, and the documentation are all in scope.
- **API contract.** The plugin's skill names, severity model (Critical / Required / Optional / Nit / FYI), and orchestration phases are stable. Future minor versions may add skills, refine reference maps, and improve detection without breaking these names. Major versions will be reserved for breaking changes (e.g., changing severity labels, removing a skill, restructuring the marketplace schema).
- **No breaking changes from 0.1.3.** This is a confidence-level bump, not a structural one. Teams that pinned to `0.1.3` can move to `1.0.0` with no migration.

## [0.1.3] — 2026-05-08

### Added

- **`pp-react-suggestion` skill.** New sixth pass in the orchestration. Detects native HTML interactive elements (`<button>`, `<input>`, `<select>`, `<div onClick>`, etc.) that have a pp-react component replacement, plus hardcoded color/spacing values that map to pp-react design tokens.

- **Strict mode via `PP_REACT_SUGGESTION_STRICT=true`.** Default keeps most pp-react suggestions Optional. Strict mode elevates them to Required. Two cases stay Required regardless of mode: broken keyboard accessibility (`<div onClick>` without role/tabIndex/onKeyDown) and colors that fail WCAG AA contrast.

- **`// pp-react-skip` line comment.** Suppresses pp-react-suggestion findings on the line below, with optional reason. For deliberate native-element use cases that aren't oversights.

- **Static reference maps.** `skills/pp-react-suggestion/references/component-map.md` and `references/token-map.md` are the single source of truth for native-to-pp-react translations and PayPal-standard tokens. Updated on each plugin release.

### Changed

- `review-frontend` orchestrator now invokes six passes instead of five. Phase 5 dedup ladder includes `pp-react-suggestion` as the owner when a native-to-pp-react swap resolves another skill's finding (the suggestion is the concrete fix; the original finding becomes a cross-reference).

### Notes

- The skill is intentionally static-map-driven for this release. Live MCP integration with `@paypalcorp/pp-react-mcp-server` and `@paypalcorp/pp-react-tokens-mcp-server` is a candidate for a future minor release once the static maps prove their value. Static-mode suggestions cover the common cases reviewers care about (component name, import path, broken-a11y findings, contrast checks) without the install friction of bundled MCP dependencies.

## [0.1.2] — 2026-05-06

### Added

- **`marketplace.json`** at `.claude-plugin/marketplace.json` so the repo can be registered as a Claude marketplace at PayPal. Schema matches the PayPal pattern (PPCN Claude Plugins LLD, Confluence page 2754748236) with `name`, `owner`, `description`, and `plugins[]`. The single plugin entry points to `./` since the repo *is* the plugin.

### Why

Teammates can now install with one command instead of pointing at a `.plugin` zip:

```
claude plugin marketplace add git+ssh://git@github.paypal.com/<your-team>/pp-frontend-review.git
claude plugin install pp-frontend-review@pp-frontend-review
```

## [0.1.1] — 2026-05-06

### Changed

- **Phase 5 of `review-frontend` no longer drops deduped findings.** The orchestrator now designates a primary owner per `file:line` but retains every secondary flag as a cross-reference, so the Performance, Security, and Accessibility subsections never look silent when their pass actually surfaced something.
- **Cross-listing rule added.** When a primary security or correctness finding has measurable performance cost, the perf section gets a one-line entry pointing back to the primary, instead of swallowing the perf framing.
- **Output template expanded.** "Notes from Skills" now uses explicit `Owned:` and `Cross-referenced elsewhere:` lines per skill, making each pass's contribution visible at a glance.

### Why

A real review run on a Redux frontend folder had four security/correctness findings that *also* carried perf consequences. The v0.1.0 dedup ladder routed them all to security or code-review-and-quality, leaving the Performance section visually empty. Reviewers reading the report could reasonably conclude perf had nothing to say. v0.1.1 fixes that.

## [0.1.0] — 2026-05-06

### Added

- Initial release.
- Five upstream review skills bundled from [`addyosmani/agent-skills`](https://github.com/addyosmani/agent-skills) (MIT-licensed):
  - `code-review-and-quality` — five-axis staff-engineer review framework.
  - `code-simplification` — complexity reduction without behavior change.
  - `security-and-hardening` — OWASP-aligned security depth.
  - `performance-optimization` — measure-first performance review.
  - `frontend-ui-engineering` — UI correctness, design-system adherence, accessibility.
- Three subagent personas: `code-reviewer`, `security-auditor`, `test-engineer`.
- New `review-frontend` orchestrator that runs all five skills with PR / repo / file scope, applies a dedup ladder per `file:line`, and emits a single severity-tagged report (Critical / Required / Optional / Nit / FYI).
- Frontend-aware file selection: skips `node_modules`, `.next`, `dist`, build artifacts; honors `.gitignore`.
- Framework detection: React, Next.js (App / Pages / hybrid), Vite, Remix, Astro; identifies state libraries (React Query, SWR, Zustand, Redux, Jotai) and test stack.
- Verification-pass integration: runs `lint`, `typecheck`, `test`, `build`, and `npm audit --omit=dev` when available, attaches results to the report.
- Scope statement in `frontend-ui-engineering/SKILL.md` declaring its non-overlapping turf (a11y, design system, UX states, responsive, state-management strategy, AI-aesthetic, file colocation) so the four other skills don't double-flag.
- README, INSTALL guide, NOTICE for upstream attribution.
- MIT license preserved from upstream.

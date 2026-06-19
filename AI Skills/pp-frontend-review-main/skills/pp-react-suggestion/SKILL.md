---
name: pp-react-suggestion
description: >
  This skill should be used when reviewing React/Next.js code at PayPal to
  suggest pp-react component replacements for native HTML elements and
  pp-react design tokens for hardcoded color/spacing/typography values.
  Trigger on `.tsx`, `.jsx`, `.ts`, `.js`, `.css`, `.scss`, `.module.css`
  files. Driven by static reference maps that ship with the plugin.
metadata:
  version: "1.0.0"
  category: review
---

# pp-react Suggestion

Find places where the team's design system would have done a better job than the native HTML or hardcoded value. Suggest the specific pp-react component or design token to swap in. Driven by static reference maps that ship with the plugin and are updated on each release.

## When to invoke

Trigger on these file types when reviewing React/Next.js code:

- `.tsx`, `.jsx` — JSX files that may contain native HTML interactive elements
- `.ts`, `.js` — files that may contain JSX (legacy components, test files mixed with components)
- `.css`, `.scss`, `.module.css` — stylesheets that may contain hardcoded values

Skip on pure server-side TypeScript (no JSX) and on test files.

When run as part of `review-frontend` orchestration, this skill emits findings into the consolidated report. It can also be invoked directly: "suggest pp-react components for components/Foo.tsx".

## Strictness mode

Default: most findings are Optional. Run with `PP_REACT_SUGGESTION_STRICT=true` in the environment to elevate eligible findings to Required.

| Pattern | Default mode | Strict mode |
|---|---|---|
| `<div onClick>` / `<span onClick>` (broken keyboard a11y) | Required | Required |
| Color that fails WCAG AA contrast against its background | Required | Required |
| Native `<button>`, `<input>`, `<select>`, `<textarea>`, `<dialog>` on **new** lines in a PR | Optional | Required |
| Native interactive on **existing** unchanged lines | FYI | Optional |
| Hardcoded brand color where a token exists | Optional | Required |
| Hardcoded spacing/font-weight/size where a token exists | Optional | Optional |
| Native `<a href>`, `<h1>`-`<h6>`, `<p>`, `<table>`, `<img>` | FYI | Optional |

The two always-Required cases are non-negotiable: broken keyboard accessibility and failing-contrast colors are real WCAG violations regardless of mode.

## Process

### Phase 1 — Read inputs

1. Read the target file(s).
2. If invoked with PR scope, read the diff so legacy lines can be down-graded to FYI.
3. Read the file's existing imports. Note which pp-react components are already in use.
4. Load `references/component-map.md` and `references/token-map.md` for the suggestion lookups.

### Phase 2 — Detect native HTML in JSX

Walk the JSX. Flag any lowercase-starting tag from the list in `references/component-map.md` when it has interactive intent or content semantics. Skip if the same tag is already wrapped in (or is itself) a pp-react component on the same line.

The component map covers:

- Form controls: `<button>`, `<input>` (multiple types), `<textarea>`, `<select>`
- Interactive non-form: `<div onClick>`, `<span onClick>`, `<a href>`, `<a onClick>`
- Composite UI: `<dialog>`, `<table>`, `<details>`, tab patterns
- Typography: `<h1>` through `<h6>`, `<p>`
- Layout suggestions: when to use `Container/Row/Col`, `Card`, `Pill`, `Badge`

For each match, look up the pp-react replacement in the map and emit the finding with:

1. The native pattern (one short snippet).
2. The pp-react component name.
3. The exact import statement from the map.
4. The rationale (a11y, design-system consistency, contrast, etc.).
5. Severity per the strictness table above.

### Phase 3 — Detect hardcoded values in stylesheets

Walk CSS, SCSS, CSS modules, and styled-components blocks. Flag:

1. **Hex colors** matching the `#[0-9a-fA-F]{3,8}` pattern.
2. **Named colors** other than `transparent`, `currentColor`, and `inherit`.
3. **rgba / hsl literals** with explicit alpha.
4. **Magic font-weights** that are non-standard (anything other than 100, 200, ..., 900).
5. **Magic spacing values** that don't appear in the project's spacing scale.

Look up each value in `references/token-map.md`. If a token match exists, suggest the swap. If no match, the value is either a one-off (note as FYI) or a candidate for adding to the design system (note in a "Design System Gaps" subsection).

For colors, also check WCAG AA contrast against the most likely background. If the file context suggests a background color, compute the ratio. If contrast fails (< 4.5:1 for normal text, < 3:1 for large text), elevate the finding to Required.

### Phase 4 — JSX context check (avoid false positives)

Before flagging a `<div onClick>` style finding as Required, verify the consumer side:

1. The native element does **not** carry `role="button"` plus `tabIndex` plus `onKeyDown` (if all three are present, keyboard a11y is already handled and the finding becomes FYI for design-system consistency).
2. The class applied to the element is on a **native element** (lowercase tag), not on a pp-react component (capitalized). If on a pp-react component, the component handles its own focus and the suggestion does not apply.
3. The project's global stylesheets do **not** preserve default browser focus indicators. If the global CSS keeps the default outline, missing `:focus-visible` is a softer concern.

If any of these checks soften the verdict, note the check in the rationale: "JSX context check confirmed/disconfirmed."

### Phase 5 — Emit findings

Each finding includes:

1. `file:line` reference.
2. The native pattern (one short snippet).
3. The pp-react replacement, including the exact import statement.
4. The rationale.
5. Severity per the strictness table.

Group findings by severity, the same as the orchestrator's output format.

When run as part of `review-frontend`, this skill defers to the orchestrator's deduplication rules. If `frontend-ui-engineering` flagged the same `<div onClick>` for missing keyboard support, this skill's finding is the **resolution** for that gap. Mark the cross-reference clearly:

```
Required
  FinancialHighlights.js:38  <div onClick> "View all" trigger has no keyboard
                             support (caught by frontend-ui-engineering on this
                             same line). pp-react ships <Button buttonType="text">
                             which handles role, tabIndex, focus ring, and
                             design-system styling.

                             import { Button } from "@paypalcorp/pp-react";

                             <Button buttonType="text" onClick={...}>View all</Button>
```

Two findings collapse into one actionable fix.

## What this skill does NOT do

1. **Refactor for you.** The skill suggests, the developer applies. Judgment, not patching.
2. **Flag every native element on legacy files.** PR-scope down-grades existing native usage to FYI. Strict mode opts in to flagging more aggressively.
3. **Replace the design-system review.** This skill complements `frontend-ui-engineering`. It does not duplicate the broader design-system audit (typography hierarchy, spacing scale, AI-aesthetic checks).
4. **Validate every prop.** The static map gives the component name and import path. Detailed prop signatures are the developer's responsibility at fix time.

## Anti-rationalization

Do not skip a finding because:

- "It's just one button." Inconsistent component choice across a codebase compounds.
- "We use native because pp-react's Button doesn't fit." If true, comment why with `// pp-react-skip: <reason>`. Without the comment it reads as oversight.
- "This is legacy code we are not refactoring." PR-scope already down-grades legacy lines. The remaining findings are on lines the current PR is touching.

## Configuration

The skill respects two environment variables and one inline override:

| Knob | Default | Effect |
|---|---|---|
| `PP_REACT_SUGGESTION_STRICT` | unset | When `true`, elevate Optional findings to Required for new code |
| `PP_REACT_SKIP_LEGACY` | `true` | When `true`, down-grade unchanged-line findings to FYI in PR scope |
| `// pp-react-skip` line comment | n/a | Suppresses any finding on the line below, with optional reason |

Document strict mode in the team's onboarding doc so contributors know when their PR will block on Required findings.

## Maintenance

The static maps in `references/` are the single source of truth. Update them on every plugin release as pp-react adds, deprecates, or moves components. The maintenance overhead is small (typically a few entries per release) and worth the lower install friction.

A future minor release may add optional integration with the live `@paypalcorp/pp-react-mcp-server` and `@paypalcorp/pp-react-tokens-mcp-server` MCPs for teams that want always-current suggestions. That will be additive, not a replacement.

## References

- `references/component-map.md` — native HTML to pp-react component map. Single source of truth for Phase 2 lookups.
- `references/token-map.md` — hardcoded values to pp-react design token map. Single source of truth for Phase 3 lookups.
- pp-react docs: `https://github.paypal.com/pages/PayPal-UI-R/pp-react/v8.x/`

# Static fallback: native HTML to pp-react component map

Use this map only when the pp-react component MCP is unreachable. Mark the report's "Verification Story" as "MCP unavailable, used static fallback" so reviewers know the suggestions may be stale relative to the current catalog.

## Form controls

| Native | pp-react component | Import | Why |
|---|---|---|---|
| `<button>` | `Button` | `import { Button } from "@paypalcorp/pp-react";` | Variants (`primary`, `secondary`, `tertiary`, `text`), sizes, loading state, focus indicator |
| `<button type="submit">` inside form | `Button` with `type="submit"` | same | Same plus correct submit semantics |
| `<input type="text|email|password">` | `TextInput` | `import { TextInput } from "@paypalcorp/pp-react";` | Label association, error helper text, controlled value |
| `<input type="number">` | `TextInput` with `type="number"` | same | Numeric input handling |
| `<input type="checkbox">` | `Checkbox` | `import { Checkbox } from "@paypalcorp/pp-react";` | Label association, indeterminate state |
| `<input type="radio">` | `RadioButton` | `import { RadioButton } from "@paypalcorp/pp-react";` | Group semantics |
| `<textarea>` | `TextArea` | `import { TextArea } from "@paypalcorp/pp-react-text-area";` | Auto-resize, character count |
| `<select>` | `DropdownMenu` | `import { DropdownMenu } from "@paypalcorp/pp-react";` | Keyboard navigation, option list a11y |

## Interactive non-form

| Native | pp-react component | Import | Why |
|---|---|---|---|
| `<div onClick>` (interactive) | `Button` or `IconButton` | `import { Button, IconButton } from "@paypalcorp/pp-react";` | Real keyboard a11y. Required swap. |
| `<span onClick>` (interactive) | `Button buttonType="text"` | same | Same as above |
| `<a href>` (text link) | `Link` | `import { Link } from "@paypalcorp/pp-react";` | Inverse styling, focus ring, design-token color |
| `<a onClick>` (no href, acts as button) | `Button buttonType="text"` | same | Real button semantics |
| `<a href="#">` placeholder | `Button buttonType="text"` | same | `#` href is an a11y smell |

## Composite UI

| Native | pp-react component | Import | Why |
|---|---|---|---|
| `<dialog>` or modal `<div>` | `Dialog` | `import { Dialog } from "@paypalcorp/pp-react";` | Focus trap, Escape handling, focus restoration |
| `<table>` for data | `DataTable` | `import { DataTable } from "@paypalcorp/pp-react-data-table";` | Sort, pagination, keyboard nav, loading/empty/error states |
| `<details>` / `<summary>` | `Accordion` / `AccordionRow` | `import { Accordion, AccordionRow } from "@paypalcorp/pp-react-accordion";` | Animation, ARIA, controlled state |
| Tab patterns (custom) | `Tabs`, `TabPanel` | `import { Tabs, TabPanel } from "@paypalcorp/pp-react";` | Keyboard nav, ARIA tablist |

## Typography

| Native | pp-react component | Import | Why |
|---|---|---|---|
| `<h1>` | `HeadingText size="xl"` | `import { HeadingText } from "@paypalcorp/pp-react";` | Type scale, brand fonts |
| `<h2>` | `HeadingText size="lg"` | same | Same |
| `<h3>` through `<h6>` | `HeadingText size="md|sm"` | same | Same |
| `<p>` body copy | `BodyText size="default|lg"` | `import { BodyText } from "@paypalcorp/pp-react";` | Type scale, brand fonts |

`HeadingText` and `BodyText` do NOT forward `className`. If you need a wrapper class, wrap in a `<div>` outside the component.

## Layout

Native `<div>` for layout is fine. Don't flag layout `<div>`s unless they have `onClick` or other interactive intent.

For consistent layouts, suggest:

| Need | pp-react | Import |
|---|---|---|
| Bootstrap-style grid | `Container`, `Row`, `Col` | `import { Container, Row, Col } from "@paypalcorp/pp-react";` |
| Card surface | `Card` | `import { Card } from "@paypalcorp/pp-react";` |
| Pill / chip | `Pill`, `PillTray` | `import { Pill, PillTray } from "@paypalcorp/pp-react-pill";` |
| Status badge | `Badge` | `import { Badge } from "@paypalcorp/pp-react";` |

## Icons and media

| Native | pp-react component | Import | Why |
|---|---|---|---|
| Inline `<svg>` icon | `pp-react-icons` named import | `import { CheckIcon } from "@paypalcorp/pp-react-icons";` | Consistent sizing, color, accessibility |
| `<img>` for content | Verify `alt` is present and descriptive. No native pp-react replacement; the project pattern is `next/image` for optimization |
| `<img>` for decoration | `<img alt="">` is correct |

## Notes on accuracy

This static map is a snapshot. The live MCP is authoritative. Components may be added, deprecated, or moved between sub-packages (e.g., `@paypalcorp/pp-react-text-area`, `@paypalcorp/pp-react-pill`, `@paypalcorp/pp-react-data-table`) over time.

When the MCP is reachable, prefer the MCP's `get_imports` response over this file's import paths.

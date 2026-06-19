# Static fallback: hardcoded values to pp-react design tokens

Use this map only when the pp-react tokens MCP is unreachable. Mark the report's "Verification Story" accordingly.

## Color tokens (commonly seen in PayPal codebases)

| Hardcoded value | Likely token | CSS variable |
|---|---|---|
| `#003087` | PayPal primary blue | `--pp-blue-primary` |
| `#0070e0` or `#0070f3` | PayPal action / link blue | `--pp-action-bg` |
| `#1546a0` | Active link / pressed primary | `--pp-blue-active` |
| `#001435` | Primary text / navy | `--pp-text-primary` |
| `#6b6b80` | Secondary text | `--pp-text-secondary` |
| `#9b9baf` | Muted text | `--pp-text-muted` |
| `#dbd8d0` | Stone border | `--pp-border` |
| `#f1efea` | Page background | `--pp-bg-page` |
| `#007a4d` | Success green | `--pp-success` |
| `#b45309` | Warning amber | `--pp-warning` |
| `#c5281c`, `#E02D50` | Danger red | `--pp-danger` |
| `#ffffff` | White (header foreground) | `--pp-text-on-dark` if defined, else `#ffffff` |
| `grey`, `gray`, `#808080` | Text secondary or muted | `--pp-text-secondary` or `--pp-text-muted` |

If the live tokens MCP is unreachable, query `app/_styles/tokens.css` (or the project's tokens file) for the actual variable names. Names vary by project; the values above are PayPal-standard.

## Spacing scale

PayPal projects typically use a 0.25rem-based scale. Common values:

| Hardcoded value | Suggested token |
|---|---|
| `4px`, `0.25rem` | `--pp-space-xs` (or `0.25rem` if no token) |
| `8px`, `0.5rem` | `--pp-space-sm` |
| `12px`, `0.75rem` | `--pp-space-md` |
| `16px`, `1rem` | `--pp-space-lg` |
| `24px`, `1.5rem` | `--pp-space-xl` |
| `32px`, `2rem` | `--pp-space-2xl` |

Flag any pixel value that is not on the 4-pixel scale (e.g., `5px`, `7px`, `13px`) as a magic value worth a token or a re-evaluation.

## Font weights

| Hardcoded value | Suggested |
|---|---|
| `400` | Regular (default) |
| `500` | Medium |
| `600` | Semibold |
| `700` | Bold |
| `750`, `850` | **Non-standard.** Round to the nearest 100. Some fonts will not have these weights. |

## Font sizes

PayPal projects typically use a `rem`-based type scale. Common values:

| Hardcoded value | Suggested token |
|---|---|
| `0.6875rem` (11px) | Below the small-text minimum. Verify intent. |
| `0.75rem` (12px) | `--pp-text-sm` (small text minimum) |
| `0.875rem` (14px) | `--pp-text-md` (default body) |
| `1rem` (16px) | `--pp-text-lg` |
| `1.125rem` and up | `HeadingText` component, not raw rem |

## Shadows

| Hardcoded value | Suggested |
|---|---|
| `box-shadow: 0 0.5rem 1.5rem rgba(0, 0, 0, 0.12)` | `--pp-shadow-md` |
| `box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1)` | `--pp-shadow-sm` |
| Heavier shadows | Likely AI-aesthetic smell. See `frontend-ui-engineering`'s anti-AI-aesthetic checks. |

## Notes on accuracy

This static map reflects PayPal-standard values. Project-specific token names are defined in each project's tokens stylesheet (commonly `app/_styles/tokens.css` or `tokens.css` at root).

When the tokens MCP is reachable, prefer its response. The MCP can resolve color values to tokens by exact-match or fuzzy search and returns the canonical token name plus any aliases.

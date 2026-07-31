# Design — Torii Run Console

Adapted from Impeccable **Neo kinpaku** (`/tmp/impeccable/DESIGN.md`) for an **Operate** product surface.

## Direction

Dark warm lacquer. Kinpaku gold for primary actions and focus. Verdigris for success/approve. Vermilion for request-changes and critical findings. No purple gradients, no glass stacks.

## Tokens (CSS variables in `src/styles.css`)

| Role | Token | Value |
|------|-------|--------|
| Page ground | `--lacquer` | `oklch(7% 0.006 95)` |
| Panel | `--raised` | `oklch(11% 0.006 95)` |
| Accent | `--gold` | `oklch(84% 0.19 80.46)` |
| Success / approve | `--patina` | `oklch(70% 0.12 188)` |
| Danger | `--vermilion` | `oklch(58% 0.15 35)` |
| Body text | `--champagne` | `oklch(91% 0 0)` |
| Muted | `--muted` | `oklch(72% 0 0)` |

## Type

- **UI / body:** Albert Sans (product one-family)
- **Wordmark / display moments:** Alumni Sans, tracking open
- Fixed rem ramp 11–20 for product chrome (no fluid hero type)

## Layout

- Top run identity strip (trace, host, model, elapsed)
- Left rail tabs (not card grids)
- Main: single content column with sparse panels (not nested cards)
- Tables for findings and stages; mono only for IDs and code/diff

## Bans (Impeccable craft floor)

No Inter default, no gray-on-color, no pure black, no nested cards, no bounce easing, no emoji as icons.

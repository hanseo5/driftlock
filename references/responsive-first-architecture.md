# Responsive-First Architecture

## Why This Exists

Responsive quality was previously treated as a late visual QA repair loop. That
made every web preview slow: generate desktop, inspect mobile, patch overflow,
repeat. Lodestar now treats responsive behavior as a first-class contract before
final UI/UX approval.

## Research Basis

- MDN describes responsive design as an approach that works across screen sizes,
  resolutions, and devices, using flexible layouts, media queries, responsive
  media, and the viewport meta tag.
- MDN container queries let components adapt to their container instead of only
  the global viewport.
- web.dev frames responsive design as changing layout for user needs and device
  capabilities, for example one column on phones, two on tablets, and more on
  desktop.
- WCAG 2.2 reflow requires content to work at 320 CSS pixels without two-way
  scrolling, except for content that genuinely needs two-dimensional layout.
- NN/g emphasizes one cohesive responsive experience across devices, with
  content priority adapted to context.

## Architecture Rule

Every browser-rendered web preview must produce:

- `browser-evidence-mobile.json`
- `browser-evidence-tablet.json`
- `browser-evidence.json` for desktop
- `responsive-matrix.json`
- `visual-qa.md`

Final UI/UX approval is blocked until the matrix and visual QA pass.

## Fast Path

Use this command pattern instead of manually reasoning about every viewport:

```text
python scripts/lodestar.py browser-collect --viewport mobile --html shape.html --expect-text "<key text>" --screenshot shape-mobile.png --out browser-evidence-mobile.json
python scripts/lodestar.py browser-collect --viewport tablet --html shape.html --expect-text "<key text>" --screenshot shape-tablet.png --out browser-evidence-tablet.json
python scripts/lodestar.py browser-collect --viewport desktop --html shape.html --expect-text "<key text>" --screenshot shape-desktop.png --out browser-evidence.json
python scripts/lodestar.py responsive-matrix --mobile browser-evidence-mobile.json --tablet browser-evidence-tablet.json --desktop browser-evidence.json --require-screenshots --out responsive-matrix.json
python scripts/lodestar.py design-gate --design DESIGN.md --shape shape.html --visual-qa visual-qa.md --responsive-matrix responsive-matrix.json --require-visual-qa --require-responsive-matrix
```

## Generation Rules

- Start with a fluid/mobile-safe shell, then enhance tablet and desktop.
- Use `grid-template-columns: repeat(auto-fit, minmax(...))` for repeated
  cards when possible.
- Use stable component dimensions for buttons, cards, tables, nav, and toolbars.
- Use horizontal scrolling only for deliberate nav rails or true two-dimensional
  content.
- Convert dense desktop tables into mobile cards or summary rows.
- Prefer component/container adaptation before page-wide breakpoint patches.
- Keep key actions visible and tappable on all three viewport classes.
- Treat clipped hero copy, cut-off buttons, and hidden commerce actions as gate
  failures, not polish requests.


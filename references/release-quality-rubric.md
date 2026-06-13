# Release Quality Rubric

This rubric blocks previews that look like a rough MVP, generic dashboard, or
style exercise instead of a product the user can confidently approve.

## Required Design Inputs

Every UI product must define these before the final UI/UX preview:

- Product archetype: native app, operational SaaS, marketplace, editor, game,
  content site, commerce, or another concrete category.
- Benchmark bar: 2-3 named products or design systems that set the quality
  target. Benchmarks are used for density, hierarchy, interaction patterns, and
  polish, not for copying brand assets.
- Design acceptance criteria: concrete pass/fail checks for first impression,
  information hierarchy, component fidelity, interaction states, data realism,
  accessibility baseline, and responsive behavior.
- Responsive contract: mobile, tablet, and desktop viewport behavior, including
  320 CSS px reflow, content priority changes, and component-level adaptation
  rules.
- Anti-slop constraints: explicit things the preview must avoid for this
  product type.

## Release Quality Checks

The final `shape.html` must pass all of these before user approval:

- **First Screen Decision Speed**: within 3 seconds, a user can tell what the
  product does, what matters now, and what action they can take.
- **Benchmark Fit**: layout density, typography, controls, and states are
  plausibly in the same quality band as the chosen benchmarks.
- **Information Architecture**: navigation, hierarchy, empty/error/loading
  expectations, and primary workflow are visible or clearly implied.
- **Component Fidelity**: buttons, tables, cards, forms, charts, tab bars, and
  detail panes have production-like dimensions, states, labels, and spacing.
- **Data Realism**: sample data looks domain-specific, varied, and operational;
  no placeholder copy, lorem ipsum, fake metrics without context, or toy data.
- **Platform Fit**: iOS, Android, web SaaS, desktop, or game conventions are
  followed instead of defaulting to generic web cards.
- **Visual Craft**: type scale, alignment, color roles, rhythm, and whitespace
  are deliberate. Text must not overlap, clip, or wrap awkwardly in key controls.
- **Responsive Matrix**: mobile, tablet, and desktop must each preserve the
  primary workflow with no horizontal overflow, clipped key copy, unreadable
  controls, or hidden commerce/product actions. Components should adapt to
  their container before page-level breakpoints are added.
- **No MVP Tells**: no wireframe labels, "placeholder", "MVP", generic hero
  slogans, four tiny static mockups, random gradients, or decorative filler.

## Visual QA Loop

Before final UI/UX approval:

1. Open the final preview locally.
2. Capture or collect browser evidence for mobile, tablet, and desktop.
3. Write `responsive-matrix.json` from the three viewport evidence files.
4. Inspect screenshots against the release checks.
5. Fix visible issues and repeat until the matrix passes.
6. Save `visual-qa.md` with screenshot paths, failures found, fixes made,
   mobile/tablet/desktop results, and final pass/fail result.

If the preview fails the rubric, route back to the design system or shape step.

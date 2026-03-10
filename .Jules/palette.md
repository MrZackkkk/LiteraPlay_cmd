## 2026-03-10 - Missing Focus Outlines

**Learning:** When reviewing the CSS styles in `src/literaplay/ui/style.css`, there are no general `:focus` or `:focus-visible` styles for interactive elements, besides one definition for `.input-group input:focus`. Buttons do not have a visual focus indicator for keyboard navigation, making it inaccessible for keyboard users.

**Action:** I will add a general `:focus-visible` style for interactive elements, prioritizing `button` tags and `.btn-*` classes, reusing existing design tokens such as `var(--accent)`.
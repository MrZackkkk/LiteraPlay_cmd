## 2026-03-07 - Keyboard Accessibility & Focus States
**Learning:** Custom UI components like div-based dropdowns lose native keyboard accessibility and need explicit `tabindex`, keyboard event handlers (Enter/Space), and ARIA roles to be usable by keyboard users. Also, custom design systems often omit `:focus-visible` styles, rendering keyboard navigation invisible.
**Action:** Always verify keyboard navigation (Tab, Enter) on custom interactive elements, and establish a global `:focus-visible` pattern early in the design system.

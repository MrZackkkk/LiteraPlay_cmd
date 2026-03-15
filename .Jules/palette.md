## 2024-05-18 - Restoring Focus Outlines on Composite Input Containers
**Learning:** When removing native outlines from input fields (`outline: none`) that are inside styled composite containers (like `.glass-input`), keyboard accessibility is severely impacted because the user loses visible focus indication.
**Action:** Always add `:focus-within` styling to the parent container to restore visible focus indication for keyboard accessibility.

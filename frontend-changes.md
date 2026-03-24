# Frontend Changes

## Code Quality Tooling

### Added Files

**`frontend/package.json`**
- Introduces npm-based dev tooling for the frontend
- Adds `prettier` (^3.4.0) as a dev dependency
- Defines three npm scripts:
  - `npm run format` — auto-format all JS, CSS, and HTML files in-place
  - `npm run format:check` — check formatting without modifying files (CI-friendly)
  - `npm run quality` — alias for `format:check`

**`frontend/.prettierrc`**
- Prettier configuration file establishing consistent formatting rules:
  - 2-space indentation (`tabWidth: 2`)
  - 80-character print width
  - Single quotes for JS strings
  - Semicolons enabled
  - Trailing commas in ES5 positions
  - Spaces inside object braces

**`scripts/frontend-quality.sh`**
- Shell script to run frontend quality checks from the project root
- Auto-installs `node_modules` if missing
- Runs `prettier --check` on all `*.js`, `*.css`, and `*.html` files
- Exits with a non-zero code on formatting violations (safe for CI)
- Usage: `./scripts/frontend-quality.sh`

### Reformatted Files

All three frontend files were reformatted to match the Prettier configuration:

**`frontend/script.js`**
- Changed indentation from 4 spaces to 2 spaces throughout
- Removed duplicate blank lines (e.g., inside `setupEventListeners`)
- Normalized arrow function parentheses: `forEach(button =>` → `forEach((button) =>`
- Trailing comma added to last property in multi-line object literals
- Long `addMessage(...)` call in `createNewSession` broken across lines for readability

**`frontend/style.css`**
- Changed indentation from 4 spaces to 2 spaces throughout
- Expanded `*, *::before, *::after` selector onto separate lines
- Split long `font-family` value across two lines at the 80-char boundary
- Expanded single-line rule sets (e.g., `.message-content h1 { font-size: 1.5rem; }`) to multi-line blocks
- Expanded `@keyframes bounce` `0%, 80%, 100%` selector onto separate lines
- Expanded `.no-courses, .loading, .error` selector onto separate lines

**`frontend/index.html`**
- Changed indentation from 4 spaces to 2 spaces throughout
- Lowercase `<!doctype html>` (Prettier standard)
- Self-closing void elements: `<meta ... />`, `<link ... />`, `<input ... />`
- Long `<button class="suggested-item" data-question="...">` attributes broken onto separate lines
- `<input>` attributes broken onto separate lines for readability
- `<svg>` attributes broken onto separate lines

## Feature: Light/Dark Mode Toggle Button

### Files Modified
- `frontend/index.html`
- `frontend/style.css`
- `frontend/script.js`

### What Was Added

#### `index.html`
- Added a `<button id="themeToggle">` element fixed in the top-right corner of the page.
- Contains two inline SVG icons: a **sun icon** (shown in light mode) and a **moon icon** (shown in dark mode).
- Button has `aria-label` and `title` attributes for accessibility. SVG icons use `aria-hidden="true"` since the button label already describes the action.

#### `style.css`
- Added a `[data-theme="light"]` CSS variable block that overrides the dark-mode defaults on `:root` with light-mode equivalents (backgrounds, surfaces, text, borders).
- Added `--toggle-bg` and `--toggle-hover-bg` variables to both `:root` (dark) and `[data-theme="light"]` blocks.
- Added `transition: background-color 0.3s ease, color 0.3s ease` to `body` for smooth theme switching.
- Added `.theme-toggle` styles:
  - `position: fixed; top: 1rem; right: 1rem` — top-right placement.
  - Circular shape (`border-radius: 50%`), 40×40px.
  - Hover: subtle scale-up (`transform: scale(1.1)`) with a soft shadow.
  - Focus: visible focus ring using `--focus-ring` variable (keyboard-navigable).
  - Active: slight scale-down for tactile click feedback.
  - All color/border transitions use `0.3s ease`.
- Icon visibility: `.sun-icon` hidden by default (dark mode), `.moon-icon` shown. Swapped under `[data-theme="light"]`.

#### `script.js`
- Added `initThemeToggle()` function called on `DOMContentLoaded`.
- Reads saved theme from `localStorage` and applies it on page load (persists user preference across sessions).
- Listens for clicks on `#themeToggle`, toggles `data-theme` attribute on `document.documentElement` between `"light"` and `"dark"`, and saves the new value to `localStorage`.

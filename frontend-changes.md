# Frontend Changes

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

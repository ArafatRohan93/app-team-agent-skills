# CSS custom properties and Tailwind themes

## Shape

- **CSS:** `:root { --color-primary: #3d5afe; --radius-md: 0.5rem; … }`, often with dark values in `[data-theme="dark"]` or `@media (prefers-color-scheme: dark)`.
- **Tailwind v4:** `@theme { --color-brand-500: …; --font-sans: …; --radius-lg: … }`.
- **Tailwind v3:** a `tailwind.config.js` `theme.extend` object. Copy its colour, spacing and borderRadius values into a CSS file of `--name: value;` lines, or write the spec by hand.

## Steps

1. Run `python3 scripts/draft_spec.py --from css design/sources/theme.css -o design/theme.spec.json`. It only reads `--name: value;` pairs.
2. **Dark values.** The draft doesn't know which block a variable came from. Read the dark block yourself and fill in `colors.dark`.
3. **`rgb()`, `rgba()`, `hsl()`, `hsla()`, `var(--x)`:** `draft_spec.py` converts and resolves these, keeping the alias chain in `source`. `oklch()`, `color-mix()` and other colour spaces stay in `unmapped`. Convert them yourself (for example with a browser devtools colour picker) and record the original in `source`.
4. **Separate type scales** (`--font-size-*`, `--font-weight-*`): compose text roles as described in `design-tokens-json.md` › Separate scales.
5. **Utility classes in HTML** (`bg-brand-500 text-white rounded-lg`) show usage. Use them to decide roles and components.

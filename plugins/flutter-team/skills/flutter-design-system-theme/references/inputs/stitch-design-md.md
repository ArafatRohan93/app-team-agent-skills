# Google Stitch `DESIGN.md`

Calibrated on a real Stitch export ("Calorie Deficit Tracker", 2026).

## Shape

1. **YAML front matter** (`--- … ---`) with `name`, `colors`, `typography`, `rounded` and `spacing`.
   - `colors` is a **complete Material 3 scheme generated from a seed**: kebab-case role names (`primary-container`, `surface-container-low`, `on-surface-variant`, the `*-fixed` roles…), plus the deprecated `background`, `on-background` and `surface-variant`. There's no dark mode.
   - `typography` entries have `fontFamily`, `fontSize` (px), `fontWeight` (a quoted string), `lineHeight` (px) and `letterSpacing` (**em**).
   - `rounded` and `spacing` use **rem**, and `full: 9999px`.
2. **Prose sections**: Brand & Style, Colors, Typography, Layout & Spacing, Elevation & Depth, Shapes, Components. **The prose is what the designer actually intends.** It often names colours that don't appear in the YAML (a Zinc neutral scale, status colours) or that contradict it.

## Steps

1. Run `python3 scripts/draft_spec.py --from stitch design/sources/DESIGN.md -o design/theme.spec.json`. This deterministically maps the whole YAML block, including the name aliases (`inverse-on-surface` → `onInverseSurface`) and the deprecated roles.
2. Read **Colors**:
   - **"Primary (`#xxxxxx`)":** compare it with the YAML `primary`. Stitch's YAML `primary` is often a darker tone of the seed, and the seed itself lands in `primary-container`. If the prose or the button spec uses a different value, record a conflict and recommend the prose/button value. When you change `primary`, also:
     - Set `seed` to the brand colour explicitly, so derived dark mode starts from the colour users see.
     - Check `primaryContainer`. If it now equals `primary` (the validator warns), recommend removing it so it derives, or ask the designer.
     - Leave the rest of the YAML's tonal family (`inversePrimary`, `surfaceTint`, `*Fixed`) as provided, and mention in the conflict reason that they came from the original seed.
   - **`surfaceBright`:** in light mode it normally equals `surface`. If you changed `surface`, record `surfaceBright` in the same conflict or set it to match.
   - **Named surfaces** (`surface-canvas`, `surface-elevated`, `surface-subtle`) → `surface`, `surfaceContainerLowest` and `surfaceContainerLow`. Record a conflict wherever they differ from the YAML.
   - **Text levels** (`text-primary`, `-secondary`, `-muted`) → `onSurface`, `onSurfaceVariant` and extension `onSurfaceMuted`.
   - **Borders** (`border-subtle`, `border-hairline`) → `outlineVariant` and extension `borderHairline`.
   - **Status tiers** → extensions `success`, `warning` and `danger`. Set `usage` from where they're used. Hero numbers are `largeText`.
3. Read **Elevation & Depth**:
   - Level 0 → `surface`; Level 1 → `surfaceContainerLowest` plus the card border.
   - The Level 2 pressed state → surface-container roles, or an extension (usage `border`/`fill`).
   - The Level 3 backdrop → `scrim` plus `bottomSheet.barrierOpacity`.
4. Read **Typography**:
   - Font fallbacks for other scripts → `fontFamilyFallback`; web stacks → `unmapped`.
   - "Tabular figures" → `fontFeatures: ["tnum", "lnum"]` on the numeric extras.
   - Line-height rules for a script → a `note`.
   - Rename draft extras to proper lowerCamelCase: `headlineLgMobile` → `headlineLargeMobile`.
5. Read **Shapes**:
   - Compare the prose px values with the `rounded` scale. Stitch prose sometimes uses shifted names, like "4px (rounded-sm)" while `rounded.sm` is 2px. Record a conflict and recommend the tokens when the component specs match them.
   - "Pill shapes forbidden" → a `note`, and don't use `radius: 9999` in any component.
6. Read **Components** → `components`:
   - Buttons: background, text colour, radius, height, text style, pressed colour.
   - Inputs: fill, border, focus colour and width, radius, height.
   - Chips, and row separators (`divider`).
   - Map every hex to a role or extension first. The pressed colour becomes an extension with usage `fill`.
7. List anything left over (sync dots, "roundedness: 1", responsive rules) in `unmapped` or `notes`.

## Expected conflicts in Stitch files

These came up in the calibration file, so expect similar ones: `primary`, `surface`, `surfaceContainerLow`, `onSurface`, `onSurfaceVariant`, `outlineVariant` (YAML vs prose), and `radiusSm` (prose names vs the `rounded` scale).

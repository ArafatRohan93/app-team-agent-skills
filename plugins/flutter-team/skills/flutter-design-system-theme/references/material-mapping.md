# Mapping designer names to Material 3

Map by **meaning and usage**, not by name alone. For every token, look at where the hand-off says it's used: components, examples, descriptions. Choose the Material role whose job matches that usage.

## Colour roles

Designers' words on the left, the Material role on the right.

| Designer vocabulary | Material role | Notes |
|---|---|---|
| brand, primary, accent, CTA, action, key colour | `primary` | The colour of filled buttons and active controls. If "primary" in the tokens differs from the CTA colour in the component specs, that's a **conflict**. |
| text/icon on the brand colour | `onPrimary` | |
| tinted brand background, selected chip, brand-soft | `primaryContainer` / `onPrimaryContainer` | |
| second brand colour, supporting accent | `secondary` (+ container) | |
| third accent, highlight, contrast accent | `tertiary` (+ container) | |
| error, destructive, invalid | `error` (+ container) | Use it only for errors. A "danger" status in data goes to an extension (`danger`). |
| canvas, page, background, base, app background, level 0 | `surface` | |
| card, sheet, elevated, paper, level 1, white plate | `surfaceContainerLowest` in light, often `#FFFFFF` | Material 3 raises elements with lighter or darker containers, not shadows. |
| subtle, recessed, input bg, muted bg, inactive pill | `surfaceContainerLow` | |
| default container, nav bar bg, grouped list bg | `surfaceContainer` | |
| strong, pressed, selected row bg | `surfaceContainerHigh` or `surfaceContainerHighest` | |
| text-primary, foreground, ink, body text | `onSurface` | |
| text-secondary, subdued text, caption | `onSurfaceVariant` | |
| text-muted, tertiary text, placeholder, disabled-ish | extension `onSurfaceMuted` (usage `text`) | Material has only two text levels. Check that it reaches 4.5:1. |
| border, stroke, divider (visible, interactive) | `outline` | Needs 3:1 against the surface. **Input and outlined-button borders are checked for this** (WCAG 1.4.11). |
| border-subtle, hairline, divider (decorative) | `outlineVariant` | If there are two decorative levels, use an extension for the second (`borderHairline`). |
| overlay, backdrop, dim, modal barrier | `scrim` | Put the opacity in `components.bottomSheet.barrierOpacity`. |
| dark tooltip, snackbar bg | `inverseSurface` / `onInverseSurface` | |
| success, positive, on-track, complete | extension `success` | required |
| warning, caution, attention, approaching | extension `warning` | required |
| info, neutral status | extension `info` | |
| pressed/hover shade of a colour | extension (usage `fill`), referenced from a component (`pressedBackground`) | |

### Traps

- **Tokens generated from a seed vs the designer's intent.** Stitch and Material Theme Builder generate a full, algorithmic scheme from one seed. The designer's prose often names different values for what users actually see. Keep the generated scheme for roles the prose doesn't mention. Record a conflict wherever the two disagree, and recommend the value the components use.
- **Near-duplicates** (`#FBF8FC` vs `#FBFBFA`) are still conflicts. Record them, and say in the reason that they're near-identical.
- **Deprecated roles** (`background`, `onBackground`, `surfaceVariant`): drop them if they equal their modern role, otherwise record a conflict.
- **One value, two roles.** If the recommendation makes two roles equal (for example `primary` = `primaryContainer`), say so in the conflict reason so the designer sees it.
- **A component spec vs the colour prose.** A component spec is more specific than the colour descriptions ("Input: background #FFFFFF" vs "surface-subtle: recessed inputs"), so it wins by default. Record the disagreement as a conflict on `components.<component>.<property>`, with both roles as candidates.
- **A subtle border on an interactive control** (`border-subtle` on inputs or buttons) usually fails 3:1. Keep the design's value, and raise it as a contrast question. The designer may accept it, or pick a darker border for interactive controls only.
- **Opacity inside a colour** (`#18181B` at 35%): store the opaque colour as the role, and put the opacity where it's applied (a component property). Never bake it into the hex.

## Text roles

Map by name first, then by size and purpose.

| Designer vocabulary | Material role |
|---|---|
| display-lg/md/sm, hero, jumbo | `displayLarge` / `displayMedium` / `displaySmall`, **but** a purpose-named style ("display-deficit", "price-hero") goes to `extras` |
| h1 · h2 · h3 | `headlineLarge` · `headlineMedium` · `headlineSmall` |
| h4 · h5 · h6, subtitle, card title, list item title | `titleLarge` · `titleMedium` · `titleSmall` |
| body-lg/md/sm, paragraph | `bodyLarge` / `bodyMedium` / `bodySmall` |
| caption, footnote, helper | `bodySmall` |
| label, button text, overline, tab, badge | `labelLarge` / `labelMedium` / `labelSmall` |
| numeric, metric, price, unit, code, mono | `extras`, usually with `fontFeatures: ["tnum", "lnum"]` |
| responsive variants (`-mobile`, `-tablet`) | For a phone-first app, the **mobile** value becomes the role (for example `headlineLarge`), and the large-screen value goes to `extras` (`headlineLargeWide`). For a tablet or desktop-first app, the reverse. Record the choice as an open conflict so the user confirms it. |

**Converting units:**

| From | To |
|---|---|
| px, pt | dp, 1:1 |
| rem | × 16, unless the hand-off states another root size |
| letter-spacing in em | × fontSize |
| letter-spacing in % | ÷ 100 × fontSize |
| unitless line height (1.5) | × fontSize |
| weight names | Thin 100, ExtraLight 200, Light 300, Regular 400, Medium 500, SemiBold 600, Bold 700, ExtraBold 800, Black 900 |

**Fonts:**
- Record the family in `typography.fontFamily`.
- Put script-specific fallbacks (Bangla, Arabic, CJK) in `fontFamilyFallback`.
- Web-only stacks (`-apple-system`, `BlinkMacSystemFont`, `system-ui`) go to `unmapped`, because Flutter uses the platform font automatically.

## Dimensions

- **Map spacing and radius scales by the design system's names** (`sm`, `md`, `lg`…) onto the contract keys (see `spec-format.md` §5). The values follow the design, even if they differ from the shell defaults.
- **Extra steps get their own keys:** `base` → `spacingBase`, `DEFAULT` → `radiusDefault`.
- **Semantic sizes:**
  - screen margin → `screenPadding`
  - gutter → `spacingGutter`
  - minimum touch target → `sizes.minTouchTarget`
  - component heights → `sizes.buttonHeight` / `sizes.inputHeight`
- **When the prose names a step differently from the tokens** (for example "4px (rounded-sm)" while the tokens say `sm` = 2px), record a conflict. Recommend whichever the component specs agree with.

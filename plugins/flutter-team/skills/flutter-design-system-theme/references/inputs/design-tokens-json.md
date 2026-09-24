# Design-token JSON (W3C DTCG, Figma variables, Tokens Studio)

## Shapes the reader understands

| Shape | Looks like |
|---|---|
| W3C DTCG | nested groups whose leaves are `{"$value": …, "$type": "color" \| "dimension" \| "typography" \| "shadow" \| …, "$description": …}`. A `$type` on a group applies to its tokens. |
| Tokens Studio | the same shape without the `$` (`value`, `type`). Unitless numbers are px (`"fontSize": "16"`, `"lineHeight": "20"`). |
| Figma variables export | one file per mode, or modes in `$extensions`. |
| Material Theme Builder | `md.sys.color.*` tokens named after the roles. |

**Value forms:**
- **Dimensions:** `"16px"`, `"1rem"`, or `{"value": 16, "unit": "px"}`.
- **Colours:** hex, `rgb()`/`hsl()`/`oklch()`, or `{"colorSpace": "srgb", "components": [...], "alpha": 1, "hex": "#…"}`.
- **Font families:** a string stack or an array. Platform and generic names (`-apple-system`, `Roboto`, `sans-serif`) are dropped.

**References and modes:**
- **References** (`"{color.green.900}"`) are resolved everywhere, including inside text styles. `source` records the chain, for example `semantic.action.primary → color.green.900`.
- **Dark mode** comes from any of:
  - `$extensions.mode.dark`;
  - a `dark` path segment (`theme.dark.brand`);
  - a second file passed with `--dark design/sources/tokens.dark.json`, with the same paths.

## What the draft does

```bash
python3 scripts/draft_spec.py --from dtcg design/sources/tokens.json [--dark design/sources/tokens.dark.json] -o design/theme.spec.json
```

**Colours, by tier.** Most files have a *palette* (`color.green.900`, `gray.500`) and *semantic* tokens (`semantic.action.primary`) that reference it.
- **Named after a Material role** (`md.sys.color.on-primary`, `surface`): mapped directly, in both modes. Such a token always wins over a suggestion.
- **Semantic or named colours:** the meaning of the name gives a **suggested** role. For example:

  | Token | Suggested role |
  |---|---|
  | `action.primary` | `primary` |
  | `text.on-brand` | `onPrimary` |
  | `text.muted` | `onSurfaceVariant` |
  | `surface.card` | `surfaceContainerLowest` |
  | `border.divider` | `outlineVariant` |
  | `surface.scrim` | `scrim` |
  | `success.500` | `ext.success` |
  | `status.pending` | `ext.statusPending` |
  | `swish.fg` / `swish.bg` | partner-brand extension pair |

  - **One value for a role:** the role is set, and its source says "suggested — confirm".
  - **Several values for a role**, e.g. `text.primary`, `text.strong` and `text.body` all reading as `onSurface`: the draft records an **open conflict** listing every candidate. It recommends the one whose name says default, primary, base or page, and keeps the others as extension colours (`textStrong`, `textBody`).
  - **No suggestion** (`semantic.heart`): the token is listed in `unmapped` for you.
- **Palette colours referenced by a semantic token:** one note. They're raw material, not roles.
- **Palette colours nothing references:** listed in `unmapped` as usually not needed.

**Text styles:**
- **Composite styles** map by name: `body` → `bodyMedium`, `button` → `labelLarge`.
- **Purpose-named styles** get a role from their name and size when they're the only candidate for it: `card-title` 14/700 → `titleSmall`, `meta` 12 → `bodySmall`.
- **Styles competing for one role** stay `extras`, and a note lists them.
- **Type primitives** that the styles use, by reference or repeated literally, need no mapping. The rest are listed.
- **A second font family** (e.g. Poppins for listing titles) is noted: text roles can't carry their own family.

**Dimensions:**
- **Numeric scales** map by value onto the contract keys: spacing `8` → `spacingSm`, `16` → `spacingLg`, and the same for Tailwind's `space-4` = 16px. Other steps keep their number (`spacing5`, `radius10`).
- **Screen gutter / margin** → `screenPadding`.
- **Pill / full radius** → `radiusFull`.

**Sizes:**
- `size.button` → `buttonHeight`
- `size.input` → `inputHeight`
- `size.icon` → `iconMd`
- `size.search` → `searchHeight`
- `size.tabbar` → `navigationBarHeight`
- touch target → `minTouchTarget`
- Screen width and breakpoints are layout facts: they go in a note.

**Component radii:** `radius.button`, `radius.input`, `radius.card`, `radius.chip` and `radius.sheet` become the components' radius (`bottomSheet.topRadius`).

**Everything else:**
- `shadow` tokens go to `unmapped`: Material 3 uses tonal surfaces.
- `duration`, `cubicBezier` and other non-theme types go to `unmapped` with their type.

## What you still do

1. **Confirm the suggested roles** against whatever else the hand-off has (screens, prose). Change a role where usage says otherwise.
2. **Take every conflict the draft opened to the user.** Two lighter greys competing for `surfaceContainerLow` is a real design question.
3. **Components:**
   - Set the colours the tokens imply: `input.border` = `ext.borderInput` if a `border.input` token exists, `card.border` = `ext.borderCard`…
   - Add the app bar and divider.
   - Record choices the tokens don't make as assumptions.
4. **`success` / `warning`:** the draft says which extension is the closest candidate (for example `statusPending`), or that there is none. See below.
5. **Contrast:** token sets are rarely checked. Expect light borders (`#E4E7EC` on white is 1.2:1), status colours and link blues to fail, and take each one to the user.

## Separate scales (no composite text styles)

Many token sets only have scales, such as `fontSize.small/medium/large` and `fontWeight.light/normal/bold`, with no complete text styles. The draft lists them in `notes`, and in `unmapped` with the reason "type-scale primitive". You then compose `typography.roles` yourself:

- **Map each size to the Material role nearest to it,** using the default sizes in `scripts/theme_spec.py` → `MATERIAL_TYPE_SCALE`. For example: 12 → `bodySmall` or `labelMedium`, 16 → `bodyLarge` or `titleMedium`, 24 → `headlineSmall`.
- **Pair weights by convention:** regular for body roles, medium for labels and titles, the bold step for headlines.
- **Every composed style is an assumption.** Set `source` to something like `"composed from fontSize.medium + fontWeight.normal (assumed pairing)"`. Then add one open conflict per role family, with the composed style's size as the single candidate, so the user confirms the pairing.
- **Leave out roles the scale can't sensibly fill.** They get Material defaults, and the report says so.

Take line height and letter spacing from the matching tokens if they exist. Otherwise leave them out, and Material's defaults for that role apply.

## Missing required values

A small token set often lacks the surfaces, text colours or the `success`/`warning` colours the app shell needs. Don't invent them silently:
- **Roles** (`surface`, `onSurface`…): leave them out. They're derived from the seed and reported as derived.
- **`success` and `warning`:** the validator requires them. Use the closest token the draft names, or propose a value that fits the palette. Mark it `"source": "assumption — …"`, and add an open conflict listing the candidates, so the user or designer confirms it.

## Calibration

The reader was tested on:
- **A real two-tier ecommerce token file** (Foremarket: palette plus `semantic.*`, 14 composite text styles, dimension objects, sizes, shadows). The draft maps 14 roles and 26 extension colours and opens 5 conflicts. The generated theme passes `flutter analyze`. `flutter test` fails only on the design's own contrast problems.
- **Test files built for:**
  - Material Theme Builder names with `$extensions` dark modes and colour objects;
  - Tokens Studio with a separate dark file.

## Checking the tokens against the screens

Token files drift from the design. Values get retyped, and screens use greys no token names. When the hand-off has screens too, pass them: `--screens design/sources/screens.figma.css.txt` (a Figma Copy as CSS, see `figma-css.md`) or an HTML page. The draft then:

- **Checks each role against its drawn usage:**

  | Role | Drawn usage |
  |---|---|
  | `primary` | filled-button fill |
  | `surface` | screen background |
  | `onSurface` | body text |
  | `outline` | field border |
  | `outlineVariant` | card border / divider |

  If the drawn colour differs from the token, it opens a conflict (or adds to one already open) with both values:
  - **Near-identical** (ΔE ≤ 3, e.g. `#134030` vs `#143F30`): the token is recommended, and the drawing is drift.
  - **Visibly different** (e.g. borders `#E4E7EC` in the tokens, `#C8C8C8` on every field): the drawn value is recommended. The tokens may be out of date, and the designer confirms.
- **Notes drift** for every other token colour drawn slightly differently.
- **Lists token colours the screens don't use.** They may just be missing from these screens.
- **Lists often-drawn colours no token matches,** each with its closest token. These are the warning or accent sets the tokens forgot, or tokens that were retyped.

Take all of these to the user alongside the other conflicts.

# Theme spec format (`design/theme.spec.json`, specVersion 1)

This is the single hand-off between extraction and generation. `scripts/theme_spec.py` has the machine-readable rules: role lists, contract names and component properties.

## Contents
1. Top level
2. colors and seed
3. extensionColors
4. typography
5. spacing, radius, sizes
6. components
7. conflicts
8. acceptedContrastExceptions, unmapped, notes
9. Complete minimal example

## 1. Top level

```json
{
  "specVersion": 1,
  "name": "Calorie Deficit Tracker",
  "sources": [{"id": "stitch", "type": "stitch-design-md", "file": "design/sources/DESIGN.md"}],
  "policy": {"deriveMissingDark": true, "schemeVariant": "fidelity"},
  "seed": {"value": "#10564F", "source": "…"},
  "colors": {"light": {}, "dark": {}},
  "extensionColors": {},
  "typography": {"fontFamily": {}, "fontFamilyFallback": [], "roles": {}, "extras": {}},
  "spacing": {}, "radius": {}, "sizes": {},
  "components": {},
  "conflicts": [],
  "acceptedContrastExceptions": [],
  "unmapped": [],
  "notes": []
}
```

- **`policy.deriveMissingDark`** (default `true`): when dark colours are missing, derive them from the seed with Material's tonal algorithm and flag them in the report. Set it to `false` when the design team must supply dark mode, and validation then fails until they do.
- **`policy.schemeVariant`**: the Flutter `DynamicSchemeVariant` used to derive roles the hand-off omits. `fidelity` (the default) keeps the brand colour's chroma. `tonalSpot` is Material's softer default.
- **`seed`** (optional, defaults to `colors.light.primary`): the colour every derived role is computed from.

**Value objects.** Every colour and dimension is an object, never a bare value:

```json
{"value": "#10564F", "token": "primary-container", "name": "Deep Forest Teal", "source": "DESIGN.md prose › Colors › Primary"}
```

| Field | Required | Meaning |
|---|---|---|
| `value` | yes | `#RRGGBB` or `#AARRGGBB` for colours, dp numbers for dimensions |
| `source` | yes | where it came from: file, section and token. For inferences, say so ("inferred from …") |
| `token` | no | the designer's token name |
| `name` | no | a human name. It becomes the private palette constant (`deepForestTeal`) |

## 2. `colors` and `seed`

```json
"colors": {
  "light": {"primary": {…}, "onPrimary": {…}, "surface": {…}},
  "dark":  {}
}
```

- **Keys** must be Flutter `ColorScheme` roles (`scripts/theme_spec.py` → `COLOR_ROLES`), such as `primary`, `onPrimary`, `primaryContainer`, the `surface` family, `outline`, `outlineVariant`, `scrim`, `inverseSurface`, `onInverseSurface`, `inversePrimary`, `surfaceTint` and the `*Fixed` roles.
- **Deprecated roles are rejected.** Map `background` → `surface`, `onBackground` → `onSurface` and `surfaceVariant` → `surfaceContainerHighest`. If their values differ, record a conflict.
- **Only `colors.light.primary` is required.** Roles you leave out are derived from the seed and listed as "derived from seed" in the report. Provided roles are used exactly.

## 3. `extensionColors`

These are roles Material has no slot for. Widgets read them as `context.appColors.<name>`.

```json
"extensionColors": {
  "success": {"usage": "largeText", "light": {"value": "#0D7A5F", "name": "Rich Emerald", "source": "…"}, "dark": null},
  "borderHairline": {"usage": "border", "light": {"value": "#F0F0EE", "source": "…"}}
}
```

- **Required names:** `success` and `warning`. The shell's theme contract requires them to exist, but the shell's own screens don't use them. So set their `usage` from how the **design** uses them.
- **Names** are lowerCamelCase and must not collide with a `ColorScheme` role.
- **`usage`** decides both the contrast rule, checked against `surface`, and how a missing dark value is derived:

| usage | Min contrast | Dark derivation |
|---|---|---|
| `text` | 4.5:1 | light foreground tone |
| `largeText` (≥24dp, or ≥18.66dp bold) | 3:1 | light foreground tone |
| `icon` | 3:1 | light foreground tone |
| `border` | none | subtle outline tone |
| `fill` | none | container tone |

## 4. `typography`

```json
"typography": {
  "fontFamily": {"value": "Inter", "source": "…"},
  "fontFamilyFallback": ["Hind Siliguri"],
  "roles": {
    "headlineLarge": {"token": "headline-lg", "fontSize": 28, "lineHeight": 34, "fontWeight": 600, "letterSpacing": -0.56, "source": "…"}
  },
  "extras": {
    "numericMetric": {"token": "numeric-metric", "fontSize": 22, "lineHeight": 26, "fontWeight": 600, "letterSpacing": -0.44,
                      "fontFeatures": ["tnum", "lnum"], "source": "…"}
  }
}
```

- **`roles` keys:** the 15 Material text roles, `display|headline|title|body|label` × `Large|Medium|Small`. Missing roles use the Material 3 defaults with your font, and the report lists them.
- **`extras`:** purpose-specific styles such as hero numbers or prices. Widgets read them as `context.appText.<name>`.
- **Units are dp.**
  - `lineHeight` is an absolute value (px), not a ratio. For a ratio like 1.5, multiply by `fontSize`.
  - `letterSpacing` is in dp. For em, multiply by `fontSize`: −0.02em × 28 = −0.56.
- **`fontWeight`:** 100–900.
- **`fontFeatures`:** 4-letter OpenType tags, such as `tnum` (tabular numbers) or `lnum` (lining figures).

## 5. `spacing`, `radius`, `sizes`

```json
"spacing": {"spacingLg": {"value": 20, "token": "space-lg", "source": "…"}},
"radius":  {"radiusLg": {"value": 8, "token": "rounded.lg", "source": "…"}},
"sizes":   {"buttonHeight": {"value": 48, "source": "…"}}
```

- **Keys** become `AppDimensions` constants.
- **The shell's contract names are always generated.** If a design system lacks one, the shell default is used and reported.

| Group | Contract names (shell default) |
|---|---|
| spacing | `spacingXxs` (2), `spacingXs` (4), `spacingSm` (8), `spacingMd` (12), `spacingLg` (16), `spacingXl` (24), `spacing2xl` (32), `spacing3xl` (48), `screenPadding` (24) |
| radius | `radiusSm` (6), `radiusMd` (12), `radiusLg` (16), `radiusXl` (24), `radiusFull` (9999) |
| sizes | `buttonHeight` (48), `inputHeight` (48), `iconSm` (16), `iconMd` (24), `iconLg` (32) |

- **Map by the design system's own names.** If its `lg` is 20, then `spacingLg` = 20. Extra keys (`spacingBase`, `radiusDefault`, `minTouchTarget`) are added as-is.

## 6. `components`

```json
"components": {
  "filledButton":   {"height": 48, "radius": 8, "textStyle": "headlineSmall", "background": "primary",
                     "foreground": "onPrimary", "pressedBackground": "ext.primaryPressed", "source": "…"},
  "outlinedButton": {"height": 48, "radius": 8, "textStyle": "…", "background": "…", "foreground": "…", "border": "…", "borderWidth": 1},
  "textButton":     {"textStyle": "…", "foreground": "primary", "horizontalPadding": 0},
  "input":          {"height": 48, "radius": 6, "fill": "…", "border": "…", "focusBorder": "primary", "focusBorderWidth": 1.5, "errorBorder": "error"},
  "card":           {"radius": 8, "color": "…", "border": "…", "elevation": 0},
  "chip":           {"radius": 4, "background": "…", "border": "…", "label": "…", "textStyle": "…"},
  "divider":        {"color": "ext.borderHairline", "thickness": 1},
  "bottomSheet":    {"background": "…", "topRadius": 12, "barrierColor": "scrim", "barrierOpacity": 0.35}
}
```

- **Colour properties** take a `ColorScheme` role name or `ext.<extensionColor>`. Raw hex is rejected.
- **`textStyle`** takes any Material text role (roles the design omits use Material defaults) or a name from `typography.extras`.
- **`radius: 9999`** means a pill (`StadiumBorder`).
- **`input.border: "none"`** draws a borderless filled field. Its contrast check becomes fill vs `surface` (id `input.fill`).
- **`appBar`** takes `background`, `foreground`, `titleStyle`, `elevation` and `centerTitle`.
- **`input`** also takes `paddingHorizontal` and `paddingVertical`.
- **Any component** can carry a `source` and a `note`. The note is printed in the report next to that component. Use it for assumptions the designer should see. Anything that **needs a decision** belongs in an open conflict.
- **Anything left out uses these defaults.** Set every value the design specifies. A button left without a `radius` becomes a pill.

| Component | Defaults when omitted |
|---|---|
| `filledButton` | height: `sizes.buttonHeight`, radius: `9999 (pill)`, textStyle: `labelLarge`, background: `primary`, foreground: `onPrimary` |
| `outlinedButton` | height: `filledButton.height`, radius: `filledButton.radius`, textStyle: `filledButton.textStyle`, foreground: `onSurface`, border: `outline`, borderWidth: `1` |
| `textButton` | textStyle: `labelLarge`, foreground: `primary` |
| `input` | height: `sizes.inputHeight`, radius: `radius.radiusMd`, fill: `surfaceContainer`, border: `outline`, focusBorder: `primary`, focusBorderWidth: `2`, errorBorder: `error`, paddingHorizontal: `16`, paddingVertical: `12` |
| `card` | radius: `radius.radiusMd`, elevation: `0` |
| `chip` | radius: `radius.radiusSm`, textStyle: `labelLarge` |
| `divider` | color: `outlineVariant`, thickness: `1` |
| `bottomSheet` | background: `surfaceContainerLow`, topRadius: `radius.radiusXl`, barrierColor: `scrim`, barrierOpacity: `0.32` |
| `appBar` | background: `surface`, foreground: `onSurface`, titleStyle: `titleLarge`, elevation: `0`, centerTitle: `False` |

`outlinedButton` inherits `height`, `radius` and `textStyle` from `filledButton` unless you set its own.

## 7. `conflicts`

A conflict is any disagreement inside the hand-off: YAML vs prose, the token table vs a component spec, the PDF vs a screenshot.

```json
{
  "target": "colors.light.primary",
  "status": "open",
  "candidates": [
    {"value": "#003D38", "source": "DESIGN.md front matter colors.primary"},
    {"value": "#10564F", "source": "DESIGN.md prose › Functional Roles › Primary; Components › Primary Button"}
  ],
  "recommendation": "#10564F",
  "reason": "prose and the button spec both use #10564F; FilledButton reads `primary`"
}
```

- **`target`** is a dotted path into the spec:
  - `colors.<light|dark>.<role>`
  - `extensionColors.<name>.<light|dark>`
  - `typography.roles.<role>` or `typography.extras.<name>`
  - `spacing.<key>`, `radius.<key>` or `sizes.<key>`
  - `components.<component>.<property>`, where the candidates can be role names such as `surfaceContainerLowest`
- **Always** put the recommended value at `target`, so a provisional generation is coherent.
- **`status: "open"`** blocks generation, unless `--allow-open-conflicts` is passed, which produces a PROVISIONAL result.
- **After the user decides:** set `"status": "resolved"` and `"resolution": "<value>"`. The validator checks that the value at `target` matches.
- **Assumptions are conflicts too.** When the hand-off doesn't give a value you have to supply (`success`/`warning`, composed text styles, sampled screenshot colours), add an open conflict with your value as the **single** candidate. That makes the user confirm it instead of it slipping through.

## 8. `acceptedContrastExceptions`, `unmapped`, `notes`

```json
"acceptedContrastExceptions": [
  {"pair": "surface/ext.warning", "mode": "light", "reason": "Only used for 44px hero numbers (large text, 3:1)"}
],
"unmapped": [{"token": "roundedness: 1", "value": "", "reason": "descriptive only"}],
"notes": ["Pill shapes are forbidden; radiusFull is kept for status dots only."]
```

- **`pair` ids** are the ids the validator and the generated test print: `<background>/<foreground>` for colour pairs, and `input.border` / `outlinedButton.border` for interactive borders (3:1 against the component's fill). `mode` is `light`, `dark` or `both`. The generated contrast test skips exactly these pairs.
- **`unmapped`:** anything in the hand-off with no place in the theme, with a reason. Nothing is silently dropped.
- **`notes`:** rules that can't be tokens. They're copied into the report for developers.

## 9. Complete minimal example

```json
{
  "specVersion": 1,
  "name": "Acme",
  "sources": [{"id": "brief", "type": "pdf", "file": "design/sources/brand.pdf"}],
  "policy": {"deriveMissingDark": true, "schemeVariant": "fidelity"},
  "colors": {"light": {"primary": {"value": "#3D5AFE", "source": "brand.pdf p.2 'Acme Blue'"}}, "dark": {}},
  "extensionColors": {
    "success": {"usage": "text", "light": {"value": "#2E7D32", "source": "brand.pdf p.3"}},
    "warning": {"usage": "icon", "light": {"value": "#B26A00", "source": "brand.pdf p.3"}}
  },
  "typography": {"fontFamily": {"value": "Inter", "source": "brand.pdf p.4"}, "roles": {}, "extras": {}},
  "spacing": {}, "radius": {}, "sizes": {}, "components": {},
  "conflicts": [], "acceptedContrastExceptions": [], "unmapped": [], "notes": []
}
```

Everything not listed is derived or defaulted, and the report lists it all.

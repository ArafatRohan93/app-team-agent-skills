# Design-token JSON (W3C DTCG, Figma variables, Tokens Studio)

## Shape

- **W3C DTCG:** nested groups whose leaves are `{ "$value": …, "$type": "color" | "dimension" | "typography" | … }`.
- **Tokens Studio:** the same shape without the `$` (`value`, `type`).
- **Figma variables export:** collections and modes. A collection with modes `Light`/`Dark` gives you both colour modes.
- **Aliases** look like `"{color.brand.500}"`. `draft_spec.py` resolves them and records the chain in `source` (`colors.primary → color.violet`). The primitive's name becomes the palette name.

## Steps

1. Run `python3 scripts/draft_spec.py --from dtcg design/sources/tokens.json -o design/theme.spec.json`. It flattens the tokens, resolves aliases, and sorts everything into colours, typography, radius and spacing. It normalises scale words (`small`/`medium`/`large` → `Sm`/`Md`/`Lg`). Unknown groups go to `unmapped`.
2. **Two-tier token sets.** Most token files have *primitive* tokens (`blue.500`) and *semantic* tokens (`color.action.primary` → `{blue.500}`). Map the **semantic** tokens to roles, per `material-mapping.md`, and use primitive names only as palette `name`s.
3. **Modes.** Move values from a `Dark` mode, or a `dark` path segment, to `colors.dark` / `extensionColors.*.dark`. Check that each dark role pairs with a light one.
4. **Composite typography tokens** (`$type: typography`) map like Stitch entries. Check the units: DTCG dimensions can be `{ "value": 16, "unit": "px" }` objects.
5. Map component tokens (`button.primary.background`…) to `components`, using role references.

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
- **`success` and `warning`:** the validator requires them, so propose values that fit the palette and mark them `"source": "assumption — not in the hand-off"`. Add an open conflict for each with that single candidate, so the user or designer confirms it.

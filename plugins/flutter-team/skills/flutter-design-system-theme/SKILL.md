---
name: flutter-design-system-theme
description: Turns a design-team hand-off into a Material 3–compliant Flutter theme for apps built with the flutter-app-structure skill. The hand-off can be a Google Stitch DESIGN.md, a Claude Design export, Figma variables or W3C design-token JSON, Tailwind or CSS variables, HTML, a PDF style guide or screenshots. The theme covers colour roles, brand extension colours, the text scale, spacing and radius, component themes, dark mode, a preview screen, contrast tests and a mapping report for designer sign-off. Use it whenever someone shares a design system, style guide, tokens file, colour palette, typography scale or UI mockup and wants the app themed from it. Also use it when they want to update the theme after a design change, add dark mode, add another brand or white-label palette, or ask why the app's colours or fonts don't match the design — even if they only say "here's the design" or "make it look like this".
---

# Flutter Design System → Theme

Design hand-offs never look the same. One designer sends a Stitch `DESIGN.md`, another a Claude Design export, a third a PDF or a screenshot. If an AI writes Dart straight from each of those, every run makes different, invisible mapping decisions. This skill splits the job so that only one step needs judgement:

```
hand-off ─► 1. DRAFT (script) ─► 2. COMPLETE (you) ─► 3. VALIDATE (script) ─► 4. DECIDE (user) ─► 5. GENERATE (script) ─► 6. VERIFY
            structured tokens     prose, components,    schema, roles,         open conflicts,      Dart theme files,      analyze, tests,
            → draft spec          conflicts, brand      contrast, dark mode    contrast exceptions  preview, tests, report preview screen
```

- **The theme spec** (`design/theme.spec.json` in the app) is the only thing you write. Everything in Dart is generated from it.
- **Every value records its source.**
- **Nothing is resolved silently.** When the hand-off disagrees with itself, you record a *conflict* with a recommendation, and the user decides.

All paths below are relative to this skill's folder. The scripts need only `python3`, and the target app must follow the flutter-app-structure layout (`lib/shared/theme/`). For HTML designs, a locally installed Chrome, Chromium, Edge or Brave lets `--from html` read computed styles (classes, Tailwind, scripts, dark mode). Without one, it falls back to a static read and says what it couldn't see.

## Before you start

1. **Check the target.** The app must have `lib/shared/theme/theme.dart`, meaning it was bootstrapped with flutter-app-structure. If it wasn't, stop and say so. The generator refuses other layouts.
2. **Keep the originals.** Copy every hand-off file into `design/sources/` in the app so the spec's `source` fields point at real files. If the user pasted text, save it as a file first.
3. **Read the guides.**
   - `references/spec-format.md`: every field of the spec.
   - `references/material-mapping.md`: how designer names map to Material roles.
   - The input guide for each file type you have:

| Hand-off | Guide | Draft script |
|---|---|---|
| Google Stitch `DESIGN.md` | `references/inputs/stitch-design-md.md` | `--from stitch` |
| Figma variables, Tokens Studio or W3C DTCG JSON (palette plus semantic tiers, composite text styles, modes) | `references/inputs/design-tokens-json.md` | `--from dtcg` (`--dark <file>` for a separate dark-mode file) |
| CSS custom properties or a Tailwind theme | `references/inputs/css-tailwind.md` | `--from css` |
| Claude Design System (claude.ai `project/tokens.json` plus READMEs) | `references/inputs/claude-design.md` | `--from claude` |
| Any **HTML design**: a Claude Design page export (bundled or rendered), an HTML/CSS mock-up, a Tailwind or React prototype, a responsive page | `references/inputs/html-design.md` | `--from html` (writes `<file>.evidence.md`) |
| Figma **Copy as CSS** (layers selected in Figma → Copy as CSS, pasted into a `.txt`) | `references/inputs/figma-css.md` | `--from figma-css` (writes `<file>.evidence.md`) |
| PDF or screenshots | `references/inputs/visual-sources.md` | none. Write the spec by hand, at low confidence |

**Tokens and screens together give the best result.** Tokens have the names; screens show what the designer actually uses. Pass the screens with any token input: `--screens <figma copy or html>`. The draft then:
- opens a conflict wherever a role's drawn colour differs from its token;
- lists drift (near-identical values), token colours the screens don't use, and drawn colours no token matches.

## Workflow

### 1. Draft (deterministic)

```bash
python3 scripts/draft_spec.py --from stitch design/sources/DESIGN.md -o design/theme.spec.json
```

This maps everything that can be mapped by name, converts units (px, rem and em become dp) and records sources. Whatever it can't place goes to `unmapped`.
- **Tokens with screens:** when the hand-off has both, add the screens, e.g. `--from dtcg design/sources/tokens.json --screens design/sources/screens.figma.css.txt`.
- **No structured part** (a PDF or screenshot): start from `references/spec-format.md` and write the spec yourself.

### 2. Complete the spec (your judgement)

Read the rest of the hand-off, including the prose, component specs and images, then:

- **Resolve `unmapped` tokens.** Map each one to a Material role or an extension colour by meaning, using `references/material-mapping.md`. If it truly has no role, leave it in `unmapped` with a reason.
- **Record conflicts.** When two parts of the hand-off give different values for the same thing, put your recommended value at the target and add a conflict with both candidates, a recommendation and the reason. Never drop a candidate.
- **Record assumptions.** When you have to supply a value the hand-off doesn't give, add an open conflict with that single candidate. Examples:
  - required `success`/`warning`;
  - text roles composed from separate size and weight scales;
  - colours sampled from a screenshot;
  - one value picked from a range ("cards 4–8px");
  - a component property the spec is silent on but you had to set.

  Component `note`s appear in the report, but only an open conflict forces a decision.
- **Add `extensionColors`** for roles Material lacks. `success` and `warning` are required by the app shell. Set each colour's `usage` (`text`, `largeText`, `icon`, `border` or `fill`). It sets the contrast rule and how dark mode is derived.
- **Move type styles.** Purpose-named styles (a hero number, a price) go to `typography.extras`. Scale-named styles go to `typography.roles`. Add `fontFeatures` such as `tnum` when the design asks for tabular numbers.
- **Fill in `components`** from the component specs. Colours there must be role names or `ext.<name>`, never raw hex. Register a hex value as a colour first.
- **Add `notes`** for rules that can't be tokens, for example "pill shapes are forbidden" or "Bangla needs +10% line height".

### 3. Validate

```bash
python3 scripts/validate_theme_spec.py design/theme.spec.json
```

Fix every error **except open conflicts**. Those are the user's decisions, in step 4. To validate while conflicts are still open, add `--allow-open-conflicts`.

Warnings are information for the user:
- derived roles and Material default text roles;
- a `primary` that equals `primaryContainer`;
- component radii you didn't set (a button left without one becomes a pill);
- missing font declarations.

### 4. Ask the user

Show the user every **open conflict**, with the candidates, your recommendation and the reason, and every **contrast failure**. Contrast failures include the WCAG 1.4.11 3:1 check on interactive borders (`input.border`, `outlinedButton.border`). Ask the questions the warnings raise too. Their answers go into the spec:

- **A conflict:** set `"status": "resolved"` and `"resolution"`, and make sure the value at the target matches.
- **An accepted low-contrast pair:** add an `acceptedContrastExceptions` entry with a reason.
- **A fix:** change the colour.

If the user wants to see the result before deciding, generate with `--allow-open-conflicts`. The output is marked **PROVISIONAL**.

### 5. Generate

```bash
python3 scripts/generate_theme.py --root . [--allow-open-conflicts] [--dry-run]
```

This writes every file under `lib/shared/theme/` (tokens, colour schemes, and all component themes including the app bar), plus `ThemePreviewScreen`, three theme tests and `design/THEME_REPORT.md`. All of them are marked GENERATED. On the first run it replaces the shell's hand-written theme, so review the result with `git diff`.

The generated contrast test checks the **final** light and dark themes. That includes colours derived at runtime, which the Python validator can't see. So a derived dark border can still fail here after validation passed. Treat that the same as a validator contrast failure: take it to the user.

### 6. Verify

- Run `flutter analyze` and `flutter test`, prefixed with `fvm` if the project uses it. The generated contrast test checks the **final** light and dark themes, including derived colours.
- If the report warns that the font isn't declared, add the font files under `assets/fonts/` and declare them in `pubspec.yaml`, or ask the user whether to use `google_fonts`.
- Tell the user to open `ThemePreviewScreen` in light and dark mode (for example, temporarily as `home:`), and to send `design/THEME_REPORT.md` to the designer for sign-off.

## Rules

- **Never write the theme Dart by hand.** Change the spec and regenerate. Generated files say so in their header.
- **Every value needs a `source`.** If you inferred it, say so: "inferred from screenshot, pixel sample at (120,48)".
- **Don't guess silently.** A value the hand-off doesn't give is either left out (the generator derives it and reports it), or added with a note that it's an assumption.
- **Components reference roles, not hex.** That keeps dark mode and future brands working.
- **Feature code is never touched.** Widgets already read `context.colors`, `context.appColors`, `context.textTheme`, `context.appText` and `AppDimensions`, so a new theme needs no widget changes.

## Updating an existing theme

When the designer sends a new version:
1. Put it in `design/sources/`.
2. Re-run `draft_spec.py` to a **new** file, such as `design/theme.spec.next.json`.
3. Diff it against the current spec and carry over the decisions already made: resolved conflicts, extension colours, components.
4. Validate, generate, and check the report's diff with `git diff design/THEME_REPORT.md`.

## Dark mode, multiple brands and user-chosen themes

See `references/runtime-theming.md` for:
- how derived dark mode works, and when to insist on designer-provided dark colours;
- adding a second brand (one spec per brand);
- letting users pick light, dark or system, or an accent colour, with a `ThemeCubit` persisted through `KeyValueStorage`.

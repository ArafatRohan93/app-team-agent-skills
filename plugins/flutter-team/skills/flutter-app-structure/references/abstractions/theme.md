# Theme

> **Theming from a designer's hand-off** (Stitch `DESIGN.md`, a Claude Design System, token JSON, CSS, PDF, screenshots): use the **flutter-design-system-theme** skill. It generates every file below from a validated spec. Once it has run, those files are marked GENERATED: change the spec and regenerate instead of editing them. This page describes the structure the files follow and how widgets use them.

**Files:** `lib/shared/theme/`
```
theme.dart                 # barrel. Widgets import only this
app_theme.dart             # AppTheme.light / AppTheme.dark, built by one _build(ColorScheme, AppColorExtension)
theme_context_ext.dart     # context.colors / context.appColors / context.textTheme / context.theme
tokens/app_colors.dart     # _Palette (private raw values) → AppColorsLight / AppColorsDark (semantic) → AppColorExtension
tokens/app_dimensions.dart # AppDimensions: spacing, radius, component sizes on an 8px grid
tokens/app_typography.dart # AppTypography: size, weight, height, tracking only. No colours
component_themes/          # color_schemes, button_themes, input_decoration_theme, app_bar_theme. Each is a function of ColorScheme
```

## The layers
1. **Palette (`_Palette`)** is private raw hex values. Rebranding means editing this and the mapping below.
2. **Semantic tokens (`AppColorsLight`/`AppColorsDark`)** give each colour a role: primary, surface, onSurface, error, success… Only `component_themes/` and `AppColorExtension` read these.
3. **The theme** is `ColorScheme` for Material roles plus the `AppColorExtension` ThemeExtension for roles Material lacks (success, warning).
4. **Widgets** read everything from the active theme, so light and dark both work without any code changes.

## Usage in widgets
```dart
import 'package:app/shared/theme/theme.dart';

Container(
  padding: const EdgeInsets.all(AppDimensions.spacingLg),
  decoration: BoxDecoration(
    color: context.colors.surfaceContainer,
    borderRadius: BorderRadius.circular(AppDimensions.radiusMd),
  ),
  child: Text('Paid', style: context.textTheme.labelLarge?.copyWith(color: context.appColors.success)),
);
```
- Material role → `context.colors.<role>`. Brand-only role → `context.appColors.<role>`.
- Text → `context.textTheme.<role>`. Only use `.copyWith(color: …)` to recolour, never to resize.
- Spacing, radius and sizes → `AppDimensions.*`. Never raw numbers.
- Buttons, inputs and app bars are already styled by component themes, so use plain `FilledButton`, `TextField` and `AppBar`.

## Extending
- **New brand colour role:** add it to `AppColorsLight` and `AppColorsDark`, add a field to `AppColorExtension` (constructor, `light`/`dark`, `copyWith`, `lerp`), and read it with `context.appColors.x`.
- **New component theme:** add `component_themes/<x>_theme.dart` exposing `XThemeData xTheme(ColorScheme colors)` and wire it into `AppTheme._build`.
- **Custom font:** add files to `assets/fonts/`, declare them in `pubspec.yaml` and set `AppTypography.fontFamily`.
- **Light-only app:** keep `darkTheme` out of `MaterialApp`. The same widget code still works.

## Testing
`tester.pumpApp(widget, theme: AppTheme.dark)` renders any widget in dark mode. See `test/shared/theme/app_theme_test.dart`.

## Don'ts
- No `Color(0x…)`, `Colors.*` (except `Colors.transparent`) or raw `TextStyle(fontSize: …)` in `features/`.
- Don't reference `AppColorsLight`/`AppColorsDark` from widgets, because that breaks dark mode.

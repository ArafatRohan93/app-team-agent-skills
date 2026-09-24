# Dark mode, brands and user-chosen themes

Widgets only read `context.colors`, `context.appColors`, `context.textTheme`, `context.appText` and `AppDimensions`. So everything here happens in the theme layer, and no feature code changes.

## Dark mode

| The hand-off has… | What to do |
|---|---|
| a dark scheme | Map it into `colors.dark` and `extensionColors.*.dark`. Every provided value is used exactly. |
| no dark scheme, and derivation is acceptable | Keep `policy.deriveMissingDark: true`. `ColorScheme.fromSeed(brightness: dark)` derives the dark scheme from the seed, and each brand colour is derived from its own tonal palette according to its `usage`. The report marks everything as derived, and the contrast test checks the result. |
| no dark scheme, and the brand is strict (a regulated or white-label client) | Set `policy.deriveMissingDark: false`. Validation then fails until the designer supplies dark values. Tell the user that's why. |

- **Derived dark mode needs a designer's eyes.** Always tell the user to review `ThemePreviewScreen` in dark mode, and list the derived colours from the report.
- **Mixed is fine.** You can provide some dark roles and derive the rest. For example, give the dark `surface` exactly and let the others derive.

## Light, dark or system, chosen by the user

The generator produces `AppTheme.light` and `AppTheme.dark`. Letting the user choose is app code, so it goes in the shell and isn't generated:

```dart
// lib/shared/theme/theme_mode_cubit.dart
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:app/core/storage/key_value_storage.dart';
import 'package:app/shared/storage/storage_keys.dart';

class ThemeModeCubit extends Cubit<ThemeMode> {
  ThemeModeCubit({required KeyValueStorage storage})
    : _storage = storage,
      super(ThemeMode.system);

  final KeyValueStorage _storage;

  Future<void> load() async {
    final saved = await _storage.read(StorageKeys.themeMode);
    emit(ThemeMode.values.asNameMap()[saved] ?? ThemeMode.system);
  }

  Future<void> select(ThemeMode mode) async {
    emit(mode);
    await _storage.write(StorageKeys.themeMode, mode.name);
  }
}
```

Wire it up in three places:
1. **`StorageKeys`:** add `static const themeMode = '$_prefix.theme_mode';`.
2. **`App`:** wrap `MaterialApp.router` in `BlocProvider(create: (_) => ThemeModeCubit(storage: sl())..load())` and a `BlocBuilder<ThemeModeCubit, ThemeMode>`, then pass `themeMode: mode`. `theme:` and `darkTheme:` are already set.
3. **Settings screen:** call `context.read<ThemeModeCubit>().select(ThemeMode.dark)`.

Test the cubit with a `MockKeyValueStorage`, per the testing conventions in flutter-app-structure.

## A user-chosen accent colour

This is **not generated yet.** Here's the pattern to follow when an app needs it:
- Keep the generated `AppTheme` as the brand default.
- For a custom accent, build a scheme with `ColorScheme.fromSeed(seedColor: userColor, brightness: …)`. Keep the brand's `AppColorExtension` and typography, and reuse the generated component-theme functions, which take `(ColorScheme, AppColorExtension)`.
- Persist the seed as a hex string in `KeyValueStorage`, the same way as the theme mode.
- Check the contrast of the result at runtime, or limit users to a curated list of seeds. Curated seeds are safer, because they can be pre-tested.

When a second app needs this, extend `generate_theme.py` to also emit `AppTheme.fromSeed(Color seed, Brightness b)`, rather than hand-editing the generated `app_theme.dart`.

## Several brands or white-label builds

This is **not generated yet.** Today the generator produces one theme per app. The intended design:
- One spec per brand: `design/brands/<brand>/theme.spec.json`.
- The generator emits one palette file per brand plus an `AppBrand` enum, and `AppTheme.light` and `AppTheme.dark` take the brand.
- The brand is chosen per flavor in `AppConfig`, or at runtime for multi-tenant apps.

**Until then:** keep the specs side by side, and generate the active brand's spec before each build. Flavor-specific brands can run the generator in CI.

## Android dynamic colour (Material You)

This is optional, and only works on Android 12 and later. Add the `dynamic_color` package and use `DynamicColorBuilder` in `App`. When the system provides a scheme, you can use it for `colorScheme` while keeping the brand's `AppColorExtension`. Most branded apps shouldn't do this, because it replaces the brand colours. Ask the user first.

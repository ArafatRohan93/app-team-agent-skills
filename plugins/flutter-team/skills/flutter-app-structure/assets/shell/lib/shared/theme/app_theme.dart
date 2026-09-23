import 'package:flutter/material.dart';

import 'component_themes/app_bar_theme.dart';
import 'component_themes/button_themes.dart';
import 'component_themes/color_schemes.dart';
import 'component_themes/input_decoration_theme.dart';
import 'tokens/app_colors.dart';
import 'tokens/app_typography.dart';

abstract final class AppTheme {
  static ThemeData get light =>
      _build(lightColorScheme, AppColorExtension.light);

  static ThemeData get dark => _build(darkColorScheme, AppColorExtension.dark);

  static ThemeData _build(ColorScheme colors, AppColorExtension appColors) =>
      ThemeData(
        useMaterial3: true,
        colorScheme: colors,
        scaffoldBackgroundColor: colors.surface,
        textTheme: AppTypography.textTheme.apply(
          bodyColor: colors.onSurface,
          displayColor: colors.onSurface,
        ),
        appBarTheme: appBarTheme(colors),
        filledButtonTheme: filledButtonTheme(colors),
        outlinedButtonTheme: outlinedButtonTheme(colors),
        textButtonTheme: textButtonTheme(colors),
        inputDecorationTheme: inputDecorationTheme(colors),
        dividerTheme: DividerThemeData(color: colors.outlineVariant),
        extensions: [appColors],
      );
}

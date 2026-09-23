import 'package:flutter/material.dart';

import '../tokens/app_dimensions.dart';
import '../tokens/app_typography.dart';

// Component themes take the ColorScheme so one definition serves light + dark.

FilledButtonThemeData filledButtonTheme(ColorScheme colors) =>
    FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(AppDimensions.buttonHeight),
        shape: const StadiumBorder(),
        textStyle: AppTypography.labelLarge,
      ),
    );

OutlinedButtonThemeData outlinedButtonTheme(ColorScheme colors) =>
    OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: colors.onSurface,
        side: BorderSide(color: colors.outline),
        minimumSize: const Size.fromHeight(AppDimensions.buttonHeight),
        shape: const StadiumBorder(),
        textStyle: AppTypography.labelLarge,
      ),
    );

TextButtonThemeData textButtonTheme(ColorScheme colors) => TextButtonThemeData(
  style: TextButton.styleFrom(
    foregroundColor: colors.primary,
    textStyle: AppTypography.labelLarge,
  ),
);

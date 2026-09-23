import 'package:flutter/material.dart';

import '../tokens/app_dimensions.dart';

InputDecorationTheme inputDecorationTheme(ColorScheme colors) {
  OutlineInputBorder border(Color color) => OutlineInputBorder(
    borderRadius: BorderRadius.circular(AppDimensions.radiusMd),
    borderSide: BorderSide(color: color),
  );

  return InputDecorationTheme(
    filled: true,
    fillColor: colors.surfaceContainer,
    contentPadding: const EdgeInsets.symmetric(
      horizontal: AppDimensions.spacingLg,
      vertical: AppDimensions.spacingMd,
    ),
    border: border(colors.outlineVariant),
    enabledBorder: border(colors.outlineVariant),
    focusedBorder: border(colors.primary),
    errorBorder: border(colors.error),
    focusedErrorBorder: border(colors.error),
  );
}

import 'package:flutter/material.dart';

import '../tokens/app_typography.dart';

AppBarTheme appBarTheme(ColorScheme colors) => AppBarTheme(
  backgroundColor: colors.surface,
  foregroundColor: colors.onSurface,
  elevation: 0,
  scrolledUnderElevation: 0,
  centerTitle: false,
  titleTextStyle: AppTypography.titleLarge.copyWith(color: colors.onSurface),
);

import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';

const lightColorScheme = ColorScheme(
  brightness: Brightness.light,
  primary: AppColorsLight.primary,
  onPrimary: AppColorsLight.onPrimary,
  primaryContainer: AppColorsLight.primaryContainer,
  onPrimaryContainer: AppColorsLight.onPrimaryContainer,
  secondary: AppColorsLight.primary,
  onSecondary: AppColorsLight.onPrimary,
  error: AppColorsLight.error,
  onError: AppColorsLight.onError,
  surface: AppColorsLight.surface,
  onSurface: AppColorsLight.onSurface,
  onSurfaceVariant: AppColorsLight.onSurfaceVariant,
  surfaceContainer: AppColorsLight.surfaceContainer,
  outline: AppColorsLight.outline,
  outlineVariant: AppColorsLight.outlineVariant,
);

const darkColorScheme = ColorScheme(
  brightness: Brightness.dark,
  primary: AppColorsDark.primary,
  onPrimary: AppColorsDark.onPrimary,
  primaryContainer: AppColorsDark.primaryContainer,
  onPrimaryContainer: AppColorsDark.onPrimaryContainer,
  secondary: AppColorsDark.primary,
  onSecondary: AppColorsDark.onPrimary,
  error: AppColorsDark.error,
  onError: AppColorsDark.onError,
  surface: AppColorsDark.surface,
  onSurface: AppColorsDark.onSurface,
  onSurfaceVariant: AppColorsDark.onSurfaceVariant,
  surfaceContainer: AppColorsDark.surfaceContainer,
  outline: AppColorsDark.outline,
  outlineVariant: AppColorsDark.outlineVariant,
);

import 'package:flutter/material.dart';

// Layer 1: raw brand palette — private. Rebrand by editing these values
// (or adding a new palette class) and remapping the layers below.
abstract final class _Palette {
  static const brand500 = Color(0xFF3D5AFE);
  static const brand100 = Color(0xFFE3E7FF);
  static const brand700 = Color(0xFF1A33C4);
  static const brand200Dark = Color(0xFFB4C0FF);
  static const neutral950 = Color(0xFF111318);
  static const neutral900 = Color(0xFF1B1D23);
  static const neutral800 = Color(0xFF2A2D35);
  static const neutral600 = Color(0xFF5B5F6B);
  static const neutral400 = Color(0xFF9CA0AB);
  static const neutral200 = Color(0xFFE4E6EB);
  static const neutral100 = Color(0xFFF3F4F7);
  static const white = Color(0xFFFFFFFF);
  static const red600 = Color(0xFFC62828);
  static const red200 = Color(0xFFFFB4AB);
  static const green600 = Color(0xFF2E7D32);
  static const green300 = Color(0xFF81C784);
  static const amber600 = Color(0xFFB26A00);
  static const amber300 = Color(0xFFFFCA6B);
}

// Layer 2: semantic tokens per brightness. Only component_themes/ and the
// ThemeExtension below read these — widgets use `context.colors` /
// `context.appColors` so they stay correct in light and dark mode.
abstract final class AppColorsLight {
  static const primary = _Palette.brand500;
  static const onPrimary = _Palette.white;
  static const primaryContainer = _Palette.brand100;
  static const onPrimaryContainer = _Palette.brand700;
  static const surface = _Palette.white;
  static const onSurface = _Palette.neutral900;
  static const onSurfaceVariant = _Palette.neutral600;
  static const surfaceContainer = _Palette.neutral100;
  static const outline = _Palette.neutral400;
  static const outlineVariant = _Palette.neutral200;
  static const error = _Palette.red600;
  static const onError = _Palette.white;
  static const success = _Palette.green600;
  static const warning = _Palette.amber600;
}

abstract final class AppColorsDark {
  static const primary = _Palette.brand200Dark;
  static const onPrimary = _Palette.neutral950;
  static const primaryContainer = _Palette.brand700;
  static const onPrimaryContainer = _Palette.brand100;
  static const surface = _Palette.neutral950;
  static const onSurface = _Palette.neutral100;
  static const onSurfaceVariant = _Palette.neutral400;
  static const surfaceContainer = _Palette.neutral800;
  static const outline = _Palette.neutral600;
  static const outlineVariant = _Palette.neutral800;
  static const error = _Palette.red200;
  static const onError = _Palette.neutral950;
  static const success = _Palette.green300;
  static const warning = _Palette.amber300;
}

/// Semantic colours Material's ColorScheme has no slot for.
/// Read with `context.appColors.success`.
@immutable
class AppColorExtension extends ThemeExtension<AppColorExtension> {
  const AppColorExtension({required this.success, required this.warning});

  static const light = AppColorExtension(
    success: AppColorsLight.success,
    warning: AppColorsLight.warning,
  );

  static const dark = AppColorExtension(
    success: AppColorsDark.success,
    warning: AppColorsDark.warning,
  );

  final Color success;
  final Color warning;

  @override
  AppColorExtension copyWith({Color? success, Color? warning}) =>
      AppColorExtension(
        success: success ?? this.success,
        warning: warning ?? this.warning,
      );

  @override
  AppColorExtension lerp(AppColorExtension? other, double t) {
    if (other == null) return this;
    return AppColorExtension(
      success: Color.lerp(success, other.success, t)!,
      warning: Color.lerp(warning, other.warning, t)!,
    );
  }
}

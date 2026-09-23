import 'package:flutter/material.dart';

import 'tokens/app_colors.dart';

/// The only way widgets read theme values:
///   context.colors.primary        (Material ColorScheme roles)
///   context.appColors.success     (brand roles Material lacks)
///   context.textTheme.titleLarge  (AppTypography via TextTheme)
extension ThemeContextExt on BuildContext {
  ThemeData get theme => Theme.of(this);

  ColorScheme get colors => theme.colorScheme;

  TextTheme get textTheme => theme.textTheme;

  AppColorExtension get appColors =>
      theme.extension<AppColorExtension>() ?? AppColorExtension.light;
}

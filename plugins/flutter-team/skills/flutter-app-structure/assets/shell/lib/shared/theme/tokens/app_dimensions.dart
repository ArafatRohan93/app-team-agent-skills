/// Spacing, radius and size tokens on an 8px base grid.
/// Widgets never use raw numbers for padding, gaps or radii.
abstract final class AppDimensions {
  // --- Spacing ---
  static const spacingXxs = 2.0;
  static const spacingXs = 4.0;
  static const spacingSm = 8.0;
  static const spacingMd = 12.0;
  static const spacingLg = 16.0;
  static const spacingXl = 24.0;
  static const spacing2xl = 32.0;
  static const spacing3xl = 48.0;

  /// Horizontal screen margin.
  static const screenPadding = spacingXl;

  // --- Radius ---
  static const radiusSm = 6.0;
  static const radiusMd = 12.0;
  static const radiusLg = 16.0;
  static const radiusXl = 24.0;
  static const radiusFull = 9999.0;

  // --- Component sizes ---
  static const buttonHeight = 48.0;
  static const inputHeight = 48.0;
  static const iconSm = 16.0;
  static const iconMd = 24.0;
  static const iconLg = 32.0;
}

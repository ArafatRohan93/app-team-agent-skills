import 'package:{{package}}/core/image_resolver/image_resource.dart';

import 'svg_image_resource.dart';

const String _iconPath = 'assets/icons';
const String _imagePath = 'assets/images';

/// The registry of every bundled image. Feature code renders images only
/// through these constants:
///
///     ImageResourceResolver.logo.getImageWidget(height: 48)
///
/// To add one: drop the file in assets/icons/ or assets/images/ (both are
/// declared in pubspec.yaml), then add a `static const` here, grouped by
/// folder and named after the file in lowerCamelCase.
abstract final class ImageResourceResolver {
  // --- Icons (assets/icons/) ---
  static const SVGImageResource icPlaceholder = SVGImageResource(
    '$_iconPath/ic_placeholder.svg',
  );

  // --- Images (assets/images/) ---
  static const SVGImageResource logo = SVGImageResource(
    '$_imagePath/logo.svg',
  );

  /// Every declared resource — test/shared/image_resolver checks each path
  /// exists, so keep this list in sync. (Use PNGImageResource for raster files.)
  static const List<ImageResource> all = [icPlaceholder, logo];
}

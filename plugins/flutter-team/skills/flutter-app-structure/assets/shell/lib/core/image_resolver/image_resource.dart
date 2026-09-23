import 'package:flutter/widgets.dart';

/// A bundled image asset that knows how to render itself.
/// Declare instances only in `ImageResourceResolver`
/// (shared/image_resolver/image_resource_resolver.dart).
abstract interface class ImageResource {
  String get path;

  Widget getImageWidget({
    double? width,
    double? height,
    BoxFit? boxFit,
    Color? color,
  });
}

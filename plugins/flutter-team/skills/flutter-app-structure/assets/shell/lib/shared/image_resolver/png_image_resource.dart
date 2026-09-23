import 'package:flutter/widgets.dart';
import 'package:{{package}}/core/image_resolver/image_resource.dart';

class PNGImageResource implements ImageResource {
  const PNGImageResource(this.path);

  @override
  final String path;

  /// For APIs that need an [ImageProvider] (DecorationImage, CircleAvatar…).
  AssetImage get provider => AssetImage(path);

  @override
  Widget getImageWidget({
    double? width,
    double? height,
    BoxFit? boxFit,
    Color? color,
  }) => Image.asset(
    path,
    width: width,
    height: height,
    fit: boxFit,
    color: color,
  );
}

import 'package:flutter/widgets.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:{{package}}/core/image_resolver/image_resource.dart';

class SVGImageResource implements ImageResource {
  const SVGImageResource(this.path);

  @override
  final String path;

  @override
  Widget getImageWidget({
    double? width,
    double? height,
    BoxFit? boxFit,
    Color? color,
  }) => SvgPicture.asset(
    path,
    width: width,
    height: height,
    fit: boxFit ?? BoxFit.contain,
    colorFilter: color != null ? ColorFilter.mode(color, BlendMode.srcIn) : null,
  );
}

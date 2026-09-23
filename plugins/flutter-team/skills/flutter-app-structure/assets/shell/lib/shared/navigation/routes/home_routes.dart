import 'package:{{package}}/core/navigation/app_route_data.dart';
import 'package:{{package}}/shared/navigation/app_route.dart';

// One file per feature: shared/navigation/routes/<feature>_routes.dart.
// Route classes live here (not in the feature) so any feature can navigate
// to any other without importing it. Fields are primitives only.

final class HomeRoute extends AppRouteData {
  const HomeRoute();

  @override
  String get pathTemplate => AppRoute.home.path;

  static HomeRoute? fromParams(
    Map<String, String> path,
    Map<String, String> query,
  ) => const HomeRoute();
}

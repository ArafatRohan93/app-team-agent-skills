import 'package:go_router/go_router.dart';
import 'package:{{package}}/core/logger/app_logger.dart';
import 'package:{{package}}/core/navigation/app_navigator.dart';
import 'package:{{package}}/core/navigation/app_route_data.dart';

class GoRouterNavigator implements AppNavigator {
  const GoRouterNavigator(this._router, {required AppLogger logger})
    : _logger = logger;

  final GoRouter _router;
  final AppLogger _logger;

  @override
  Future<T?> push<T extends Object?>(AppRouteData route, {Object? extra}) =>
      _accept(route)
      ? _router.push<T>(route.location, extra: extra)
      : Future<T?>.value();

  @override
  void replace(AppRouteData route, {Object? extra}) {
    if (_accept(route)) _router.replace<Object?>(route.location, extra: extra);
  }

  @override
  void popAllThenPush(AppRouteData route, {Object? extra}) {
    if (_accept(route)) _router.go(route.location, extra: extra);
  }

  @override
  void pop<T extends Object?>([T? result]) => _router.pop<T>(result);

  @override
  bool canPop() => _router.canPop();

  @override
  Future<T?> pushLocation<T extends Object?>(String location) =>
      _router.push<T>(location);

  @override
  void popAllThenPushLocation(String location) => _router.go(location);

  /// Push-time guard: broken route data never reaches the router. Fails
  /// loudly in debug (assert) and is logged + ignored in release.
  bool _accept(AppRouteData route) {
    if (route.isComplete && route.isValid) return true;
    _logger.warning('Blocked navigation to invalid route: $route');
    assert(false, 'Invalid route data: $route');
    return false;
  }
}

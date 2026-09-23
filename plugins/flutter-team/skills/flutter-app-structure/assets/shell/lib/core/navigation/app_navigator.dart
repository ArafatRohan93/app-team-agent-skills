import 'app_route_data.dart';

/// Navigation contract. Widgets reach it through `context.nav`
/// (shared/navigation/navigator_scope.dart); coordinators get it from DI.
/// Nothing outside shared/navigation/ may import go_router.
///
/// Features navigate with typed routes only:
///   context.nav.push(OrderDetailsRoute(orderId: order.id));
/// A route that isn't [AppRouteData.isValid] is refused (asserts in debug).
abstract interface class AppNavigator {
  /// Pushes [route] on top. Stack: [A, B] → [A, B, C].
  /// Completes with the value the pushed screen passes to [pop].
  /// [extra] is an optional in-memory speed-up only (e.g. an already-loaded
  /// model) — the screen must work without it.
  Future<T?> push<T extends Object?>(AppRouteData route, {Object? extra});

  /// Replaces the top screen. Stack: [A, B] → [A, C]
  void replace(AppRouteData route, {Object? extra});

  /// Clears the stack and shows [route]. Stack: [A, B, C] → [D]
  void popAllThenPush(AppRouteData route, {Object? extra});

  /// Pops the top screen, optionally returning [result]. Stack: [A, B] → [A]
  void pop<T extends Object?>([T? result]);

  /// True when [pop] is safe (more than one screen on the stack).
  bool canPop();

  /// Raw URL variants for deep links and notification payloads. Only
  /// coordinators use these; the router still parses and validates the URL
  /// before building, so a broken link shows InvalidRouteScreen.
  Future<T?> pushLocation<T extends Object?>(String location);

  void popAllThenPushLocation(String location);
}

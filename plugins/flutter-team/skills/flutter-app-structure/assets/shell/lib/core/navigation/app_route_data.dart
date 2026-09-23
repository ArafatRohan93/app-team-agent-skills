/// Typed description of one navigation target. Features navigate only with
/// these: `context.nav.push(OrderDetailsRoute(orderId: order.id))`.
///
/// Subclasses live in shared/navigation/routes/, hold primitive fields only
/// (ids, numbers, bools, dates, enums declared next to the route) and provide
/// `static XRoute? fromParams(path, query)` — the single place URL strings
/// are parsed back into the route.
abstract class AppRouteData {
  const AppRouteData();

  /// The go_router path template, e.g. `/orders/:id` (`AppRoute.x.path`).
  String get pathTemplate;

  Map<String, String> get pathParameters => const {};

  Map<String, String> get queryParameters => const {};

  /// Rules the type system can't express (non-empty id, positive page, …).
  /// AppNavigator refuses to navigate to a route that isn't valid.
  bool get isValid => true;

  /// False when [pathTemplate] still has a `:param` that [pathParameters]
  /// didn't fill — a bug in the route class.
  bool get isComplete => !_filledPath.contains('/:');

  /// The URL for this route. Every value is escaped, so ids like "a/b"
  /// can't break the path; go_router decodes them again before parsing.
  String get location {
    final query = queryParameters.isEmpty
        ? ''
        : '?${Uri(queryParameters: queryParameters).query}';
    return '$_filledPath$query';
  }

  String get _filledPath => pathParameters.entries.fold(
    pathTemplate,
    (path, e) => path.replaceFirst(':${e.key}', Uri.encodeComponent(e.value)),
  );

  @override
  String toString() => '$runtimeType($location)';
}

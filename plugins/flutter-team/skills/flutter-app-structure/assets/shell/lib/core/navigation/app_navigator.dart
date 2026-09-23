/// Navigation contract. Widgets reach it through `context.nav`
/// (see shared/navigation/navigator_scope.dart); coordinators get it from DI.
/// Nothing outside shared/navigation/ may import go_router.
abstract interface class AppNavigator {
  /// Clears the stack and shows [location]. Stack: [A, B, C] → [D]
  void popAllThenPush(String location, {Object? extra});

  /// Pushes [location] on top. Stack: [A, B] → [A, B, C].
  /// Completes with the value the pushed screen passes to [pop].
  Future<T?> push<T extends Object?>(String location, {Object? extra});

  /// Pops the top screen, optionally returning [result]. Stack: [A, B] → [A]
  void pop<T extends Object?>([T? result]);

  /// Replaces the top screen. Stack: [A, B] → [A, C]
  void replace(String location, {Object? extra});

  /// [popAllThenPush] by route name.
  void popAllThenPushNamed(
    String name, {
    Map<String, String> pathParameters = const {},
    Map<String, dynamic> queryParameters = const {},
    Object? extra,
  });

  /// [push] by route name.
  Future<T?> pushNamed<T extends Object?>(
    String name, {
    Map<String, String> pathParameters = const {},
    Map<String, dynamic> queryParameters = const {},
    Object? extra,
  });

  /// [replace] by route name.
  void replaceNamed(
    String name, {
    Map<String, String> pathParameters = const {},
    Map<String, dynamic> queryParameters = const {},
    Object? extra,
  });

  /// True when [pop] is safe (more than one screen on the stack).
  bool canPop();
}

import 'package:go_router/go_router.dart';
import 'package:{{package}}/core/navigation/app_navigator.dart';

class GoRouterNavigator implements AppNavigator {
  const GoRouterNavigator(this._router);

  final GoRouter _router;

  @override
  void popAllThenPush(String location, {Object? extra}) =>
      _router.go(location, extra: extra);

  @override
  Future<T?> push<T extends Object?>(String location, {Object? extra}) =>
      _router.push<T>(location, extra: extra);

  @override
  void pop<T extends Object?>([T? result]) => _router.pop<T>(result);

  @override
  void replace(String location, {Object? extra}) =>
      _router.replace<Object?>(location, extra: extra);

  @override
  void popAllThenPushNamed(
    String name, {
    Map<String, String> pathParameters = const {},
    Map<String, dynamic> queryParameters = const {},
    Object? extra,
  }) => _router.goNamed(
    name,
    pathParameters: pathParameters,
    queryParameters: queryParameters,
    extra: extra,
  );

  @override
  Future<T?> pushNamed<T extends Object?>(
    String name, {
    Map<String, String> pathParameters = const {},
    Map<String, dynamic> queryParameters = const {},
    Object? extra,
  }) => _router.pushNamed<T>(
    name,
    pathParameters: pathParameters,
    queryParameters: queryParameters,
    extra: extra,
  );

  @override
  void replaceNamed(
    String name, {
    Map<String, String> pathParameters = const {},
    Map<String, dynamic> queryParameters = const {},
    Object? extra,
  }) => _router.replaceNamed<Object?>(
    name,
    pathParameters: pathParameters,
    queryParameters: queryParameters,
    extra: extra,
  );

  @override
  bool canPop() => _router.canPop();
}

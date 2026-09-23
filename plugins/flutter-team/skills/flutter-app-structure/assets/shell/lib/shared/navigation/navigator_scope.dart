import 'package:flutter/widgets.dart';
import 'package:{{package}}/core/navigation/app_navigator.dart';

/// Exposes the [AppNavigator] to the widget tree. Widgets navigate with
/// `context.nav.push(...)` — never `context.go` / `GoRouter.of(context)`.
class NavigatorScope extends InheritedWidget {
  const NavigatorScope({
    super.key,
    required this.navigator,
    required super.child,
  });

  final AppNavigator navigator;

  static AppNavigator of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<NavigatorScope>();
    if (scope == null) {
      throw FlutterError(
        'NavigatorScope.of() called with a context that does not contain a '
        'NavigatorScope.\nEnsure your widget tree is wrapped with NavigatorScope.',
      );
    }
    return scope.navigator;
  }

  @override
  bool updateShouldNotify(NavigatorScope oldWidget) =>
      navigator != oldWidget.navigator;
}

extension NavigatorScopeExtension on BuildContext {
  AppNavigator get nav => NavigatorScope.of(this);
}

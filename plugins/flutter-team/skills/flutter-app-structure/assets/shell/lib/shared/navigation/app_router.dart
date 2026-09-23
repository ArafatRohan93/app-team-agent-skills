import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:{{package}}/core/config/app_config.dart';
import 'package:{{package}}/core/logger/app_logger.dart';
import 'package:{{package}}/core/navigation/app_navigator.dart';
import 'package:{{package}}/features/home/presentation/screens/home_screen.dart';
import 'package:{{package}}/shared/navigation/app_route.dart';
import 'package:{{package}}/shared/navigation/go_router_navigator.dart';
import 'package:{{package}}/shared/navigation/navigation_observer.dart';
import 'package:{{package}}/shared/navigation/transitions/app_page_transition.dart';

/// The only place that knows about go_router. It owns the route table and
/// exposes an [AppNavigator] for the rest of the app.
class AppRouter {
  AppRouter({required AppConfig config, required AppLogger logger}) {
    _router = GoRouter(
      navigatorKey: GlobalKey<NavigatorState>(debugLabel: 'AppNavigatorKey'),
      debugLogDiagnostics: kDebugMode,
      initialLocation: AppRoute.home.path,
      observers: [AppNavigationObserver(logger)],
      errorBuilder: (_, state) => _RouterErrorScreen(state.error),
      routes: [
        GoRoute(
          path: AppRoute.home.path,
          name: AppRoute.home.name,
          pageBuilder: (_, state) =>
              buildTransitionPage(
                state: state,
                child: HomeScreen(appName: config.appName),
              ),
        ),
      ],
    );
    _navigator = GoRouterNavigator(_router);
  }

  late final GoRouter _router;
  late final AppNavigator _navigator;

  RouterConfig<Object> get routerConfig => _router;

  AppNavigator get navigator => _navigator;
}

class _RouterErrorScreen extends StatelessWidget {
  const _RouterErrorScreen(this.error);

  final Exception? error;

  @override
  Widget build(BuildContext context) =>
      Scaffold(body: Center(child: Text(error?.toString() ?? 'Page not found')));
}

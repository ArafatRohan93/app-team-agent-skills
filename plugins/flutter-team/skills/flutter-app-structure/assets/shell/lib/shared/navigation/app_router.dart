import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:{{package}}/core/config/app_config.dart';
import 'package:{{package}}/core/logger/app_logger.dart';
import 'package:{{package}}/core/navigation/app_navigator.dart';
import 'package:{{package}}/features/home/presentation/screens/home_screen.dart';
import 'package:{{package}}/shared/navigation/app_route.dart';
import 'package:{{package}}/shared/navigation/go_router_navigator.dart';
import 'package:{{package}}/shared/navigation/invalid_route_screen.dart';
import 'package:{{package}}/shared/navigation/navigation_observer.dart';
import 'package:{{package}}/shared/navigation/routes/home_routes.dart';
import 'package:{{package}}/shared/navigation/typed_page.dart';

/// The only place that knows about go_router. It owns the route table and
/// exposes an [AppNavigator] for the rest of the app.
///
/// Every GoRoute uses `path`/`name` from [AppRoute] and a `pageBuilder` that
/// goes through [buildTypedPage] with the route class's `fromParams`.
class AppRouter {
  AppRouter({required AppConfig config, required AppLogger logger}) {
    _router = GoRouter(
      navigatorKey: GlobalKey<NavigatorState>(debugLabel: 'AppNavigatorKey'),
      debugLogDiagnostics: kDebugMode,
      initialLocation: AppRoute.home.path,
      observers: [AppNavigationObserver(logger)],
      errorBuilder: (_, state) {
        logger.warning('No route for ${state.uri}');
        return const InvalidRouteScreen();
      },
      routes: [
        GoRoute(
          path: AppRoute.home.path,
          name: AppRoute.home.name,
          pageBuilder: (_, state) => buildTypedPage(
            state,
            logger: logger,
            parse: HomeRoute.fromParams,
            builder: (_) => HomeScreen(appName: config.appName),
          ),
        ),
      ],
    );
    _navigator = GoRouterNavigator(_router, logger: logger);
  }

  late final GoRouter _router;
  late final AppNavigator _navigator;

  RouterConfig<Object> get routerConfig => _router;

  AppNavigator get navigator => _navigator;
}

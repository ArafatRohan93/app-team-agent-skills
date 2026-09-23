import 'package:flutter/widgets.dart';
import 'package:go_router/go_router.dart';
import 'package:{{package}}/core/logger/app_logger.dart';
import 'package:{{package}}/core/navigation/app_route_data.dart';
import 'package:{{package}}/shared/navigation/invalid_route_screen.dart';
import 'package:{{package}}/shared/navigation/transitions/app_page_transition.dart';

typedef RouteParser<R extends AppRouteData> =
    R? Function(Map<String, String> path, Map<String, String> query);

/// Build-time guard: every GoRoute.pageBuilder goes through this. It parses
/// the URL back into a typed route before the screen is built — deep links
/// and notifications arrive as raw URLs and skip the push-time check — and
/// shows [InvalidRouteScreen] instead of building with broken arguments.
Page<Object?> buildTypedPage<R extends AppRouteData>(
  GoRouterState state, {
  required RouteParser<R> parse,
  required Widget Function(R route) builder,
  required AppLogger logger,
}) {
  final route = parse(state.pathParameters, state.uri.queryParameters);
  if (route == null || !route.isValid) {
    logger.warning('Invalid route arguments: ${state.uri}');
    return buildTransitionPage<Object?>(
      state: state,
      child: const InvalidRouteScreen(),
    );
  }
  return buildTransitionPage<Object?>(state: state, child: builder(route));
}

import 'package:flutter/widgets.dart';
import 'package:{{package}}/core/logger/app_logger.dart';

class AppNavigationObserver extends NavigatorObserver {
  AppNavigationObserver(this._logger);

  final AppLogger _logger;

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) =>
      _logger.debug('NAV push: ${_name(previousRoute)} → ${_name(route)}');

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) =>
      _logger.debug('NAV pop: ${_name(route)} → ${_name(previousRoute)}');

  @override
  void didReplace({Route<dynamic>? newRoute, Route<dynamic>? oldRoute}) =>
      _logger.debug('NAV replace: ${_name(oldRoute)} → ${_name(newRoute)}');

  @override
  void didRemove(Route<dynamic> route, Route<dynamic>? previousRoute) =>
      _logger.debug('NAV remove: ${_name(route)}');

  String _name(Route<dynamic>? route) => route?.settings.name ?? '<unknown>';
}

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:{{package}}/core/navigation/app_navigator.dart';
import 'package:{{package}}/l10n/l10n.dart';
import 'package:{{package}}/shared/navigation/navigator_scope.dart';
import 'package:{{package}}/shared/theme/theme.dart';

import 'mocks.dart';

extension PumpApp on WidgetTester {
  /// Pumps [widget] with the app's theme, localizations and a
  /// [NavigatorScope] (a [MockAppNavigator] unless [navigator] is given),
  /// so `context.l10n`, `context.colors` and `context.nav` all work.
  Future<void> pumpApp(
    Widget widget, {
    AppNavigator? navigator,
    ThemeData? theme,
  }) {
    return pumpWidget(
      NavigatorScope(
        navigator: navigator ?? MockAppNavigator(),
        child: MaterialApp(
          theme: theme ?? AppTheme.light,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: widget,
        ),
      ),
    );
  }
}

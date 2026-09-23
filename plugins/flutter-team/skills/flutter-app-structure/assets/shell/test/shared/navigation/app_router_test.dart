import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:{{package}}/core/config/app_config.dart';
import 'package:{{package}}/core/config/flavor.dart';
import 'package:{{package}}/features/home/presentation/screens/home_screen.dart';
import 'package:{{package}}/l10n/l10n.dart';
import 'package:{{package}}/shared/navigation/app_router.dart';
import 'package:{{package}}/shared/navigation/invalid_route_screen.dart';
import 'package:{{package}}/shared/navigation/navigator_scope.dart';
import 'package:{{package}}/shared/navigation/routes/home_routes.dart';

import '../../helpers/mocks.dart';

const _config = AppConfig(
  flavor: Flavor.development,
  appName: 'Test',
  baseUrl: 'https://example.test',
);

void main() {
  late AppRouter router;

  setUp(() => router = AppRouter(config: _config, logger: MockAppLogger()));

  Future<void> pumpRouter(WidgetTester tester) async {
    await tester.pumpWidget(
      NavigatorScope(
        navigator: router.navigator,
        child: MaterialApp.router(
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          routerConfig: router.routerConfig,
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  group('AppRouter', () {
    testWidgets('starts on the home route', (tester) async {
      await pumpRouter(tester);

      expect(find.byType(HomeScreen), findsOneWidget);
      expect(router.navigator.canPop(), isFalse);
    });

    testWidgets('typed routes push, replace, pop and reset the stack', (
      tester,
    ) async {
      await pumpRouter(tester);

      router.navigator.push<void>(const HomeRoute());
      await tester.pumpAndSettle();
      expect(router.navigator.canPop(), isTrue);

      router.navigator.replace(const HomeRoute());
      await tester.pumpAndSettle();
      router.navigator.pop<void>();
      await tester.pumpAndSettle();
      expect(router.navigator.canPop(), isFalse);

      router.navigator.popAllThenPush(const HomeRoute());
      await tester.pumpAndSettle();
      expect(find.byType(HomeScreen), findsOneWidget);
    });

    testWidgets('an unknown location shows InvalidRouteScreen', (
      tester,
    ) async {
      await pumpRouter(tester);

      router.navigator.popAllThenPushLocation('/does-not-exist');
      await tester.pumpAndSettle();
      expect(find.byType(InvalidRouteScreen), findsOneWidget);

      await tester.tap(find.byType(FilledButton));
      await tester.pumpAndSettle();
      expect(find.byType(HomeScreen), findsOneWidget);
    });
  });
}

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:{{package}}/core/config/app_config.dart';
import 'package:{{package}}/core/config/flavor.dart';
import 'package:{{package}}/features/home/presentation/screens/home_screen.dart';
import 'package:{{package}}/l10n/l10n.dart';
import 'package:{{package}}/shared/navigation/app_route.dart';
import 'package:{{package}}/shared/navigation/app_router.dart';

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
      MaterialApp.router(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        routerConfig: router.routerConfig,
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

    testWidgets('push and pop move through the stack', (tester) async {
      await pumpRouter(tester);

      router.navigator.push<void>('/missing');
      await tester.pumpAndSettle();
      expect(find.byType(HomeScreen), findsNothing);
      expect(router.navigator.canPop(), isTrue);

      router.navigator.pop<void>();
      await tester.pumpAndSettle();
      expect(find.byType(HomeScreen), findsOneWidget);
    });

    testWidgets('named navigation resolves AppRoute names', (tester) async {
      await pumpRouter(tester);

      router.navigator.pushNamed<void>(AppRoute.home.name);
      await tester.pumpAndSettle();
      expect(router.navigator.canPop(), isTrue);

      router.navigator.replaceNamed(AppRoute.home.name);
      await tester.pumpAndSettle();
      router.navigator.replace(AppRoute.home.path);
      await tester.pumpAndSettle();

      router.navigator.popAllThenPushNamed(AppRoute.home.name);
      await tester.pumpAndSettle();
      expect(router.navigator.canPop(), isFalse);

      router.navigator.popAllThenPush(AppRoute.home.path);
      await tester.pumpAndSettle();
      expect(find.byType(HomeScreen), findsOneWidget);
    });
  });
}

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';
import 'package:{{package}}/core/navigation/app_route_data.dart';
import 'package:{{package}}/core/navigation/route_params.dart';
import 'package:{{package}}/l10n/l10n.dart';
import 'package:{{package}}/shared/navigation/invalid_route_screen.dart';
import 'package:{{package}}/shared/navigation/navigator_scope.dart';
import 'package:{{package}}/shared/navigation/routes/home_routes.dart';
import 'package:{{package}}/shared/navigation/typed_page.dart';

import '../../helpers/mocks.dart';

final class _ItemRoute extends AppRouteData {
  const _ItemRoute(this.id);

  final int id;

  @override
  String get pathTemplate => '/items/:id';

  @override
  Map<String, String> get pathParameters => {'id': '$id'};

  @override
  bool get isValid => id > 0;

  static _ItemRoute? fromParams(
    Map<String, String> path,
    Map<String, String> query,
  ) {
    final id = path.integer('id');
    return id == null ? null : _ItemRoute(id);
  }
}

void main() {
  late MockAppLogger logger;
  late MockAppNavigator navigator;
  late GoRouter router;

  setUpAll(() => registerFallbackValue(const HomeRoute()));

  setUp(() {
    logger = MockAppLogger();
    navigator = MockAppNavigator();
    router = GoRouter(
      initialLocation: '/items/1',
      routes: [
        GoRoute(
          path: '/items/:id',
          pageBuilder: (_, state) => buildTypedPage(
            state,
            logger: logger,
            parse: _ItemRoute.fromParams,
            builder: (route) => Text('item ${route.id}'),
          ),
        ),
      ],
    );
  });

  Future<void> pumpAt(WidgetTester tester, String location) async {
    await tester.pumpWidget(
      NavigatorScope(
        navigator: navigator,
        child: MaterialApp.router(
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          routerConfig: router,
        ),
      ),
    );
    router.go(location);
    await tester.pumpAndSettle();
  }

  group('buildTypedPage', () {
    testWidgets('builds the screen with parsed, typed arguments', (
      tester,
    ) async {
      await pumpAt(tester, '/items/42');

      expect(find.text('item 42'), findsOneWidget);
      verifyNever(() => logger.warning(any()));
    });

    testWidgets('shows InvalidRouteScreen when parsing fails', (tester) async {
      await pumpAt(tester, '/items/abc');

      expect(find.byType(InvalidRouteScreen), findsOneWidget);
      verify(() => logger.warning(any())).called(1);
    });

    testWidgets('shows InvalidRouteScreen when the route is not valid', (
      tester,
    ) async {
      await pumpAt(tester, '/items/0');

      expect(find.byType(InvalidRouteScreen), findsOneWidget);
    });

    testWidgets('InvalidRouteScreen sends the user home', (tester) async {
      await pumpAt(tester, '/items/abc');

      await tester.tap(find.byType(FilledButton));

      verify(() => navigator.popAllThenPush(any())).called(1);
    });
  });
}

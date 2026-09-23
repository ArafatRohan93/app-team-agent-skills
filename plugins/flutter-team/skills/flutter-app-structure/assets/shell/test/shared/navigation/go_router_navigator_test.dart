import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';
import 'package:{{package}}/core/navigation/app_route_data.dart';
import 'package:{{package}}/shared/navigation/go_router_navigator.dart';

import '../../helpers/mocks.dart';

final class _ItemRoute extends AppRouteData {
  const _ItemRoute(this.id);

  final String id;

  @override
  String get pathTemplate => '/items/:id';

  @override
  Map<String, String> get pathParameters => {'id': id};

  @override
  bool get isValid => id.isNotEmpty;
}

final class _HomeRoute extends AppRouteData {
  const _HomeRoute();

  @override
  String get pathTemplate => '/';
}

void main() {
  late MockAppLogger logger;
  late GoRouter router;
  late GoRouterNavigator navigator;

  setUp(() {
    logger = MockAppLogger();
    router = GoRouter(
      routes: [
        GoRoute(path: '/', builder: (_, _) => const Text('home')),
        GoRoute(
          path: '/items/:id',
          builder: (_, state) => Text('item ${state.pathParameters['id']}'),
        ),
      ],
    );
    navigator = GoRouterNavigator(router, logger: logger);
  });

  Future<void> pump(WidgetTester tester) async {
    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.pumpAndSettle();
  }

  group('GoRouterNavigator', () {
    testWidgets('push, replace, pop and popAllThenPush a typed route', (
      tester,
    ) async {
      await pump(tester);

      navigator.push<void>(const _ItemRoute('a/b'));
      await tester.pumpAndSettle();
      expect(find.text('item a/b'), findsOneWidget);
      expect(navigator.canPop(), isTrue);

      navigator.replace(const _ItemRoute('2'));
      await tester.pumpAndSettle();
      expect(find.text('item 2'), findsOneWidget);

      navigator.pop<void>();
      await tester.pumpAndSettle();
      expect(find.text('home'), findsOneWidget);

      navigator.popAllThenPush(const _ItemRoute('3'));
      await tester.pumpAndSettle();
      expect(find.text('item 3'), findsOneWidget);
      expect(navigator.canPop(), isFalse);
    });

    testWidgets('raw location variants for coordinators', (tester) async {
      await pump(tester);

      navigator.pushLocation<void>('/items/9');
      await tester.pumpAndSettle();
      expect(find.text('item 9'), findsOneWidget);

      navigator.popAllThenPushLocation('/');
      await tester.pumpAndSettle();
      expect(find.text('home'), findsOneWidget);
    });

    testWidgets('refuses an invalid route, logs it and asserts in debug', (
      tester,
    ) async {
      await pump(tester);

      expect(
        () => navigator.push<void>(const _ItemRoute('')),
        throwsA(isA<AssertionError>()),
      );
      expect(
        () => navigator.popAllThenPush(const _ItemRoute('')),
        throwsA(isA<AssertionError>()),
      );
      expect(
        () => navigator.replace(const _ItemRoute('')),
        throwsA(isA<AssertionError>()),
      );
      await tester.pumpAndSettle();

      verify(() => logger.warning(any())).called(3);
      expect(find.text('home'), findsOneWidget);
      expect(const _HomeRoute().isValid, isTrue);
    });
  });
}

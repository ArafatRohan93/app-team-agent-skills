import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:{{package}}/shared/navigation/navigator_scope.dart';

import '../../helpers/mocks.dart';
import '../../helpers/pump_app.dart';

void main() {
  group('NavigatorScope', () {
    testWidgets('context.nav returns the provided navigator', (tester) async {
      final navigator = MockAppNavigator();
      when(() => navigator.canPop()).thenReturn(false);

      await tester.pumpApp(
        Builder(
          builder: (context) => TextButton(
            onPressed: () => context.nav.pop<void>(),
            child: const Text('back'),
          ),
        ),
        navigator: navigator,
      );
      await tester.tap(find.text('back'));

      verify(() => navigator.pop<void>()).called(1);
    });

    testWidgets('throws a FlutterError when no scope is above', (
      tester,
    ) async {
      late BuildContext captured;
      await tester.pumpWidget(
        Builder(
          builder: (context) {
            captured = context;
            return const SizedBox();
          },
        ),
      );

      expect(() => captured.nav, throwsFlutterError);
    });
  });
}

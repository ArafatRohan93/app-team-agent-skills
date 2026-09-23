import 'package:flutter_test/flutter_test.dart';
import 'package:{{package}}/features/home/presentation/screens/home_screen.dart';

import '../../../../helpers/pump_app.dart';

void main() {
  group('HomeScreen', () {
    testWidgets('shows the localized welcome with the app name', (
      tester,
    ) async {
      await tester.pumpApp(const HomeScreen(appName: 'Demo'));

      expect(find.text('Welcome to Demo'), findsOneWidget);
    });
  });
}

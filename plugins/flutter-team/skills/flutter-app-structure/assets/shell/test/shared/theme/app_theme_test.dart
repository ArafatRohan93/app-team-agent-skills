import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:{{package}}/shared/theme/theme.dart';

import '../../helpers/pump_app.dart';

void main() {
  group('AppTheme', () {
    test('light and dark themes carry the AppColorExtension', () {
      expect(AppTheme.light.brightness, Brightness.light);
      expect(AppTheme.dark.brightness, Brightness.dark);
      expect(AppTheme.light.extension<AppColorExtension>(), isNotNull);
      expect(AppTheme.dark.extension<AppColorExtension>(), isNotNull);
    });

    test('AppColorExtension copyWith and lerp', () {
      const light = AppColorExtension.light;
      const dark = AppColorExtension.dark;

      expect(light.copyWith(success: dark.success).success, dark.success);
      expect(light.copyWith().warning, light.warning);
      expect(light.lerp(dark, 1).success, dark.success);
      expect(light.lerp(null, 0.5), same(light));
    });

    testWidgets('context extensions read from the active theme', (
      tester,
    ) async {
      late BuildContext captured;
      await tester.pumpApp(
        Builder(
          builder: (context) {
            captured = context;
            return const SizedBox();
          },
        ),
        theme: AppTheme.dark,
      );

      expect(captured.colors.brightness, Brightness.dark);
      expect(captured.appColors, AppColorExtension.dark);
      expect(captured.textTheme.bodyMedium, isNotNull);
    });
  });
}

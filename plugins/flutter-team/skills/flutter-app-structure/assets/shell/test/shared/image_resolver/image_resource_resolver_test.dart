import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:{{package}}/shared/image_resolver/image_resource_resolver.dart';

void main() {
  group('ImageResourceResolver', () {
    test('every declared resource points at a bundled file', () {
      for (final resource in ImageResourceResolver.all) {
        expect(
          File(resource.path).existsSync(),
          isTrue,
          reason: '${resource.path} is declared but missing on disk',
        );
      }
    });

    testWidgets('resources render without throwing', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Column(
            children: [
              for (final resource in ImageResourceResolver.all)
                resource.getImageWidget(width: 24, height: 24),
            ],
          ),
        ),
      );

      expect(tester.takeException(), isNull);
    });
  });
}

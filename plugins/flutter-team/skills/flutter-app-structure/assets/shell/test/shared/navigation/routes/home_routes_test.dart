import 'package:flutter_test/flutter_test.dart';
import 'package:{{package}}/shared/navigation/routes/home_routes.dart';

void main() {
  group('HomeRoute', () {
    test('points at / and parses from any params', () {
      const route = HomeRoute();

      expect(route.location, '/');
      expect(
        HomeRoute.fromParams(route.pathParameters, route.queryParameters),
        isA<HomeRoute>(),
      );
    });
  });
}

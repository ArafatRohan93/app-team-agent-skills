import 'package:flutter_test/flutter_test.dart';
import 'package:{{package}}/core/navigation/app_route_data.dart';

final class _ItemRoute extends AppRouteData {
  const _ItemRoute(this.id, {this.query = const {}});

  final String id;
  final Map<String, String> query;

  @override
  String get pathTemplate => '/items/:id';

  @override
  Map<String, String> get pathParameters => {'id': id};

  @override
  Map<String, String> get queryParameters => query;
}

final class _UnfilledRoute extends AppRouteData {
  const _UnfilledRoute();

  @override
  String get pathTemplate => '/items/:id';
}

void main() {
  group('AppRouteData.location', () {
    test('fills and escapes path parameters', () {
      expect(const _ItemRoute('a/b c').location, '/items/a%2Fb%20c');
    });

    test('encodes query parameters and omits "?" when there are none', () {
      expect(
        const _ItemRoute('1', query: {'q': 'x&y=z'}).location,
        '/items/1?q=x%26y%3Dz',
      );
      expect(const _ItemRoute('1').location, '/items/1');
    });
  });

  group('AppRouteData.isComplete', () {
    test('is false while a :param is unfilled', () {
      expect(const _ItemRoute('1').isComplete, isTrue);
      expect(const _UnfilledRoute().isComplete, isFalse);
    });
  });

  test('defaults to valid and prints its location', () {
    expect(const _ItemRoute('1').isValid, isTrue);
    expect(const _ItemRoute('1').toString(), '_ItemRoute(/items/1)');
  });
}

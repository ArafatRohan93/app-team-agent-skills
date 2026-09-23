import 'package:flutter_test/flutter_test.dart';
import 'package:{{package}}/core/network/network_exception.dart';

void main() {
  group('NetworkException.toString', () {
    test('describes each exception type', () {
      expect(
        const ServerNetworkException(
          statusCode: 500,
          errorCode: 'X',
          message: 'm',
        ).toString(),
        contains('500 [X]'),
      );
      expect(
        const ServerNetworkException(statusCode: 500, message: 'm').toString(),
        isNot(contains('[')),
      );
      expect(
        const UnauthorizedNetworkException().toString(),
        contains('Unauthorized'),
      );
      expect(const TimeoutNetworkException().toString(), contains('Timeout'));
      expect(
        const ConnectionNetworkException().toString(),
        contains('Connection'),
      );
      expect(
        const UnknownNetworkException(message: 'boom').toString(),
        contains('boom'),
      );
    });
  });
}

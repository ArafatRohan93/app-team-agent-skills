import 'package:flutter_test/flutter_test.dart';
import 'package:{{package}}/core/domain/failures/failure.dart';
import 'package:{{package}}/core/network/network_exception.dart';
import 'package:{{package}}/core/network/network_exception_ext.dart';

void main() {
  group('NetworkExceptionToFailure.toFailure', () {
    test('maps ServerNetworkException to ServerFailure with code and message', () {
      const exception = ServerNetworkException(
        statusCode: 400,
        errorCode: 'BAD_INPUT',
        message: 'Bad input',
      );

      final failure = exception.toFailure();

      expect(
        failure,
        isA<ServerFailure>()
            .having((f) => f.errorCode, 'errorCode', 'BAD_INPUT')
            .having((f) => f.message, 'message', 'Bad input'),
      );
    });

    test('maps UnauthorizedNetworkException to UnauthorizedFailure', () {
      expect(
        const UnauthorizedNetworkException().toFailure(),
        isA<UnauthorizedFailure>(),
      );
    });

    test('maps timeout and connection errors to NetworkFailure', () {
      expect(
        const TimeoutNetworkException().toFailure(),
        isA<NetworkFailure>(),
      );
      expect(
        const ConnectionNetworkException().toFailure(),
        isA<NetworkFailure>(),
      );
    });

    test('maps UnknownNetworkException to UnknownFailure', () {
      expect(
        const UnknownNetworkException(message: 'boom').toFailure(),
        isA<UnknownFailure>().having((f) => f.message, 'message', 'boom'),
      );
    });
  });
}

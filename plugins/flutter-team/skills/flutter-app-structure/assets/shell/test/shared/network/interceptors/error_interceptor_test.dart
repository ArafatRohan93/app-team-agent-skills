import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:{{package}}/core/network/network_exception.dart';
import 'package:{{package}}/shared/network/interceptors/error_interceptor.dart';

final _options = RequestOptions(path: '/test');

DioException _dioError(DioExceptionType type, {int? status, Object? data}) =>
    DioException(
      requestOptions: _options,
      type: type,
      response: status == null
          ? null
          : Response<dynamic>(
              requestOptions: _options,
              statusCode: status,
              data: data,
            ),
    );

void main() {
  group('ErrorInterceptor.toNetworkException', () {
    test('maps timeouts to TimeoutNetworkException', () {
      for (final type in [
        DioExceptionType.connectionTimeout,
        DioExceptionType.sendTimeout,
        DioExceptionType.receiveTimeout,
      ]) {
        expect(
          ErrorInterceptor.toNetworkException(_dioError(type)),
          isA<TimeoutNetworkException>(),
        );
      }
    });

    test('maps connectionError to ConnectionNetworkException', () {
      expect(
        ErrorInterceptor.toNetworkException(
          _dioError(DioExceptionType.connectionError),
        ),
        isA<ConnectionNetworkException>(),
      );
    });

    test('maps 401 to UnauthorizedNetworkException', () {
      expect(
        ErrorInterceptor.toNetworkException(
          _dioError(DioExceptionType.badResponse, status: 401),
        ),
        isA<UnauthorizedNetworkException>(),
      );
    });

    test('parses error code and message from a bad response body', () {
      final result = ErrorInterceptor.toNetworkException(
        _dioError(
          DioExceptionType.badResponse,
          status: 422,
          data: {'error': 'INVALID', 'message': 'Invalid name'},
        ),
      );

      expect(
        result,
        isA<ServerNetworkException>()
            .having((e) => e.statusCode, 'statusCode', 422)
            .having((e) => e.errorCode, 'errorCode', 'INVALID')
            .having((e) => e.message, 'message', 'Invalid name'),
      );
    });

    test('falls back to a generic message for non-JSON bodies', () {
      final result = ErrorInterceptor.toNetworkException(
        _dioError(DioExceptionType.badResponse, status: 500, data: 'oops'),
      );

      expect(
        result,
        isA<ServerNetworkException>().having(
          (e) => e.message,
          'message',
          'Server error',
        ),
      );
    });

    test('maps anything else to UnknownNetworkException', () {
      expect(
        ErrorInterceptor.toNetworkException(_dioError(DioExceptionType.cancel)),
        isA<UnknownNetworkException>(),
      );
    });
  });
}

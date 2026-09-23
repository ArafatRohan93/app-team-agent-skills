import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:{{package}}/shared/network/interceptors/logging_interceptor.dart';

import '../../../helpers/mocks.dart';

class _MockRequestHandler extends Mock implements RequestInterceptorHandler {}

class _MockResponseHandler extends Mock implements ResponseInterceptorHandler {}

class _MockErrorHandler extends Mock implements ErrorInterceptorHandler {}

final _options = RequestOptions(path: '/items', method: 'GET');

void main() {
  late MockAppLogger logger;
  late LoggingInterceptor interceptor;

  setUp(() {
    logger = MockAppLogger();
    interceptor = LoggingInterceptor(logger: logger);
  });

  group('LoggingInterceptor', () {
    test('logs requests and forwards them', () {
      final handler = _MockRequestHandler();

      interceptor.onRequest(_options, handler);

      verify(() => logger.debug(any())).called(1);
      verify(() => handler.next(_options)).called(1);
    });

    test('logs responses and forwards them', () {
      final handler = _MockResponseHandler();
      final response = Response<dynamic>(
        requestOptions: _options,
        statusCode: 200,
      );

      interceptor.onResponse(response, handler);

      verify(() => logger.debug(any())).called(1);
      verify(() => handler.next(response)).called(1);
    });

    test('logs errors and forwards them', () {
      final handler = _MockErrorHandler();
      final error = DioException(requestOptions: _options);

      interceptor.onError(error, handler);

      verify(() => logger.error(any(), any(), any())).called(1);
      verify(() => handler.next(error)).called(1);
    });
  });
}

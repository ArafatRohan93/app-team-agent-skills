import 'package:dio/dio.dart';
import 'package:{{package}}/core/logger/app_logger.dart';

class LoggingInterceptor extends Interceptor {
  const LoggingInterceptor({required AppLogger logger}) : _logger = logger;

  final AppLogger _logger;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    _logger.debug('[→] ${options.method} ${options.uri}\n[Data:] ${options.data}');
    handler.next(options);
  }

  @override
  void onResponse(
    Response<dynamic> response,
    ResponseInterceptorHandler handler,
  ) {
    _logger.debug(
      '[←] ${response.statusCode} ${response.requestOptions.uri}\n[Data:] ${response.data}',
    );
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    final statusCode = err.response?.statusCode;
    _logger.error(
      '[✗] ${statusCode != null ? '$statusCode ' : ''}${err.requestOptions.uri}',
      err.error ?? err,
      err.stackTrace,
    );
    handler.next(err);
  }
}

import 'package:dio/dio.dart';
import 'package:{{package}}/core/network/network_exception.dart';

/// Converts every [DioException] into a typed [NetworkException] carried in
/// `DioException.error`, which DioNetworkClient surfaces as
/// `NetworkResponse.error`.
///
/// Expects error bodies shaped like `{"error": "CODE", "message": "..."}` —
/// adjust [_parseServerError] to your backend's contract.
class ErrorInterceptor extends Interceptor {
  const ErrorInterceptor();

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    handler.next(
      DioException(
        requestOptions: err.requestOptions,
        response: err.response,
        type: err.type,
        error: toNetworkException(err),
        stackTrace: err.stackTrace,
      ),
    );
  }

  static NetworkException toNetworkException(DioException e) =>
      switch (e.type) {
        DioExceptionType.connectionTimeout ||
        DioExceptionType.sendTimeout ||
        DioExceptionType.receiveTimeout => const TimeoutNetworkException(),
        DioExceptionType.connectionError => const ConnectionNetworkException(),
        DioExceptionType.badResponse => _parseServerError(e),
        _ => UnknownNetworkException(message: e.message ?? 'Unknown error'),
      };

  static NetworkException _parseServerError(DioException e) {
    final statusCode = e.response?.statusCode ?? -1;
    if (statusCode == 401) return const UnauthorizedNetworkException();

    final data = e.response?.data;
    String? errorCode;
    var message = 'Server error';
    if (data is Map<String, dynamic>) {
      errorCode = data['error'] as String?;
      final serverMessage = data['message'] as String?;
      if (serverMessage != null && serverMessage.isNotEmpty) {
        message = serverMessage;
      }
    }

    return ServerNetworkException(
      statusCode: statusCode,
      errorCode: errorCode,
      message: message,
    );
  }
}

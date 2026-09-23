import 'network_exception.dart';

class NetworkResponse {
  const NetworkResponse({
    this.jsonResponse,
    this.requestHeaders,
    this.responseHeaders,
    this.requestURL,
    this.error,
    this.statusCode = 0,
  });

  final String? jsonResponse;
  final Map<String, String>? requestHeaders;
  final Map<String, List<String>>? responseHeaders;
  final String? requestURL;
  final NetworkException? error;
  final int statusCode;

  bool get isSuccess => error == null;
}

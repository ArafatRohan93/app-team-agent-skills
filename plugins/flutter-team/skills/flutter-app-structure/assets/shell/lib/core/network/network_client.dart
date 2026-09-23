import 'network_response.dart';

/// HTTP contract every data source depends on. Implementations must never
/// throw for HTTP/transport errors — they return [NetworkResponse.error].
abstract interface class NetworkClient {
  Future<NetworkResponse> get(
    String path, {
    Map<String, dynamic>? queryParameters,
    Map<String, String>? headers,
  });

  Future<NetworkResponse> post(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    Map<String, String>? headers,
  });

  Future<NetworkResponse> put(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    Map<String, String>? headers,
  });

  Future<NetworkResponse> patch(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    Map<String, String>? headers,
  });

  Future<NetworkResponse> delete(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    Map<String, String>? headers,
  });
}

import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:{{package}}/core/network/network_client.dart';
import 'package:{{package}}/core/network/network_exception.dart';
import 'package:{{package}}/core/network/network_response.dart';

class DioNetworkClient implements NetworkClient {
  const DioNetworkClient({required Dio dio}) : _dio = dio;

  final Dio _dio;

  @override
  Future<NetworkResponse> get(
    String path, {
    Map<String, dynamic>? queryParameters,
    Map<String, String>? headers,
  }) => _send(
    () => _dio.get<dynamic>(
      path,
      queryParameters: queryParameters,
      options: Options(headers: headers),
    ),
  );

  @override
  Future<NetworkResponse> post(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    Map<String, String>? headers,
  }) => _send(
    () => _dio.post<dynamic>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: Options(headers: headers),
    ),
  );

  @override
  Future<NetworkResponse> put(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    Map<String, String>? headers,
  }) => _send(
    () => _dio.put<dynamic>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: Options(headers: headers),
    ),
  );

  @override
  Future<NetworkResponse> patch(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    Map<String, String>? headers,
  }) => _send(
    () => _dio.patch<dynamic>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: Options(headers: headers),
    ),
  );

  @override
  Future<NetworkResponse> delete(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    Map<String, String>? headers,
  }) => _send(
    () => _dio.delete<dynamic>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: Options(headers: headers),
    ),
  );

  Future<NetworkResponse> _send(
    Future<Response<dynamic>> Function() request,
  ) async {
    try {
      return _toResponse(await request());
    } on DioException catch (e) {
      return _toErrorResponse(e);
    }
  }

  NetworkResponse _toResponse(Response<dynamic> response) {
    final data = response.data;
    return NetworkResponse(
      jsonResponse: switch (data) {
        null => null,
        final String s => s,
        _ => jsonEncode(data),
      },
      requestHeaders: _toStringMap(response.requestOptions.headers),
      responseHeaders: response.headers.map,
      requestURL: response.requestOptions.uri.toString(),
      statusCode: response.statusCode ?? 0,
    );
  }

  NetworkResponse _toErrorResponse(DioException e) => NetworkResponse(
    error: switch (e.error) {
      final NetworkException error => error,
      _ => UnknownNetworkException(message: e.message ?? 'Unknown error'),
    },
    statusCode: e.response?.statusCode ?? 0,
    requestURL: e.requestOptions.uri.toString(),
    requestHeaders: _toStringMap(e.requestOptions.headers),
    responseHeaders: e.response?.headers.map,
  );

  Map<String, String> _toStringMap(Map<String, dynamic> headers) =>
      headers.map((key, value) => MapEntry(key, value.toString()));
}

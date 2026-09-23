import 'package:dio/dio.dart';
import 'package:{{package}}/core/config/app_config.dart';
import 'package:{{package}}/core/logger/app_logger.dart';
import 'package:{{package}}/core/network/network_client.dart';
import 'package:{{package}}/shared/network/dio_network_client.dart';
import 'package:{{package}}/shared/network/interceptors/error_interceptor.dart';
import 'package:{{package}}/shared/network/interceptors/logging_interceptor.dart';

/// Builds the app's [NetworkClient]. Add auth / retry interceptors here —
/// ErrorInterceptor must stay before LoggingInterceptor so logs show the
/// mapped NetworkException.
class NetworkClientFactory {
  const NetworkClientFactory({
    required AppConfig config,
    required AppLogger logger,
    required bool enableLogging,
    List<Interceptor> extraInterceptors = const [],
  }) : _config = config,
       _logger = logger,
       _enableLogging = enableLogging,
       _extraInterceptors = extraInterceptors;

  final AppConfig _config;
  final AppLogger _logger;
  final bool _enableLogging;
  final List<Interceptor> _extraInterceptors;

  NetworkClient create() {
    final dio = Dio(
      BaseOptions(
        baseUrl: _config.baseUrl,
        connectTimeout: _config.connectTimeout,
        receiveTimeout: _config.receiveTimeout,
        sendTimeout: _config.sendTimeout,
        headers: const {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    dio.interceptors.addAll([
      ..._extraInterceptors,
      const ErrorInterceptor(),
      if (_enableLogging) LoggingInterceptor(logger: _logger),
    ]);

    return DioNetworkClient(dio: dio);
  }
}

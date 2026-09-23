import 'package:flutter/foundation.dart';
import 'package:get_it/get_it.dart';
import 'package:{{package}}/core/config/app_config.dart';
import 'package:{{package}}/core/logger/app_logger.dart';
import 'package:{{package}}/core/network/network_client.dart';
import 'package:{{package}}/shared/network/network_client_factory.dart';

void registerNetworkDependencies() {
  final sl = GetIt.instance;

  sl.registerLazySingleton<NetworkClient>(
    () => NetworkClientFactory(
      config: sl<AppConfig>(),
      logger: sl<AppLogger>(),
      enableLogging: !kReleaseMode,
    ).create(),
  );
}

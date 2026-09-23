import 'package:get_it/get_it.dart';
import 'package:{{package}}/core/config/app_config.dart';
import 'package:{{package}}/core/crash/crash_reporter.dart';
import 'package:{{package}}/core/logger/app_logger.dart';
import 'package:{{package}}/core/storage/key_value_storage.dart';
import 'package:{{package}}/shared/crash/console_crash_reporter.dart';
import 'package:{{package}}/shared/logging/console_logger.dart';
import 'package:{{package}}/shared/storage/secure_key_value_storage.dart';

/// App-agnostic services. Swapping an implementation (e.g. Crashlytics for
/// ConsoleCrashReporter) is a one-line change here.
void registerCoreDependencies(AppConfig config) {
  final sl = GetIt.instance;

  sl.registerSingleton<AppConfig>(config);
  sl.registerSingleton<AppLogger>(ConsoleLogger());
  sl.registerSingleton<CrashReporter>(
    ConsoleCrashReporter(logger: sl<AppLogger>()),
  );
  sl.registerLazySingleton<KeyValueStorage>(
    () => const SecureKeyValueStorage(),
  );
}

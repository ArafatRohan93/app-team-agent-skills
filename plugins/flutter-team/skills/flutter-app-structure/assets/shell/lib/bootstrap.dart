import 'dart:async';
import 'dart:ui';

import 'package:flutter/widgets.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:{{package}}/app/app.dart';
import 'package:{{package}}/core/config/app_config.dart';
import 'package:{{package}}/core/crash/crash_reporter.dart';
import 'package:{{package}}/core/logger/app_logger.dart';
import 'package:{{package}}/di/service_locator.dart';
import 'package:{{package}}/shared/bloc/app_bloc_observer.dart';

/// Shared start-up for every flavor: DI → crash reporting → error hooks →
/// Bloc observer → runApp. Flavor entry points only choose the [AppConfig].
Future<void> bootstrap(AppConfig config) async {
  CrashReporter? crashReporter;

  await runZonedGuarded(
    () async {
      WidgetsFlutterBinding.ensureInitialized();

      setupDependencies(config);

      crashReporter = sl<CrashReporter>();
      await crashReporter!.initialize();
      _setupErrorHandlers(crashReporter!);

      Bloc.observer = AppBlocObserver(logger: sl<AppLogger>());

      runApp(App(config: config));
    },
    (error, stack) => crashReporter?.recordError(error, stack, fatal: true),
  );
}

void _setupErrorHandlers(CrashReporter crashReporter) {
  FlutterError.onError = (details) {
    FlutterError.presentError(details);
    crashReporter.recordError(details.exception, details.stack);
  };

  PlatformDispatcher.instance.onError = (error, stack) {
    crashReporter.recordError(error, stack, fatal: true);
    return true;
  };
}

import 'package:get_it/get_it.dart';
import 'package:{{package}}/core/config/app_config.dart';
import 'package:{{package}}/core/logger/app_logger.dart';
import 'package:{{package}}/core/navigation/app_navigator.dart';
import 'package:{{package}}/shared/navigation/app_router.dart';

void registerNavigationDependencies() {
  final sl = GetIt.instance;

  sl.registerLazySingleton<AppRouter>(
    () => AppRouter(config: sl<AppConfig>(), logger: sl<AppLogger>()),
  );
  // Non-widget code (coordinators, services) navigates through this.
  sl.registerLazySingleton<AppNavigator>(() => sl<AppRouter>().navigator);
}

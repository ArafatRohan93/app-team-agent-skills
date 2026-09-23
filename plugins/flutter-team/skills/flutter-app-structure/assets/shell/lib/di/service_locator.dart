import 'package:get_it/get_it.dart';
import 'package:{{package}}/core/config/app_config.dart';
import 'package:{{package}}/di/modules/core_module.dart';
import 'package:{{package}}/di/modules/navigation_module.dart';
import 'package:{{package}}/di/modules/network_module.dart';

final GetIt sl = GetIt.instance;

/// Registers every module. Order matters: a module may only resolve types
/// registered by modules above it. Add feature modules at the bottom.
void setupDependencies(AppConfig config) {
  registerCoreDependencies(config);
  registerNetworkDependencies();
  registerNavigationDependencies();
}

import 'package:flutter_test/flutter_test.dart';
import 'package:{{package}}/core/config/app_config.dart';
import 'package:{{package}}/core/config/flavor.dart';
import 'package:{{package}}/core/crash/crash_reporter.dart';
import 'package:{{package}}/core/logger/app_logger.dart';
import 'package:{{package}}/core/navigation/app_navigator.dart';
import 'package:{{package}}/core/network/network_client.dart';
import 'package:{{package}}/core/storage/key_value_storage.dart';
import 'package:{{package}}/di/service_locator.dart';

void main() {
  const config = AppConfig(
    flavor: Flavor.development,
    appName: 'Test',
    baseUrl: 'https://example.test',
  );

  tearDown(sl.reset);

  test('setupDependencies registers every core contract', () {
    setupDependencies(config);

    expect(sl<AppConfig>(), same(config));
    expect(sl.isRegistered<AppLogger>(), isTrue);
    expect(sl.isRegistered<CrashReporter>(), isTrue);
    expect(sl.isRegistered<KeyValueStorage>(), isTrue);
    expect(sl<NetworkClient>(), isNotNull);
    expect(sl<AppNavigator>(), isNotNull);
  });
}

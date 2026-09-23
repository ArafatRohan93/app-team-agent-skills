import 'package:mocktail/mocktail.dart';
import 'package:{{package}}/core/crash/crash_reporter.dart';
import 'package:{{package}}/core/logger/app_logger.dart';
import 'package:{{package}}/core/navigation/app_navigator.dart';
import 'package:{{package}}/core/network/network_client.dart';
import 'package:{{package}}/core/storage/key_value_storage.dart';

// Shared mocks of the core contracts. Feature-specific mocks stay private
// (`class _MockFoo extends Mock implements Foo {}`) in their own test file.
class MockAppNavigator extends Mock implements AppNavigator {}

class MockAppLogger extends Mock implements AppLogger {}

class MockCrashReporter extends Mock implements CrashReporter {}

class MockNetworkClient extends Mock implements NetworkClient {}

class MockKeyValueStorage extends Mock implements KeyValueStorage {}

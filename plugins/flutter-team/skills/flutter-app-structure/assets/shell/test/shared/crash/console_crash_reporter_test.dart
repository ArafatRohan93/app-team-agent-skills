import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:{{package}}/shared/crash/console_crash_reporter.dart';

import '../../helpers/mocks.dart';

void main() {
  late MockAppLogger logger;
  late ConsoleCrashReporter reporter;

  setUp(() {
    logger = MockAppLogger();
    reporter = ConsoleCrashReporter(logger: logger);
  });

  group('ConsoleCrashReporter.recordError', () {
    test('logs fatal errors at fatal level', () async {
      final error = Exception('boom');

      await reporter.recordError(error, StackTrace.empty, fatal: true);

      verify(() => logger.fatal(any(), error, StackTrace.empty)).called(1);
    });

    test('logs non-fatal errors at error level', () async {
      final error = Exception('boom');

      await reporter.recordError(error, StackTrace.empty);

      verify(() => logger.error(any(), error, StackTrace.empty)).called(1);
    });
  });

  group('ConsoleCrashReporter breadcrumbs', () {
    test('initialize, log, setCustomKey and setUserId go to the logger', () async {
      await reporter.initialize();
      await reporter.log('opened');
      await reporter.setCustomKey('screen', 'home');
      await reporter.setUserId('u1');

      verify(() => logger.info(any())).called(1);
      verify(() => logger.debug(any())).called(2);
    });
  });
}

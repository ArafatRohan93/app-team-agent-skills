import 'package:flutter_test/flutter_test.dart';
import 'package:logger/logger.dart';
import 'package:mocktail/mocktail.dart';
import 'package:{{package}}/shared/logging/console_logger.dart';

class _MockLogger extends Mock implements Logger {}

void main() {
  late _MockLogger logger;
  late ConsoleLogger consoleLogger;

  setUp(() {
    logger = _MockLogger();
    consoleLogger = ConsoleLogger(logger: logger);
  });

  group('ConsoleLogger', () {
    test('forwards each level to the matching Logger method', () {
      final error = Exception('e');

      consoleLogger
        ..verbose('v', error)
        ..debug('d', error)
        ..info('i', error)
        ..warning('w', error)
        ..error('e', error)
        ..fatal('f', error);

      verify(() => logger.t('v', error: error)).called(1);
      verify(() => logger.d('d', error: error)).called(1);
      verify(() => logger.i('i', error: error)).called(1);
      verify(() => logger.w('w', error: error)).called(1);
      verify(() => logger.e('e', error: error)).called(1);
      verify(() => logger.f('f', error: error)).called(1);
    });

    test('builds a default Logger when none is injected', () {
      expect(ConsoleLogger.new, returnsNormally);
    });
  });
}

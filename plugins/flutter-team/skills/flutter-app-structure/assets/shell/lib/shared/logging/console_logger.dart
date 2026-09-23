import 'package:logger/logger.dart';
import 'package:{{package}}/core/logger/app_logger.dart';

class ConsoleLogger implements AppLogger {
  ConsoleLogger({Logger? logger}) : _logger = logger ?? Logger(printer: _printer);

  static final _printer = PrettyPrinter(
    methodCount: 2,
    errorMethodCount: 8,
    lineLength: 120,
  );

  final Logger _logger;

  @override
  void verbose(Object? message, [Object? error, StackTrace? stackTrace]) =>
      _logger.t(message, error: error, stackTrace: stackTrace);

  @override
  void debug(Object? message, [Object? error, StackTrace? stackTrace]) =>
      _logger.d(message, error: error, stackTrace: stackTrace);

  @override
  void info(Object? message, [Object? error, StackTrace? stackTrace]) =>
      _logger.i(message, error: error, stackTrace: stackTrace);

  @override
  void warning(Object? message, [Object? error, StackTrace? stackTrace]) =>
      _logger.w(message, error: error, stackTrace: stackTrace);

  @override
  void error(Object? message, [Object? error, StackTrace? stackTrace]) =>
      _logger.e(message, error: error, stackTrace: stackTrace);

  @override
  void fatal(Object? message, [Object? error, StackTrace? stackTrace]) =>
      _logger.f(message, error: error, stackTrace: stackTrace);
}

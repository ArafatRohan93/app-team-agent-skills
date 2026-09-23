/// Logging contract. Never use `print`/`debugPrint` in app code — inject this.
abstract interface class AppLogger {
  void verbose(Object? message, [Object? error, StackTrace? stackTrace]);

  void debug(Object? message, [Object? error, StackTrace? stackTrace]);

  void info(Object? message, [Object? error, StackTrace? stackTrace]);

  void warning(Object? message, [Object? error, StackTrace? stackTrace]);

  void error(Object? message, [Object? error, StackTrace? stackTrace]);

  void fatal(Object? message, [Object? error, StackTrace? stackTrace]);
}

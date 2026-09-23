/// Error-reporting contract (Crashlytics, Sentry, …). The default
/// implementation logs to the console; swap it in di/modules/core_module.dart.
abstract interface class CrashReporter {
  Future<void> initialize();

  Future<void> recordError(
    Object error,
    StackTrace? stackTrace, {
    bool fatal = false,
  });

  Future<void> log(String message);

  Future<void> setCustomKey(String key, Object value);

  Future<void> setUserId(String? id);
}

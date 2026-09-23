import 'package:{{package}}/core/crash/crash_reporter.dart';
import 'package:{{package}}/core/logger/app_logger.dart';

/// Default [CrashReporter]: forwards everything to [AppLogger].
/// Replace with a Crashlytics/Sentry adapter when the backend is chosen —
/// see the skill's references/abstractions/error-reporting.md.
class ConsoleCrashReporter implements CrashReporter {
  const ConsoleCrashReporter({required AppLogger logger}) : _logger = logger;

  final AppLogger _logger;

  @override
  Future<void> initialize() async {}

  @override
  Future<void> recordError(
    Object error,
    StackTrace? stackTrace, {
    bool fatal = false,
  }) async {
    if (fatal) {
      _logger.fatal('Unhandled error', error, stackTrace);
    } else {
      _logger.error('Recorded error', error, stackTrace);
    }
  }

  @override
  Future<void> log(String message) async => _logger.info('[crash] $message');

  @override
  Future<void> setCustomKey(String key, Object value) async =>
      _logger.debug('[crash] $key = $value');

  @override
  Future<void> setUserId(String? id) async =>
      _logger.debug('[crash] userId = $id');
}

# Error reporting

**Contract:** `lib/core/crash/crash_reporter.dart`. `CrashReporter` has `initialize()`, `recordError(error, stack, {fatal})`, `log(message)`, `setCustomKey(key, value)` and `setUserId(id)`.

**Default implementation:** `lib/shared/crash/console_crash_reporter.dart`. `ConsoleCrashReporter` forwards to `AppLogger`. The shell builds and runs with no accounts. You pick a backend later by swapping one file and one DI line.

## Where it's wired (bootstrap.dart)
- `runZonedGuarded(..., (e, s) => crashReporter.recordError(e, s, fatal: true))` catches uncaught async errors.
- `FlutterError.onError` catches framework errors (non-fatal).
- `PlatformDispatcher.instance.onError` catches platform and isolate errors (fatal).
- `AppBlocObserver.onError` logs errors thrown inside cubits.

## Usage
Feature code rarely calls it directly. Uncaught errors are handled for you. Call it for handled-but-unexpected errors, and to add context:
```dart
_crashReporter.setUserId(user.id);             // after sign-in, null after sign-out
_crashReporter.setCustomKey('flavor', config.flavor.name);
_crashReporter.log('Checkout started');        // breadcrumb
_crashReporter.recordError(e, st);             // handled but should never happen
```

## Swapping in Firebase Crashlytics
Run `flutterfire configure` for each flavor, then `flutter pub add firebase_core firebase_crashlytics`. Add `lib/shared/crash/firebase_crash_reporter.dart`:
```dart
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'package:flutter/foundation.dart';
import 'package:app/core/crash/crash_reporter.dart';
import 'package:app/firebase_options.dart';

class FirebaseCrashReporter implements CrashReporter {
  FirebaseCrashReporter({required bool enabled}) : _enabled = enabled;

  final bool _enabled;
  late FirebaseCrashlytics _crashlytics;

  @override
  Future<void> initialize() async {
    if (Firebase.apps.isEmpty) {
      await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
    }
    _crashlytics = FirebaseCrashlytics.instance;
    await _crashlytics.setCrashlyticsCollectionEnabled(_enabled);
  }

  @override
  Future<void> recordError(Object error, StackTrace? stackTrace, {bool fatal = false}) =>
      _crashlytics.recordError(error, stackTrace, fatal: fatal, printDetails: !kReleaseMode);

  @override
  Future<void> log(String message) => _crashlytics.log(message);

  @override
  Future<void> setCustomKey(String key, Object value) => _crashlytics.setCustomKey(key, value);

  @override
  Future<void> setUserId(String? id) => _crashlytics.setUserIdentifier(id ?? '');
}
```
Then in `di/modules/core_module.dart`:
```dart
sl.registerSingleton<CrashReporter>(FirebaseCrashReporter(enabled: !kDebugMode));
```
With multiple flavors, generate one `firebase_options_<flavor>.dart` per flavor and pass the right options in via `AppConfig`.

## Swapping in Sentry
Run `flutter pub add sentry_flutter` and pass the DSN per flavor with `--dart-define=SENTRY_DSN=…`. Add `lib/shared/crash/sentry_crash_reporter.dart`. The API shown is from sentry_flutter 8.x, so check it against the version you install:
```dart
import 'package:sentry_flutter/sentry_flutter.dart';
import 'package:app/core/crash/crash_reporter.dart';

class SentryCrashReporter implements CrashReporter {
  const SentryCrashReporter({required String dsn, required String environment})
    : _dsn = dsn, _environment = environment;

  final String _dsn;
  final String _environment;

  @override
  Future<void> initialize() => SentryFlutter.init((o) {
    o.dsn = _dsn;
    o.environment = _environment;
  });

  @override
  Future<void> recordError(Object error, StackTrace? stackTrace, {bool fatal = false}) =>
      Sentry.captureException(error, stackTrace: stackTrace);

  @override
  Future<void> log(String message) => Sentry.addBreadcrumb(Breadcrumb(message: message));

  @override
  Future<void> setCustomKey(String key, Object value) =>
      Sentry.configureScope((scope) => scope.setTag(key, value.toString()));

  @override
  Future<void> setUserId(String? id) =>
      Sentry.configureScope((scope) => scope.setUser(id == null ? null : SentryUser(id: id)));
}
```
Register it with `SentryCrashReporter(dsn: const String.fromEnvironment('SENTRY_DSN'), environment: config.flavor.name)`.

In both cases, add the adapter file to `COVERAGE_EXCLUDES` in `scripts/local_ci.sh`. It's a thin SDK wrapper.

## Testing
Use `MockCrashReporter` from `test/helpers/mocks.dart`. Nothing in `features/` should need a real reporter.

## Don'ts
- Don't import `firebase_crashlytics` or `sentry_flutter` anywhere except the adapter file.
- Don't report expected failures such as validation or 4xx responses as errors. Those are `Failure` values.

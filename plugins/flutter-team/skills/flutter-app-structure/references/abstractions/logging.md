# Logger

**Contract:** `lib/core/logger/app_logger.dart`. `AppLogger` has `verbose`, `debug`, `info`, `warning`, `error` and `fatal`, each taking `(message, [error, stackTrace])`.

**Implementation:** `lib/shared/logging/console_logger.dart`. `ConsoleLogger` wraps the `logger` package with a `PrettyPrinter`. It's registered as a singleton in `di/modules/core_module.dart`.

## Where it's already wired
- `LoggingInterceptor`: HTTP requests and responses, non-release builds only.
- `AppNavigationObserver`: route changes.
- `AppBlocObserver`: every Cubit/Bloc transition and error.
- `ConsoleCrashReporter`: recorded errors.

## Usage
Inject it through the constructor, like every other dependency:
```dart
class SyncCoordinator {
  SyncCoordinator({required AppLogger logger}) : _logger = logger;
  final AppLogger _logger;

  Future<void> run() async {
    _logger.info('Sync started');
    try { … } catch (e, st) { _logger.error('Sync failed', e, st); }
  }
}
```

## Levels
| Level | Use for |
|---|---|
| verbose | high-volume tracing (state transitions) |
| debug | developer diagnostics (HTTP bodies, navigation) |
| info | notable app events (sync started, user signed in) |
| warning | recoverable problems (fallback used, retry) |
| error | failed operations the user notices |
| fatal | crashes / unrecoverable state |

## Extending
- **Silence in release builds:** give `ConsoleLogger` a `Logger(filter: ProductionFilter(), level: Level.warning)` in `core_module.dart` when `config.isProduction`.
- **Ship logs somewhere:** write `RemoteLogger implements AppLogger`, or a `CompositeLogger` that fans out to several loggers, and register it instead.

## Testing
Use `MockAppLogger` from `test/helpers/mocks.dart` and verify with `verify(() => logger.error(any(), any(), any()))`.

## Don'ts
- `print` is a lint **error** (`avoid_print`). Don't use `debugPrint` in app code either.
- Never log secrets, tokens or full PII. The logging interceptor prints bodies, so keep it non-release only.

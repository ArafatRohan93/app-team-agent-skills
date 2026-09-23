# Dependency injection

**Files:**
- `lib/di/service_locator.dart`: `final GetIt sl` and `setupDependencies(AppConfig)`.
- `lib/di/modules/<area>_module.dart`: one `void register<Area>Dependencies()` per area: `core`, `network`, `navigation`, then one per feature.

## Rules
- Register **interfaces**, not implementations: `sl.registerLazySingleton<NetworkClient>(() => …)`.
- Use `registerSingleton` for things needed at startup (config, logger, crash reporter) and `registerLazySingleton` for everything else. Data sources are usually constructed inline inside their repository's registration.
- **Cubits are not registered.** They're created in `BlocProvider(create: (_) => XCubit(useCase: sl()))`, in `AppRouter` or at the top of a screen, so their lifetime follows the UI.
- Only three places call `sl`: DI modules, `AppRouter` route builders, and screen-level `BlocProvider.create`. Every class takes its dependencies through named constructor parameters (`const Foo({required Bar bar}) : _bar = bar;`).
- Module order in `setupDependencies` matters. A module may only resolve types registered above it. Feature modules go last.

## Testing
`test/di/service_locator_test.dart` calls `setupDependencies` and resolves each core contract. Extend it when adding modules, and `tearDown(sl.reset)`. Unit tests never touch `sl`. They construct the class under test with mocks.

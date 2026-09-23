# Architecture

## The tree

```
lib/
├── main_development.dart     # each main_<flavor>.dart only picks an AppConfig and calls bootstrap()
├── main_staging.dart
├── main_production.dart
├── bootstrap.dart            # runZonedGuarded → setupDependencies → CrashReporter → error hooks → Bloc.observer → runApp
├── app/app.dart              # App: NavigatorScope + MaterialApp.router (theme, darkTheme, l10n, flavor banner)
├── di/
│   ├── service_locator.dart  # `final GetIt sl`, setupDependencies(config) calls every module in order
│   └── modules/              # core_, network_, navigation_, then <feature>_module.dart
├── core/                     # CONTRACTS ONLY: abstract interfaces, value types, sealed exceptions
│   ├── config/               # Flavor, AppConfig
│   ├── domain/failures/      # sealed Failure (shared by every feature)
│   ├── network/              # NetworkClient, NetworkResponse, sealed NetworkException, toFailure()
│   ├── navigation/           # AppNavigator
│   ├── logger/               # AppLogger
│   ├── crash/                # CrashReporter
│   ├── storage/              # KeyValueStorage
│   └── image_resolver/       # ImageResource
├── shared/                   # IMPLEMENTATIONS of core contracts + app-wide UI
│   ├── network/              # DioNetworkClient, NetworkClientFactory, interceptors/
│   ├── navigation/           # AppRoute, AppRouter, GoRouterNavigator, NavigatorScope (context.nav), transitions/
│   ├── theme/                # theme.dart barrel, app_theme, theme_context_ext, tokens/, component_themes/
│   ├── image_resolver/       # ImageResourceResolver + PNG/SVG resources
│   ├── logging/  crash/  storage/  bloc/ (AppBlocObserver)
│   ├── coordinators/         # (when needed) cross-feature glue reacting to app events
│   ├── widgets/              # reusable, feature-agnostic widgets
│   └── utils/                # pure helpers
├── l10n/                     # arb/app_en.arb, l10n.dart (context.l10n), failure_l10n.dart, gen/ (generated)
└── features/<feature>/
    ├── data/
    │   ├── data_sources/     # <x>_remote_data_source.dart (+ optional <x>_data_source.dart interface), <x>_local_data_source.dart
    │   ├── models/           # JSON models, <action>_<noun>_request.dart / _response.dart
    │   └── repositories/     # <x>_repository_impl.dart
    ├── domain/
    │   ├── models/           # (optional) domain-owned types that aren't wire DTOs
    │   ├── repositories/     # <x>_repository.dart: abstract interface class
    │   └── use_cases/        # <verb>_<noun>_use_case.dart, invoked through call()
    ├── presentation/
    │   ├── cubits/           # <x>_cubit.dart + <x>_state.dart (part of). Several cubits → one subfolder each
    │   ├── screens/          # <x>_screen.dart: route targets
    │   └── widgets/          # feature widgets. Group by sub-area when there are more than ~6 files
    └── utils/                # (optional) feature-local enums/helpers

test/                         # mirrors lib/ exactly
├── helpers/                  # pump_app.dart (tester.pumpApp), mocks.dart (mocks of core contracts)
assets/  icons/  images/  (fonts/)
scripts/local_ci.sh           # format → analyze → test + coverage gate → flavor builds
l10n.yaml  analysis_options.yaml  .vscode/launch.json  README.md
```

A feature only gets the layers it needs. It can be presentation-only (a tab shell), domain-only (use cases that coordinate core services) or data-only. Don't create empty folders to fill out the pattern.

## Dependency rules

| Layer | May import | Must not import |
|---|---|---|
| `core/` | Dart/Flutter SDK, fpdart, other `core/` | `shared/`, `features/`, `di/`, third-party SDKs (Dio, go_router, Firebase…) |
| `shared/` | `core/`, third-party packages | `features/`, except `shared/navigation/app_router.dart` and `shared/coordinators/`, the composition points |
| `features/*/data` | `core/`, own `domain/` contracts and own models | other features, `shared/` implementations when a `core/` contract exists |
| `features/*/domain` | `core/`, own `data/models` | Flutter UI, Dio, `shared/` |
| `features/*/presentation` | own `domain/`, `core/`, `shared/theme`, `shared/widgets`, `shared/navigation` (for `context.nav`), `l10n/` | data sources, `NetworkClient`, other features' cubits |
| `di/`, `bootstrap.dart`, `app/` | everything | — |

When feature A needs something from feature B, move it. A contract goes to `core/`, orchestration goes to `shared/coordinators/`, and a reusable widget goes to `shared/widgets/`.

## Core idioms

1. **Errors are values.** Data sources return `Either<NetworkException, T>`. Repositories `mapLeft((e) => e.toFailure())` into `Either<Failure, T>`. Use cases and cubits `fold`. `Failure` and `NetworkException` are `sealed`, so every `switch` is exhaustive.
2. **Interfaces are `abstract interface class`.** Implementations are `<Tech><Name>` in `shared/` (`DioNetworkClient`, `ConsoleCrashReporter`) or `<Name>Impl` in features (`OrderRepositoryImpl`).
3. **Constructor injection** uses named params and private fields: `const Foo({required Bar bar}) : _bar = bar; final Bar _bar;`. See [abstractions/dependency-injection.md](abstractions/dependency-injection.md).
4. **Use cases** hold business rules (page sizes, "not found → empty", sequencing) and are invoked through `call()`.
5. **Cubit state** is a `sealed class XState` in a `part of` file, with `XInitial / XLoading / XLoaded / XError`. Screens render it with an exhaustive `switch (state)`. `XError` carries the `Failure`, and the widget shows `failure.localizedMessage(context.l10n)`.
6. **Navigation** goes through `context.nav.*` and paths come from the `AppRoute` enum. See [abstractions/navigation.md](abstractions/navigation.md).
7. **Theme** is read through `context.colors`, `context.appColors`, `context.textTheme` and `AppDimensions`. See [abstractions/theme.md](abstractions/theme.md).
8. **Images** are declared only in `ImageResourceResolver` and drawn with `.getImageWidget()`. See [abstractions/images.md](abstractions/images.md).
9. **Strings** come from `context.l10n`. See [abstractions/localization.md](abstractions/localization.md).
10. **Constant holders** are `abstract final class` (`StorageKeys`, `AppDimensions`, `AppTypography`).
11. **Imports** are absolute `package:<app>/...`. Relative imports are only OK inside one small folder, such as `shared/theme/`.

## Naming

- File suffixes: `_data_source`, `_remote_data_source`, `_local_data_source`, `_repository`, `_repository_impl`, `_use_case`, `_cubit`, `_state`, `_screen`, `_module`, `_coordinator`, `_service`, `_exception`, `_request`, `_response`, `_test`.
- Classes: `GetOrdersUseCase`, `OrderRemoteDataSource`, `OrdersCubit`, `OrdersScreen`. The DI function is `registerOrdersDependencies()` in `di/modules/orders_module.dart`.
- Features are short nouns (`orders`, `profile`). Classes inside can use a more specific noun (`Order*` in `orders/`).
- l10n keys: `<feature><Thing>` or `common<Thing>`.

## Where does this go?

| Thing | Location |
|---|---|
| Wrapper around a package (Dio, Firebase, secure storage…) | contract in `core/<area>/`, implementation in `shared/<area>/`, registered in `di/modules/` |
| JSON request/response shape | `features/<f>/data/models/` |
| Business rule (limits, fallbacks, ordering, validation) | `features/<f>/domain/use_cases/` |
| Widget used by 2+ features | `shared/widgets/` |
| Widget used by one feature | `features/<f>/presentation/widgets/` |
| Glue between features triggered by app events (sign-in, push tap, deep link) | `shared/coordinators/<x>_coordinator.dart` with `initialize()`/`dispose()`, started from `bootstrap.dart` |
| Route path / route builder | `AppRoute` enum / `AppRouter` |
| Colours, spacing, text styles | `shared/theme/tokens/` |
| Storage key | `shared/storage/storage_keys.dart` |
| User-visible string | `lib/l10n/arb/app_en.arb` |
| Environment-specific value | `AppConfig` + `main_<flavor>.dart` |

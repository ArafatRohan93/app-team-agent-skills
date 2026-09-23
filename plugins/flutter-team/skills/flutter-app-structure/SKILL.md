---
name: flutter-app-structure
description: Team standard for Flutter apps. It bootstraps an empty `flutter create` project into a production shell with native flavors (dev/staging/prod), clean architecture (core contracts / shared implementations / feature data-domain-presentation), GetIt DI, Cubit state management, fpdart Either errors, go_router behind an AppNavigator, localization, theme tokens, network/logger/crash-reporter/storage/image-resolver abstractions, tests, a local CI script and a README. It also scaffolds features and defines the conventions for existing apps. Use it whenever someone starts a new Flutter app or project shell, adds a feature, screen, route, API call, service, SDK integration, image, string or theme value, asks where a file belongs or how to use the theme, navigation, network, logging or error-reporting layers, or reviews or refactors Flutter code for architecture, even if they never say "structure" or "template".
---

# Flutter App Structure

This skill packages the team's Flutter conventions, taken from the production `ruvy_app` project, plus the most useful parts of what Very Good CLI provides. It has two entry points:

- **Empty or new project** → follow [Bootstrap a new app](#bootstrap-a-new-app). A script builds the whole shell.
- **Existing project** → follow the conventions in `references/`. Use `scripts/scaffold_feature.py` for new features.

All paths below are relative to this skill's directory. The scripts need only `python3` (plus `ruby` with the `xcodeproj` gem for iOS flavors) and a Flutter SDK. They detect `fvm` automatically.

## Before any work

1. Read `pubspec.yaml` for the package name. Every import is `package:<name>/...`.
2. Detect how Flutter is invoked. If there's a `.fvmrc` or `.fvm/` in the project or its parent, prefix every command with `fvm` (`fvm flutter test`).
3. Decide which entry point applies. An empty project is still the `flutter create` counter app: `lib/main.dart` contains `MyHomePage` and there's no `lib/core/`.

## Bootstrap a new app

Read `references/bootstrap.md`, then:

```bash
# if there is no project yet (ask for the org and app name when unknown)
flutter create --org com.acme --project-name acme_wallet --platforms android,ios acme_wallet

python3 scripts/bootstrap_app.py --root acme_wallet --app-name "Acme Wallet" --dry-run   # preview
python3 scripts/bootstrap_app.py --root acme_wallet --app-name "Acme Wallet" --description "…"
cd acme_wallet && scripts/local_ci.sh          # format, analyze, tests + coverage, Android & iOS flavor builds
```

The bootstrap copies `assets/shell/` (real, compiling source: the single source of truth for every abstraction), adds dependencies, configures l10n, and adds Android and iOS flavors. It finishes with `flutter analyze` and `flutter test`, and it is idempotent. Don't hand-write shell files when the script can produce them. If a step fails, fix the cause and re-run it.

When it's done, tell the user what's left to them: real API base URLs in `lib/main_<flavor>.dart`, the crash-reporting backend (`references/abstractions/error-reporting.md`), app icons and signing.

## Work in an existing app

| Task | Read |
|---|---|
| Where does a file go, what may import what, naming | `references/architecture.md` |
| Add a feature, screen, use case, repository or cubit | `references/feature-layers.md` + `scripts/scaffold_feature.py` |
| Environments, flavors, config, secrets | `references/abstractions/config-and-flavors.md` |
| Calling an API, error mapping, interceptors | `references/abstractions/network.md` |
| Navigating, adding routes, route arguments and deep links, guards | `references/abstractions/navigation.md` |
| Colours, text styles, spacing, dark mode | `references/abstractions/theme.md` |
| Adding or using images and icons | `references/abstractions/images.md` |
| User-visible strings, error messages | `references/abstractions/localization.md` |
| Logging | `references/abstractions/logging.md` |
| Crash / error reporting (Crashlytics, Sentry) | `references/abstractions/error-reporting.md` |
| Persisting data | `references/abstractions/storage.md` |
| Registering dependencies | `references/abstractions/dependency-injection.md` |
| Writing tests, coverage | `references/testing.md` |

The implementation behind each doc lives in `assets/shell/lib/...` (`{{package}}` is replaced with the real package name). Read the shell file when you need the full code.

### Add a feature

```bash
python3 scripts/scaffold_feature.py --root . --feature orders --entity Order [--layers data,domain,presentation] [--dry-run]
```
Then register the DI module in `setupDependencies`, add an `AppRoute` + `GoRoute`, add l10n strings, fill in the stubs and tests, and run `scripts/local_ci.sh --skip-build`. Details are in `references/feature-layers.md`.

## Non-negotiables

These are what keep the structure intact. Each rule's reason is in the linked doc.

1. `core/` holds contracts only. Third-party SDKs are imported only in `shared/<area>/`. Features depend on `core/` interfaces.
2. Features never import other features. Shared pieces move to `core/`, `shared/widgets/` or `shared/coordinators/`.
3. Errors are values. Data sources return `Either<NetworkException, T>` and repositories return `Either<Failure, T>`. Nothing throws across layers.
4. Every dependency comes in through a named constructor parameter. Only DI modules, `AppRouter` and screen-level `BlocProvider.create` call `sl`.
5. State is a sealed class in a Cubit. Error states carry the `Failure`, and widgets show `failure.localizedMessage(context.l10n)`.
6. Navigate only with typed routes: `context.nav.push(XRoute(...))`. Route classes live in `shared/navigation/routes/` with primitive fields, and `fromParams` rejects broken URLs. Every `GoRoute` goes through `buildTypedPage`. No URL strings, no required data in `extra`, and never `context.go`, `GoRouter.of` or `Navigator.push`.
7. Read the theme only through `context.colors`, `context.appColors`, `context.textTheme` and `AppDimensions`. No raw colours, sizes or text styles in features.
8. Render images only through `ImageResourceResolver.<name>.getImageWidget()`. Never `Image.asset` or `SvgPicture.asset`.
9. User-visible text only via `context.l10n`.
10. Log through `AppLogger` (`print` is a lint error). Report unexpected errors through `CrashReporter`.
11. `test/` mirrors `lib/`, and `scripts/local_ci.sh` must pass before pushing.

## Reviewing code against the standard

Check the diff against the non-negotiables above and the dependency table in `references/architecture.md`. Report each violation with its file and line, the rule it breaks, and the concrete fix, for example "move `Dio` usage behind `NetworkClient`" or "replace `Colors.red` with `context.colors.error`".

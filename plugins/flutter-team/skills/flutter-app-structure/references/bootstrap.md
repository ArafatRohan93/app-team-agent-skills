# Bootstrapping a new app

Use this to turn an empty `flutter create` project into the team shell.

## Prerequisites
- Flutter, or fvm with a `.fvmrc` in the project or its parent. The scripts detect fvm and use `fvm flutter`.
- `python3`.
- For iOS flavors: macOS with `ruby` and the `xcodeproj` gem, which ships with CocoaPods. Check with `gem list xcodeproj`.

## Steps
1. **Create the project** if the user hasn't already. Ask for the org and app name if they aren't known.
   ```bash
   flutter create --org com.acme --project-name acme_wallet --platforms android,ios acme_wallet
   ```
   The package name must be snake_case. The org becomes the base bundle id.
2. **Dry run first** to see what will be written:
   ```bash
   python3 <skill-dir>/scripts/bootstrap_app.py --root acme_wallet --app-name "Acme Wallet" --dry-run
   ```
3. **Run it:**
   ```bash
   python3 <skill-dir>/scripts/bootstrap_app.py --root acme_wallet --app-name "Acme Wallet" --description "Acme's customer wallet."
   ```
   It finishes by running `flutter analyze` and `flutter test`. Both must pass. Every step is idempotent: re-running skips work that's already done, and existing non-boilerplate files are never overwritten unless you pass `--force`.
4. **Run the full gate**, which also builds the development flavor for Android and iOS:
   ```bash
   cd acme_wallet && scripts/local_ci.sh
   ```
5. **Tell the user what's left:** real base URLs in `lib/main_<flavor>.dart`, the choice of crash backend ([abstractions/error-reporting.md](abstractions/error-reporting.md)), app icons, and signing.
6. **Add features** with `scripts/scaffold_feature.py` (see [feature-layers.md](feature-layers.md)).

Options: `--skip-android`, `--skip-ios` (for example on Linux), `--skip-verify`, `--force`, `--dry-run`.

## What it produces

| Area | Result |
|---|---|
| Flavors | `main_{development,staging,production}.dart`. Android `productFlavors` (`.dev`/`.stg` suffixes, `[DEV]`/`[STG]` launcher names). iOS `Debug/Release/Profile-<flavor>` configurations with their own xcconfigs, one shared scheme per flavor, a Podfile mapping, and `CFBundleDisplayName = $(FLAVOR_APP_NAME)` |
| Architecture | the full `core/` + `shared/` + `di/` + `app/` + `features/home` shell (see [architecture.md](architecture.md)) |
| State management | flutter_bloc + `AppBlocObserver`. bloc_test is available for tests |
| Localization | `flutter_localizations` + `intl`, `l10n.yaml`, `app_en.arb`, `context.l10n`, `Failure.localizedMessage` |
| Theme | two-layer tokens, light + dark `ThemeData`, `context.colors/appColors/textTheme` |
| Abstractions | network (Dio), navigation (go_router), logger, crash reporter (console), secure key-value storage, image resolver |
| Tests | ~40 tests for every shell piece, `test/helpers/pump_app.dart` and `mocks.dart`. Coverage above 90% |
| Tooling | `analysis_options.yaml` (flutter_lints + team rules), `scripts/local_ci.sh`, `.vscode/launch.json`, `README.md` |
| Removed | the counter `lib/main.dart` and `test/widget_test.dart` |

## Troubleshooting
- **`xcodeproj gem is missing`:** run `gem install xcodeproj` or `brew install cocoapods`. Or pass `--skip-ios` and add the configurations by hand in Xcode, following [abstractions/config-and-flavors.md](abstractions/config-and-flavors.md).
- **iOS build: "Unable to open base configuration reference file":** a `Flutter/<Config>-<flavor>.xcconfig` is missing or has the wrong path. Re-run the bootstrap. It repairs references and never duplicates them.
- **Android: "Gradle build failed to produce an .apk":** you ran without `--flavor`. Every build needs `--flavor <f> -t lib/main_<f>.dart`.
- **`flutter run` without a flavor:** that's expected to fail. There's no `lib/main.dart` on purpose. Use a launch config or pass the flavor.

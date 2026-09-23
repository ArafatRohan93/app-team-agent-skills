import 'package:flutter/widgets.dart';
import 'package:{{package}}/l10n/gen/app_localizations.dart';

export 'package:{{package}}/l10n/gen/app_localizations.dart';

/// Widgets read strings with `context.l10n.someKey` — no hard-coded UI text.
extension AppLocalizationsX on BuildContext {
  AppLocalizations get l10n => AppLocalizations.of(this);
}

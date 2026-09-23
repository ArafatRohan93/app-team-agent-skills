import 'package:{{package}}/core/domain/failures/failure.dart';
import 'package:{{package}}/l10n/gen/app_localizations.dart';

/// Cubit states carry the [Failure]; widgets turn it into text:
///   Text(state.failure.localizedMessage(context.l10n))
/// Keeps user-facing strings out of cubits and fully localized.
extension FailureL10n on Failure {
  String localizedMessage(AppLocalizations l10n) => switch (this) {
    ServerFailure(:final message) =>
      message.isNotEmpty ? message : l10n.errorGeneric,
    NetworkFailure() => l10n.errorNoInternet,
    UnauthorizedFailure() => l10n.errorSessionExpired,
    UnknownFailure() => l10n.errorGeneric,
  };
}

import 'package:flutter_test/flutter_test.dart';
import 'package:{{package}}/core/domain/failures/failure.dart';
import 'package:{{package}}/l10n/failure_l10n.dart';
import 'package:{{package}}/l10n/gen/app_localizations_en.dart';

void main() {
  final l10n = AppLocalizationsEn();

  group('FailureL10n.localizedMessage', () {
    test('uses the server message when present', () {
      expect(
        const ServerFailure(message: 'Card declined').localizedMessage(l10n),
        'Card declined',
      );
    });

    test('falls back to localized strings', () {
      expect(const ServerFailure().localizedMessage(l10n), l10n.errorGeneric);
      expect(const NetworkFailure().localizedMessage(l10n), l10n.errorNoInternet);
      expect(
        const UnauthorizedFailure().localizedMessage(l10n),
        l10n.errorSessionExpired,
      );
      expect(const UnknownFailure('x').localizedMessage(l10n), l10n.errorGeneric);
    });
  });
}

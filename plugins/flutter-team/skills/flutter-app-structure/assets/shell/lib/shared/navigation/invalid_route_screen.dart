import 'package:flutter/material.dart';
import 'package:{{package}}/l10n/l10n.dart';
import 'package:{{package}}/shared/navigation/navigator_scope.dart';
import 'package:{{package}}/shared/navigation/routes/home_routes.dart';
import 'package:{{package}}/shared/theme/theme.dart';

/// Shown for unknown paths and for known paths whose arguments fail to parse
/// (see buildTypedPage) — a broken link never crashes the app.
class InvalidRouteScreen extends StatelessWidget {
  const InvalidRouteScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: AppDimensions.screenPadding,
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                context.l10n.routeInvalidTitle,
                textAlign: TextAlign.center,
                style: context.textTheme.headlineSmall,
              ),
              const SizedBox(height: AppDimensions.spacingSm),
              Text(
                context.l10n.routeInvalidMessage,
                textAlign: TextAlign.center,
                style: context.textTheme.bodyMedium?.copyWith(
                  color: context.colors.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: AppDimensions.spacingXl),
              FilledButton(
                onPressed: () => context.nav.popAllThenPush(const HomeRoute()),
                child: Text(context.l10n.routeGoHome),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

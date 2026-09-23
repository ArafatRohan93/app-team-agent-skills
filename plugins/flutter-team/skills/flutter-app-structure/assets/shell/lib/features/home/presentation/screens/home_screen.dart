import 'package:flutter/material.dart';
import 'package:{{package}}/l10n/l10n.dart';
import 'package:{{package}}/shared/image_resolver/image_resource_resolver.dart';
import 'package:{{package}}/shared/theme/theme.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, required this.appName});

  final String appName;

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
              ImageResourceResolver.logo.getImageWidget(
                height: AppDimensions.spacing3xl,
                color: context.colors.primary,
              ),
              const SizedBox(height: AppDimensions.spacingXl),
              Text(
                context.l10n.homeWelcome(appName),
                textAlign: TextAlign.center,
                style: context.textTheme.headlineSmall,
              ),
              const SizedBox(height: AppDimensions.spacingSm),
              Text(
                context.l10n.homeSubtitle,
                textAlign: TextAlign.center,
                style: context.textTheme.bodyMedium?.copyWith(
                  color: context.colors.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

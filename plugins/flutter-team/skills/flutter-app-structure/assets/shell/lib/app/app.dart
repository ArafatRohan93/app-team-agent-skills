import 'package:flutter/material.dart';
import 'package:{{package}}/core/config/app_config.dart';
import 'package:{{package}}/di/service_locator.dart';
import 'package:{{package}}/l10n/l10n.dart';
import 'package:{{package}}/shared/navigation/app_router.dart';
import 'package:{{package}}/shared/navigation/navigator_scope.dart';
import 'package:{{package}}/shared/theme/theme.dart';

class App extends StatelessWidget {
  const App({super.key, required this.config});

  final AppConfig config;

  @override
  Widget build(BuildContext context) {
    final appRouter = sl<AppRouter>();
    return NavigatorScope(
      navigator: appRouter.navigator,
      child: MaterialApp.router(
        title: config.appName,
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light,
        darkTheme: AppTheme.dark,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        routerConfig: appRouter.routerConfig,
        builder: (context, child) => config.isProduction
            ? child!
            : Banner(
                message: config.flavor.name.toUpperCase(),
                location: BannerLocation.topEnd,
                child: child,
              ),
      ),
    );
  }
}

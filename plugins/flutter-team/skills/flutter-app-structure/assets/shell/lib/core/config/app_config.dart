import 'flavor.dart';

/// Per-flavor runtime configuration. One const instance per `main_<flavor>.dart`.
/// Secrets do not belong here — pass them with `--dart-define` and read them
/// via `String.fromEnvironment` in the flavor's entry point.
class AppConfig {
  const AppConfig({
    required this.flavor,
    required this.appName,
    required this.baseUrl,
    this.connectTimeout = const Duration(seconds: 30),
    this.receiveTimeout = const Duration(seconds: 30),
    this.sendTimeout = const Duration(seconds: 30),
  });

  final Flavor flavor;
  final String appName;
  final String baseUrl;
  final Duration connectTimeout;
  final Duration receiveTimeout;
  final Duration sendTimeout;

  bool get isProduction => flavor == Flavor.production;
}

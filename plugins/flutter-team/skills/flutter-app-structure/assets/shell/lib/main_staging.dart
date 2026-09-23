import 'package:{{package}}/bootstrap.dart';
import 'package:{{package}}/core/config/app_config.dart';
import 'package:{{package}}/core/config/flavor.dart';

void main() => bootstrap(
  const AppConfig(
    flavor: Flavor.staging,
    appName: '[STG] {{app_name}}',
    baseUrl: 'https://api.staging.example.com',
  ),
);

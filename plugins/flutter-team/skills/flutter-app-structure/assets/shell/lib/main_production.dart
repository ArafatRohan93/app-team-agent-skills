import 'package:{{package}}/bootstrap.dart';
import 'package:{{package}}/core/config/app_config.dart';
import 'package:{{package}}/core/config/flavor.dart';

void main() => bootstrap(
  const AppConfig(
    flavor: Flavor.production,
    appName: '{{app_name}}',
    baseUrl: 'https://api.example.com',
  ),
);

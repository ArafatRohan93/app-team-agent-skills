/// Every route in the app. `name` doubles as the go_router route name.
/// Add an entry here, then a matching GoRoute in app_router.dart.
enum AppRoute {
  home('/');

  const AppRoute(this.path);

  final String path;
}

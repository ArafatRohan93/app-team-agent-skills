/// Every path in the app. `name` doubles as the go_router route name.
/// To add a page: add an entry here, a route class in routes/, and a GoRoute
/// in app_router.dart that goes through buildTypedPage.
enum AppRoute {
  home('/');

  const AppRoute(this.path);

  final String path;
}

# Navigation

**Contract:** `lib/core/navigation/app_navigator.dart`. `AppNavigator` has `push`, `pop`, `replace`, `popAllThenPush`, `pushNamed`, `replaceNamed`, `popAllThenPushNamed` and `canPop`.

**Implementation:** `lib/shared/navigation/`
- `app_route.dart`: the `AppRoute` enum, the single list of paths. `.name` doubles as the go_router route name.
- `app_router.dart`: `AppRouter` owns the `GoRouter` (routes, redirect, observers, error page). It exposes `routerConfig` and `navigator`. This is the only file that builds screens for routes.
- `go_router_navigator.dart`: `GoRouterNavigator implements AppNavigator`.
- `navigator_scope.dart`: the `NavigatorScope` InheritedWidget plus `extension on BuildContext { AppNavigator get nav }`.
- `navigation_observer.dart`: logs route changes through `AppLogger`.
- `transitions/app_page_transition.dart`: `buildTransitionPage()`. Every route uses it, so motion is defined in one place.

`App` wraps `MaterialApp.router` in `NavigatorScope(navigator: appRouter.navigator)`. DI also registers `AppNavigator`, for non-widget code such as coordinators.

## Usage
```dart
// widgets
onPressed: () => context.nav.push(AppRoute.orderDetails.path.replaceFirst(':id', order.id)),
onPressed: () => context.nav.pushNamed(AppRoute.orderDetails.name, pathParameters: {'id': order.id}),
onPressed: () => context.nav.popAllThenPush(AppRoute.home.path),   // e.g. after logout
final picked = await context.nav.push<Address>(AppRoute.addressPicker.path);

// coordinators / services (constructor-injected)
_navigator.pushNamed(AppRoute.orderDetails.name, pathParameters: {'id': id});
```

## Adding a route
1. Add an entry to `AppRoute`, for example `orderDetails('/orders/:id')`.
2. Add a `GoRoute(path: AppRoute.x.path, name: AppRoute.x.name, pageBuilder: (_, state) => buildTransitionPage(state: state, child: …))` in `AppRouter`. If the screen needs a cubit tied to the route, especially one that uses path params, create its `BlocProvider` here.
3. Put guards and redirects in `AppRouter.redirect`, not in screens.

## Testing
- Widgets: `tester.pumpApp(widget, navigator: mockNavigator)`, then `verify(() => mockNavigator.push<void>('/x')).called(1)`.
- Router: pump `MaterialApp.router(routerConfig: router.routerConfig)` and drive `router.navigator` (see `test/shared/navigation/app_router_test.dart`).

## Don'ts
- Never call `context.go`, `context.push`, `GoRouter.of(context)` or `Navigator.of(context).push` in features. Dialogs and bottom sheets (`showDialog`, `showModalBottomSheet`) are fine.
- Never import `go_router` outside `lib/shared/navigation/`.
- Never hard-code path strings. Use `AppRoute`.

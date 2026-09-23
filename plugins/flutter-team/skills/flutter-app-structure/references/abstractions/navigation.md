# Navigation

Features navigate with **typed route classes**. The URL is the only contract between the caller and the screen, and it's checked twice:

- **At push time**, by the navigator. This catches bugs in our own code.
- **At build time**, by the router. This catches deep links, notifications and web URLs, which arrive as raw strings and never pass through the push-time check.

A screen's constructor therefore never receives a null or broken argument.

## Files

**Contracts (`lib/core/navigation/`)**
- `app_navigator.dart`: `AppNavigator` has `push`, `replace` and `popAllThenPush`, each taking an `AppRouteData`, plus `pop`, `canPop` and the raw-URL `pushLocation`/`popAllThenPushLocation` for coordinators.
- `app_route_data.dart`: the `AppRouteData` base class. It provides `pathTemplate`, `pathParameters`, `queryParameters`, `isValid`, `isComplete` and the escaped `location`.
- `route_params.dart`: the `RouteParams` extension on `Map<String, String>`, with null-safe readers: `string`, `integer`, `decimal`, `boolean`, `dateTime` and `enumByName`.

**Implementation (`lib/shared/navigation/`)**
- `app_route.dart`: the `AppRoute` enum, the list of every path. `.name` is also the go_router route name.
- `routes/<feature>_routes.dart`: one file per feature, holding its route classes (for example `HomeRoute` in `routes/home_routes.dart`).
- `app_router.dart`: `AppRouter` owns the `GoRouter`. Every `GoRoute` goes through `buildTypedPage`, and unknown paths show `InvalidRouteScreen`.
- `typed_page.dart`: `buildTypedPage()`, the build-time guard.
- `invalid_route_screen.dart`: a localized "Page not found" screen with a **Go to home** button.
- `go_router_navigator.dart`: `GoRouterNavigator implements AppNavigator`, including the push-time guard.
- `navigator_scope.dart`: `context.nav`. `navigation_observer.dart` logs route changes, and `transitions/` holds the shared page transition.

## Declaring a route

```dart
// lib/shared/navigation/routes/orders_routes.dart
import 'package:app/core/navigation/app_route_data.dart';
import 'package:app/core/navigation/route_params.dart';
import 'package:app/shared/navigation/app_route.dart';

enum OrderTab { summary, items }

final class OrderDetailsRoute extends AppRouteData {
  const OrderDetailsRoute({required this.orderId, this.tab = OrderTab.summary});

  final String orderId;
  final OrderTab tab;

  @override
  String get pathTemplate => AppRoute.orderDetails.path;       // '/orders/:id'

  @override
  Map<String, String> get pathParameters => {'id': orderId};

  @override
  Map<String, String> get queryParameters => {'tab': tab.name};

  @override
  bool get isValid => orderId.isNotEmpty;

  static OrderDetailsRoute? fromParams(Map<String, String> path, Map<String, String> query) {
    final id = path.string('id');
    if (id == null) return null;                                          // required → reject
    return OrderDetailsRoute(
      orderId: id,
      tab: query.enumByName('tab', OrderTab.values) ?? OrderTab.summary,  // optional → default
    );
  }
}
```

**Rules for route classes:**
- **Put route classes in `shared/navigation/routes/`, not in the feature.** Any feature can then navigate to any other without importing it.
- **Fields are primitives only:** `String` IDs, `int`, `double`, `bool`, `DateTime`, and enums declared in the route file. Never a feature model. Pass the ID, and let the screen's cubit load the data.
- **`fromParams` is the only place URL strings are parsed.** Use the `RouteParams` helpers. Never write `params['x']!`, `int.parse` or `as` casts.
- **A missing or malformed required parameter makes `fromParams` return `null`.** A malformed optional parameter falls back to its default, so old links survive changes.
- **`isValid` holds the rules types can't express** (a non-empty ID, a positive page number). Both guards check it.
- **Every path parameter in the template must be filled in `pathParameters`.** Otherwise `isComplete` is false and the navigator refuses the route.

## Registering it in `AppRouter`

1. Add an entry to `AppRoute`: `orderDetails('/orders/:id')`.
2. Add a `GoRoute`:
   ```dart
   GoRoute(
     path: AppRoute.orderDetails.path,
     name: AppRoute.orderDetails.name,
     pageBuilder: (_, state) => buildTypedPage(
       state,
       logger: logger,
       parse: OrderDetailsRoute.fromParams,
       builder: (route) => OrderDetailsScreen(orderId: route.orderId, initialTab: route.tab),
     ),
   ),
   ```
   `buildTypedPage` parses the URL. If the result is `null` or not valid, it logs a warning and shows `InvalidRouteScreen` instead of building the screen.
3. If the screen needs a cubit tied to the route (for example one keyed by `orderId`), create its `BlocProvider` inside `builder`.
4. Put guards such as sign-in and onboarding in `GoRouter.redirect`, never in screens.

`scripts/scaffold_feature.py` does steps 1 and 2 for new features. It generates the route class and its test, adds the `AppRoute` entry, and prints the `GoRoute` to paste in.

## Navigating

```dart
context.nav.push(OrderDetailsRoute(orderId: order.id));
context.nav.replace(const OrdersRoute());
context.nav.popAllThenPush(const HomeRoute());                            // e.g. after sign-out
final address = await context.nav.push<Address>(const AddressPickerRoute());   // results can be Dart objects
context.nav.pop(selectedAddress);
```

- **Coordinators** (deep links, notification taps) receive raw URLs. They use `navigator.pushLocation(url)` or `popAllThenPushLocation(url)` with the `AppNavigator` from DI. The router still validates the URL at build time.
- **Invalid routes:** if a route isn't valid, the navigator refuses it. It logs a warning, fails an assert in debug builds so the bug is obvious, and does nothing in release.

## `extra`

- **Never put data a screen needs in `extra`.** It isn't part of the URL, so deep links and notifications never carry it. It also can't be saved for state restoration or browser history unless the router has an `extraCodec`, and it's untyped.
- **It's allowed only as an optional speed-up.** For example, pass an already-loaded model so the screen can render immediately. The screen must also work with `null`:
  ```dart
  context.nav.push(OrderDetailsRoute(orderId: order.id), extra: order);

  builder: (route) => OrderDetailsScreen(
    orderId: route.orderId,
    preloaded: state.extra is Order ? state.extra as Order : null,
  ),
  ```

## Testing

- **Route classes:** round-trip `fromParams(route.pathParameters, route.queryParameters)`, then check that missing or malformed parameters are rejected and that bad optional ones fall back to defaults. The scaffold generates the round-trip test. URL escaping is tested once, for `AppRouteData` itself, and go_router decodes escaped values before `fromParams` sees them.
- **Widgets:** use `tester.pumpApp(widget, navigator: mockNavigator)`, call `registerFallbackValue(const HomeRoute())`, then `verify(() => mockNavigator.push<void>(any())).called(1)`.
- **Router:** pump `MaterialApp.router(routerConfig: router.routerConfig)` inside a `NavigatorScope`, and drive `router.navigator`. See `test/shared/navigation/`.

## Don'ts

- Don't call `context.go`, `context.push`, `GoRouter.of(context)` or `Navigator.of(context).push` in features. Dialogs and bottom sheets are fine.
- Don't import `go_router` outside `lib/shared/navigation/`.
- Don't build URL strings in features (`'/orders/$id'`). Construct a route class instead.
- Don't use feature models as route fields, and don't put required data in `extra`.
- Don't read `GoRouterState` inside screens. Screens take typed constructor arguments.

## Why not `go_router_builder`?

go_router's code-generated typed routes are a valid alternative. They also expose `.location`, so they can be pushed through `context.nav.pushLocation`. We use hand-written route classes for three reasons:
- There's no `build_runner` code generation step.
- Invalid URLs have explicit, tested handling: `fromParams` returns `null` and the app shows `InvalidRouteScreen`.
- `isValid` checks the same rules at both push time and build time.

Consider switching if an app grows past about 30 routes.

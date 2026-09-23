# Testing

- `test/` mirrors `lib/` one-to-one, and files end in `_test.dart`.
- **Shared mocks** of core contracts live in `test/helpers/mocks.dart` (`MockAppNavigator`, `MockAppLogger`, `MockCrashReporter`, `MockNetworkClient`, `MockKeyValueStorage`). Feature mocks are private to their file: `class _MockGetOrdersUseCase extends Mock implements GetOrdersUseCase {}`.
- **Fixtures** are private top-level values or builders: `final _order = Order(...)`, `Order _order(String id) => ...`.
- **Structure:** `setUp` creates fresh mocks, and a local `buildCubit()` builds the class under test. Groups are named after the class and method, `group('OrdersCubit', …)` → `group('load()', …)`. Test names describe behaviour: `'emits [OrdersLoading, OrdersLoaded] on success'`.
- **Either:** stub with `right(...)` / `left(const NetworkFailure())`, and assert with `result.getRight().toNullable()` / `isA<UnauthorizedFailure>()`.
- **Cubits:** `expectLater(cubit.stream, emitsInOrder([isA<OrdersLoading>(), isA<OrdersLoaded>()]))`, or `blocTest<OrdersCubit, OrdersState>(...)` from bloc_test.
- **Widgets:** `await tester.pumpApp(const OrdersScreen(), navigator: mockNavigator)` gives you the theme, l10n and `context.nav`. Pass `theme: AppTheme.dark` to check dark mode.
- **What to test per layer:**
  - models: `fromJson`/`toJson`
  - data sources: parsing and error mapping
  - repositories: `Failure` mapping
  - use cases: business rules
  - cubits: emitted state sequences
  - screens: one test per state
- **Coverage gate:** `scripts/local_ci.sh` fails below `MIN_COVERAGE` (80% by default). Generated code, entry points and thin plugin wrappers are excluded in `COVERAGE_EXCLUDES`. Add new thin SDK adapters there instead of lowering the gate.

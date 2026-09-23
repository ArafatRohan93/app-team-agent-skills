# Feature layers

## Generate, don't hand-write
```bash
python3 <skill-dir>/scripts/scaffold_feature.py --root . --feature orders --entity Order [--plural Orders] [--layers data,domain,presentation] [--dry-run]
```
This writes compile-ready stubs: model, remote data source, repository contract and impl, use case, cubit and state, screen, `di/modules/orders_module.dart`, and mirrored repository and cubit tests. In shell projects it also writes the feature's route class (`shared/navigation/routes/<feature>_routes.dart`) and its test, and adds the `AppRoute` entry. It reads the package name from `pubspec.yaml`, never overwrites files and formats its output. If `lib/l10n/failure_l10n.dart` exists (a bootstrapped shell), states carry the `Failure` and the screen localizes it. Otherwise the cubit maps failures to strings, which is the legacy style.

After generating:
1. Fill in model fields and `fromJson`/`toJson`, the endpoint, and use-case rules. Delete stubs you don't need.
2. Add `registerOrdersDependencies()` to `setupDependencies` in `lib/di/service_locator.dart`, after the modules it depends on.
3. Paste the `GoRoute` the script printed into `AppRouter`. It goes through `buildTypedPage` with `XRoute.fromParams`. Add path or query fields to the route class if the screen needs arguments (see [abstractions/navigation.md](abstractions/navigation.md)).
4. Add l10n strings, finish the tests, and run `scripts/local_ci.sh --skip-build`.

Below is the reference shape of each file. `app` stands for the package name.

**Import fpdart with `show`.** For example, `import 'package:fpdart/fpdart.dart' show Either, left, right;`, listing only the names the file uses. fpdart also exports common names such as `Order`, `State`, `Task` and `Option`. A bare import clashes with entities that have those names (`ambiguous_import`). The scaffold already generates the `show` form.

## data/models
```dart
class Order {
  const Order({required this.id, required this.totalCents, required this.createdAt});

  final String id;
  final int totalCents;
  final DateTime createdAt;

  factory Order.fromJson(Map<String, dynamic> json) => Order(
    id: json['id'] as String,
    totalCents: json['totalCents'] as int,
    createdAt: DateTime.parse(json['createdAt'] as String),
  );
}
```
Request DTOs have `Map<String, dynamic> toJson()` and are named `create_order_request.dart` / `create_order_response.dart`. Models are immutable, `const` where possible, and have no Flutter imports.

## data/data_sources
See [abstractions/network.md](abstractions/network.md) for the full remote data source pattern. Constructors take `NetworkClient` (remote) or `KeyValueStorage` (local). Add an `abstract interface class OrderDataSource` only when there are multiple implementations.

## data/repositories
```dart
class OrderRepositoryImpl implements OrderRepository {
  const OrderRepositoryImpl({required OrderRemoteDataSource dataSource}) : _dataSource = dataSource;

  final OrderRemoteDataSource _dataSource;

  @override
  Future<Either<Failure, List<Order>>> getOrders() async {
    final result = await _dataSource.getOrders();
    return result.mapLeft((e) => e.toFailure());
  }
}
```
The repository is where data sources are combined (remote + cache) and exceptions become `Failure`s.

## domain/repositories + use_cases
```dart
abstract interface class OrderRepository {
  Future<Either<Failure, List<Order>>> getOrders();
}

class GetOrdersUseCase {
  const GetOrdersUseCase({required OrderRepository repository}) : _repository = repository;

  final OrderRepository _repository;

  Future<Either<Failure, List<Order>>> call() async {
    final result = await _repository.getOrders();
    return result.fold(
      (failure) => switch (failure) {
        ServerFailure(errorCode: 'ORDERS_NOT_FOUND') => right(const []), // business rule
        _ => left(failure),
      },
      right,
    );
  }
}
```

## presentation/cubits
```dart
// orders_cubit.dart
part 'orders_state.dart';

class OrdersCubit extends Cubit<OrdersState> {
  OrdersCubit({required GetOrdersUseCase getOrders}) : _getOrders = getOrders, super(const OrdersInitial());

  final GetOrdersUseCase _getOrders;

  Future<void> load() async {
    emit(const OrdersLoading());
    final result = await _getOrders();
    result.fold((failure) => emit(OrdersError(failure)), (orders) => emit(OrdersLoaded(orders)));
  }
}

// orders_state.dart
part of 'orders_cubit.dart';

sealed class OrdersState { const OrdersState(); }
class OrdersInitial extends OrdersState { const OrdersInitial(); }
class OrdersLoading extends OrdersState { const OrdersLoading(); }
class OrdersLoaded extends OrdersState { const OrdersLoaded(this.orders); final List<Order> orders; }
class OrdersError extends OrdersState { const OrdersError(this.failure); final Failure failure; }
```
Add `copyWith` on `Loaded` for incremental updates such as pagination or `isLoadingMore`. Use a `Bloc` with events instead of a Cubit only when you need event transformers (debounce, droppable).

## presentation/screens
```dart
class OrdersScreen extends StatelessWidget {
  const OrdersScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => OrdersCubit(getOrders: sl<GetOrdersUseCase>())..load(),
      child: BlocBuilder<OrdersCubit, OrdersState>(
        builder: (context, state) => switch (state) {
          OrdersInitial() || OrdersLoading() => const Center(child: CircularProgressIndicator()),
          OrdersLoaded(:final orders) => ListView.separated(
            padding: const EdgeInsets.all(AppDimensions.screenPadding),
            itemCount: orders.length,
            separatorBuilder: (_, _) => const SizedBox(height: AppDimensions.spacingLg),
            itemBuilder: (_, i) => OrderTile(order: orders[i]),
          ),
          OrdersError(:final failure) => ErrorView(
            message: failure.localizedMessage(context.l10n),
            onRetry: () => context.read<OrdersCubit>().load(),
          ),
        },
      ),
    );
  }
}
```
Use `BlocConsumer` or `BlocListener` for one-off effects such as snackbars and navigation, and keep them out of `builder`.

## DI module
```dart
void registerOrdersDependencies() {
  final sl = GetIt.instance;
  sl.registerLazySingleton<OrderRepository>(
    () => OrderRepositoryImpl(dataSource: OrderRemoteDataSource(networkClient: sl())),
  );
  sl.registerLazySingleton<GetOrdersUseCase>(() => GetOrdersUseCase(repository: sl()));
}
```

## Coordinators (cross-feature)
```dart
class SessionCoordinator {
  SessionCoordinator({required AuthService authService, required AppNavigator navigator, required AppLogger logger})
    : _authService = authService, _navigator = navigator, _logger = logger;
  …
  Future<void> initialize() async { _sub = _authService.authEvents.listen(_onEvent); }
  void dispose() { _sub?.cancel(); }
}
```
Register it in DI and start it in `bootstrap.dart` with `unawaited(sl<SessionCoordinator>().initialize());` before `runApp`.

# Network caller

**Contract:** `lib/core/network/`
- `network_client.dart`: `NetworkClient` with `get`, `post`, `put`, `patch` and `delete`.
- `network_response.dart`: `NetworkResponse` with `jsonResponse`, `statusCode`, headers, `error` and `isSuccess`.
- `network_exception.dart`: sealed `NetworkException` with the subtypes `Server`, `Unauthorized`, `Timeout`, `Connection` and `Unknown`.
- `network_exception_ext.dart`: `toFailure()`.

**Implementation:** `lib/shared/network/`
- `DioNetworkClient`, built by `NetworkClientFactory` from `AppConfig`: base URL, timeouts, JSON headers.
- `interceptors/error_interceptor.dart` maps `DioException` to `NetworkException`.
- `interceptors/logging_interceptor.dart` logs traffic through `AppLogger` in non-release builds only.

## The error pipeline

```
Dio throws DioException
  → ErrorInterceptor puts a typed NetworkException in DioException.error
  → DioNetworkClient catches it and returns NetworkResponse(error: …)   (it never throws)
  → Data source returns Either<NetworkException, T>
  → Repository calls result.mapLeft((e) => e.toFailure())  →  Either<Failure, T>
  → Use case / cubit folds it. The widget shows failure.localizedMessage(context.l10n).
```

## Usage in a data source
```dart
Future<Either<NetworkException, List<Order>>> getOrders() async {
  try {
    final response = await _client.get('/orders');
    if (response.error != null) return left(response.error!);
    final json = jsonDecode(response.jsonResponse!) as Map<String, dynamic>;
    return right((json['orders'] as List).map((e) => Order.fromJson(e as Map<String, dynamic>)).toList());
  } on NetworkException catch (e) {
    return left(e);
  } catch (e) {
    return left(UnknownNetworkException(message: e.toString())); // e.g. a JSON parse error
  }
}
```

## Extending
- **Auth header or token refresh:** write `shared/network/interceptors/auth_interceptor.dart`. It depends on a `core/auth/AuthService` contract, never on the auth SDK directly. Pass it to `NetworkClientFactory(extraInterceptors: [...])` in `di/modules/network_module.dart`. ruvy_app's `AuthInterceptor` is the reference: it adds the Bearer token on request and signs out on 401 `UNAUTHORIZED`.
- **Backend error shape:** adjust `ErrorInterceptor._parseServerError`. It expects `{"error": "CODE", "message": "…"}`.
- **New error kinds:** add a `NetworkException` subtype and a `Failure` subtype. Because both are sealed, the compiler then flags every `switch` that has to handle them.
- **Replacing Dio:** write `HttpNetworkClient implements NetworkClient` and change one line in `network_module.dart`. Nothing in `features/` changes.

## Testing
- Data sources: mock `NetworkClient` (`MockNetworkClient` in `test/helpers/mocks.dart`) and stub it to return `NetworkResponse(jsonResponse: '...')` or `NetworkResponse(error: const TimeoutNetworkException())`.
- `DioNetworkClient`: mock `Dio` (see `test/shared/network/dio_network_client_test.dart`).

## Don'ts
- Don't import `dio` outside `lib/shared/network/`.
- Don't throw from data sources. Return `left(...)`.
- Don't return `NetworkException` above the repository. Domain and presentation only see `Failure`.

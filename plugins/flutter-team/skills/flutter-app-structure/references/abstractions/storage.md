# Storage

**Contract:** `lib/core/storage/key_value_storage.dart`. `KeyValueStorage` has `read`, `write`, `delete` and `clear`. All take `String` keys and values and are async.

**Implementation:** `lib/shared/storage/secure_key_value_storage.dart`. `SecureKeyValueStorage` wraps `flutter_secure_storage` (Keychain on iOS, encrypted storage on Android). It's registered lazily in `core_module.dart`.

**Keys:** `lib/shared/storage/storage_keys.dart`. `StorageKeys` is an `abstract final class` with every key, namespaced by the bundle id. Per-user keys use `StorageKeys.forUser(userId, 'name')`.

## Usage
Wrap storage in the feature's local data source, or in a repository, so that nothing above the data layer knows how data persists:
```dart
class SessionLocalDataSource {
  const SessionLocalDataSource({required KeyValueStorage storage}) : _storage = storage;
  final KeyValueStorage _storage;

  Future<bool> hasCompletedOnboarding() async =>
      await _storage.read(StorageKeys.onboardingCompleted) == 'true';

  Future<void> markOnboardingCompleted() => _storage.write(StorageKeys.onboardingCompleted, 'true');
}
```
Store structured values as `jsonEncode(model.toJson())`.

## Extending
- **Non-sensitive, high-volume preferences:** add `SharedPrefsKeyValueStorage implements KeyValueStorage` (shared_preferences) and register it under a second name, `sl.registerLazySingleton<KeyValueStorage>(…, instanceName: 'prefs')`. You can also create a separate `PreferencesStorage` contract if the API needs to differ.
- **Database-grade storage** (drift, isar…): define a feature-specific contract in `core/` and keep the database package inside `shared/`.

## Testing
Use `MockKeyValueStorage` from `test/helpers/mocks.dart`. `SecureKeyValueStorage` is excluded from the coverage gate because it's a thin plugin wrapper.

## Don'ts
- No string-literal keys outside `StorageKeys`.
- Don't import `flutter_secure_storage` or `shared_preferences` in `features/`.

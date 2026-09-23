/// Persistent string key/value storage. Keys come from `StorageKeys`
/// (shared/storage/storage_keys.dart) — never inline string literals.
abstract interface class KeyValueStorage {
  Future<String?> read(String key);

  Future<void> write(String key, String value);

  Future<void> delete(String key);

  Future<void> clear();
}

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:{{package}}/core/storage/key_value_storage.dart';

/// Keychain (iOS) / EncryptedSharedPreferences-backed (Android) storage.
class SecureKeyValueStorage implements KeyValueStorage {
  const SecureKeyValueStorage({
    FlutterSecureStorage storage = const FlutterSecureStorage(),
  }) : _storage = storage;

  final FlutterSecureStorage _storage;

  @override
  Future<String?> read(String key) => _storage.read(key: key);

  @override
  Future<void> write(String key, String value) =>
      _storage.write(key: key, value: value);

  @override
  Future<void> delete(String key) => _storage.delete(key: key);

  @override
  Future<void> clear() => _storage.deleteAll();
}

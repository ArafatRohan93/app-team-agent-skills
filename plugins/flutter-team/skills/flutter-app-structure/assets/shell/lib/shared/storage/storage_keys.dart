/// Every persisted key in one place, namespaced by the app's bundle id.
abstract final class StorageKeys {
  static const _prefix = '{{bundle_id}}';

  static const onboardingCompleted = '$_prefix.onboarding_completed';

  static String forUser(String userId, String name) =>
      '$_prefix.${name}_$userId';
}

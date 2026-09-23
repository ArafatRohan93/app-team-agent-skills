/// Safe readers for URL path/query parameters. Each returns null instead of
/// throwing, so `fromParams` can reject a broken URL instead of crashing.
/// Never use `params['x']!`, `int.parse` or `as` casts on route parameters.
extension RouteParams on Map<String, String> {
  /// Trimmed value, or null when missing or blank.
  String? string(String key) {
    final value = this[key]?.trim();
    return (value == null || value.isEmpty) ? null : value;
  }

  int? integer(String key) => int.tryParse(this[key] ?? '');

  double? decimal(String key) => double.tryParse(this[key] ?? '');

  bool? boolean(String key) => switch (this[key]?.toLowerCase()) {
    'true' || '1' => true,
    'false' || '0' => false,
    _ => null,
  };

  DateTime? dateTime(String key) => DateTime.tryParse(this[key] ?? '');

  T? enumByName<T extends Enum>(String key, List<T> values) {
    final value = this[key];
    return value == null ? null : values.asNameMap()[value];
  }
}

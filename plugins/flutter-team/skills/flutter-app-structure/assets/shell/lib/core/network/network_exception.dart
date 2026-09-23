/// Transport-level error produced by the data layer. Repositories convert it
/// to a [Failure] with `toFailure()` (see network_exception_ext.dart).
sealed class NetworkException implements Exception {
  const NetworkException();
}

final class ServerNetworkException extends NetworkException {
  const ServerNetworkException({
    required this.statusCode,
    this.errorCode,
    required this.message,
  });

  final int statusCode;
  final String? errorCode;
  final String message;

  @override
  String toString() =>
      'ServerNetworkException: $statusCode${errorCode != null ? ' [$errorCode]' : ''} – $message';
}

final class UnauthorizedNetworkException extends NetworkException {
  const UnauthorizedNetworkException();

  @override
  String toString() => 'UnauthorizedNetworkException: token rejected by server';
}

final class TimeoutNetworkException extends NetworkException {
  const TimeoutNetworkException();

  @override
  String toString() => 'TimeoutNetworkException: request timed out';
}

final class ConnectionNetworkException extends NetworkException {
  const ConnectionNetworkException();

  @override
  String toString() => 'ConnectionNetworkException: no network connection';
}

final class UnknownNetworkException extends NetworkException {
  const UnknownNetworkException({required this.message});

  final String message;

  @override
  String toString() => 'UnknownNetworkException: $message';
}

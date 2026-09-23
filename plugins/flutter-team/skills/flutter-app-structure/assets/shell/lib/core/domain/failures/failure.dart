/// Domain-level error returned in the `Left` of every repository / use case.
/// Sealed so presentation code can `switch` over it exhaustively.
sealed class Failure {
  const Failure();
}

final class ServerFailure extends Failure {
  const ServerFailure({this.errorCode, this.message = ''});

  final String? errorCode;
  final String message;
}

final class UnauthorizedFailure extends Failure {
  const UnauthorizedFailure();
}

final class NetworkFailure extends Failure {
  const NetworkFailure();
}

final class UnknownFailure extends Failure {
  const UnknownFailure(this.message);

  final String message;
}

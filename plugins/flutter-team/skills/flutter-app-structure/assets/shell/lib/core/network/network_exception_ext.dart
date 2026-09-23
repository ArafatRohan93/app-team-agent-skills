import 'package:{{package}}/core/domain/failures/failure.dart';
import 'package:{{package}}/core/network/network_exception.dart';

extension NetworkExceptionToFailure on NetworkException {
  Failure toFailure() => switch (this) {
    ServerNetworkException(:final errorCode, :final message) => ServerFailure(
      errorCode: errorCode,
      message: message,
    ),
    UnauthorizedNetworkException() => const UnauthorizedFailure(),
    TimeoutNetworkException() => const NetworkFailure(),
    ConnectionNetworkException() => const NetworkFailure(),
    UnknownNetworkException(:final message) => UnknownFailure(message),
  };
}

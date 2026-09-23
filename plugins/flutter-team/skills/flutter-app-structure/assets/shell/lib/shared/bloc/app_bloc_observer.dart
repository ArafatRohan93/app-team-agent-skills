import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:{{package}}/core/logger/app_logger.dart';

/// Logs every Cubit/Bloc state change and error. Installed in bootstrap.dart.
class AppBlocObserver extends BlocObserver {
  const AppBlocObserver({required AppLogger logger}) : _logger = logger;

  final AppLogger _logger;

  @override
  void onChange(BlocBase<dynamic> bloc, Change<dynamic> change) {
    super.onChange(bloc, change);
    _logger.verbose(
      '${bloc.runtimeType}: ${change.currentState.runtimeType} → '
      '${change.nextState.runtimeType}',
    );
  }

  @override
  void onError(BlocBase<dynamic> bloc, Object error, StackTrace stackTrace) {
    _logger.error('${bloc.runtimeType} error', error, stackTrace);
    super.onError(bloc, error, stackTrace);
  }
}

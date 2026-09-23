import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:{{package}}/shared/bloc/app_bloc_observer.dart';

import '../../helpers/mocks.dart';

class _CounterCubit extends Cubit<int> {
  _CounterCubit() : super(0);
}

void main() {
  group('AppBlocObserver', () {
    test('logs state changes and errors', () {
      final logger = MockAppLogger();
      final observer = AppBlocObserver(logger: logger);
      final cubit = _CounterCubit();

      observer.onChange(cubit, const Change(currentState: 0, nextState: 1));
      observer.onError(cubit, Exception('x'), StackTrace.empty);

      verify(() => logger.verbose(any())).called(1);
      verify(() => logger.error(any(), any(), StackTrace.empty)).called(1);
      cubit.close();
    });
  });
}

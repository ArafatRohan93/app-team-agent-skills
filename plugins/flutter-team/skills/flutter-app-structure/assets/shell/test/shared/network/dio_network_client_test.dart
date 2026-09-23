import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:{{package}}/core/network/network_exception.dart';
import 'package:{{package}}/shared/network/dio_network_client.dart';

class _MockDio extends Mock implements Dio {}

final _options = RequestOptions(path: '/items');

void main() {
  late _MockDio dio;
  late DioNetworkClient client;

  setUpAll(() => registerFallbackValue(Options()));

  setUp(() {
    dio = _MockDio();
    client = DioNetworkClient(dio: dio);
  });

  group('DioNetworkClient.get', () {
    test('returns the JSON-encoded body and status on success', () async {
      when(
        () => dio.get<dynamic>(
          '/items',
          queryParameters: any(named: 'queryParameters'),
          options: any(named: 'options'),
        ),
      ).thenAnswer(
        (_) async => Response<dynamic>(
          requestOptions: _options,
          statusCode: 200,
          data: {'id': 1},
        ),
      );

      final response = await client.get('/items');

      expect(response.isSuccess, isTrue);
      expect(response.statusCode, 200);
      expect(response.jsonResponse, '{"id":1}');
    });

    test('surfaces the mapped NetworkException on DioException', () async {
      when(
        () => dio.get<dynamic>(
          '/items',
          queryParameters: any(named: 'queryParameters'),
          options: any(named: 'options'),
        ),
      ).thenThrow(
        DioException(
          requestOptions: _options,
          error: const TimeoutNetworkException(),
        ),
      );

      final response = await client.get('/items');

      expect(response.isSuccess, isFalse);
      expect(response.error, isA<TimeoutNetworkException>());
    });
  });

  group('DioNetworkClient.post', () {
    test('forwards the body and returns a String body unchanged', () async {
      when(
        () => dio.post<dynamic>(
          '/items',
          data: {'name': 'a'},
          queryParameters: any(named: 'queryParameters'),
          options: any(named: 'options'),
        ),
      ).thenAnswer(
        (_) async => Response<dynamic>(
          requestOptions: _options,
          statusCode: 201,
          data: '{"id":2}',
        ),
      );

      final response = await client.post('/items', data: {'name': 'a'});

      expect(response.statusCode, 201);
      expect(response.jsonResponse, '{"id":2}');
    });
  });

  group('DioNetworkClient.put/patch/delete', () {
    Response<dynamic> ok() =>
        Response<dynamic>(requestOptions: _options, statusCode: 204);

    test('delegate to Dio and return the status code', () async {
      when(
        () => dio.put<dynamic>(
          any(),
          data: any(named: 'data'),
          queryParameters: any(named: 'queryParameters'),
          options: any(named: 'options'),
        ),
      ).thenAnswer((_) async => ok());
      when(
        () => dio.patch<dynamic>(
          any(),
          data: any(named: 'data'),
          queryParameters: any(named: 'queryParameters'),
          options: any(named: 'options'),
        ),
      ).thenAnswer((_) async => ok());
      when(
        () => dio.delete<dynamic>(
          any(),
          data: any(named: 'data'),
          queryParameters: any(named: 'queryParameters'),
          options: any(named: 'options'),
        ),
      ).thenAnswer((_) async => ok());

      expect((await client.put('/items/1')).statusCode, 204);
      expect((await client.patch('/items/1')).statusCode, 204);
      expect((await client.delete('/items/1')).statusCode, 204);
    });

    test('wraps a DioException without a typed error as Unknown', () async {
      when(
        () => dio.delete<dynamic>(
          any(),
          data: any(named: 'data'),
          queryParameters: any(named: 'queryParameters'),
          options: any(named: 'options'),
        ),
      ).thenThrow(DioException(requestOptions: _options, message: 'nope'));

      final response = await client.delete('/items/1');

      expect(response.error, isA<UnknownNetworkException>());
    });
  });
}

import 'package:flutter_test/flutter_test.dart';
import 'package:{{package}}/core/navigation/route_params.dart';

enum _Tab { summary, items }

void main() {
  const params = {
    'id': ' o-1 ',
    'blank': '  ',
    'page': '3',
    'price': '9.5',
    'flag': 'TRUE',
    'off': '0',
    'at': '2026-01-02T03:04:05Z',
    'tab': 'items',
    'bad': 'nope',
  };

  group('RouteParams', () {
    test('string trims and treats blank or missing as null', () {
      expect(params.string('id'), 'o-1');
      expect(params.string('blank'), isNull);
      expect(params.string('missing'), isNull);
    });

    test('numbers return null instead of throwing', () {
      expect(params.integer('page'), 3);
      expect(params.integer('bad'), isNull);
      expect(params.decimal('price'), 9.5);
      expect(params.decimal('missing'), isNull);
    });

    test('boolean accepts true/false/1/0 case-insensitively', () {
      expect(params.boolean('flag'), isTrue);
      expect(params.boolean('off'), isFalse);
      expect(params.boolean('bad'), isNull);
    });

    test('dateTime and enumByName', () {
      expect(params.dateTime('at'), DateTime.utc(2026, 1, 2, 3, 4, 5));
      expect(params.dateTime('bad'), isNull);
      expect(params.enumByName('tab', _Tab.values), _Tab.items);
      expect(params.enumByName('bad', _Tab.values), isNull);
      expect(params.enumByName('missing', _Tab.values), isNull);
    });
  });
}

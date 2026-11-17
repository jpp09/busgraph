import copy
import unittest

from data.emdec_collector import normalize, parse_geojson


class CollectorTests(unittest.TestCase):
    def feature(self, sequence, stop):
        return {'properties': {'num_linha': '332', 'sentido': 1,
                'ptseqlinha': sequence, 'ponto_id': stop, 'nome_linha': 'Mapa'},
                'geometry': {'type': 'Point', 'coordinates': [-47, -22]}}

    def normalize(self, features):
        return normalize({'numero_linha': '332', 'nome': '  Hospital  das Clínicas '},
                         {'features': features})

    def test_duplicates_removed_but_repeated_stop_visit_preserved(self):
        first = self.feature(1, 10)
        result = self.normalize([self.feature(3, 10), first, copy.deepcopy(first), self.feature(2, 20)])
        self.assertEqual([s['parada_id'] for s in result['paradas']], ['10', '20', '10'])
        self.assertEqual(len(result['trechos']), 2)
        self.assertIsNone(result['trechos'][0]['duracao_min'])
        self.assertEqual(result['paradas'][0]['nome_linha'], 'Hospital das Clínicas')

    def test_invalid_coordinate_does_not_create_bridge(self):
        bad = self.feature(2, 20)
        bad['geometry']['coordinates'][0] = float('nan')
        result = self.normalize([self.feature(1, 10), bad, self.feature(3, 30)])
        self.assertEqual(len(result['paradas']), 2)
        self.assertEqual(result['trechos'], [])

    def test_conflicting_sequences_do_not_create_edges(self):
        result = self.normalize([self.feature(1, 10), self.feature(2, 20), self.feature(2, 21)])
        self.assertEqual(result['trechos'], [])

    def test_fractional_sequence_is_preserved(self):
        result = self.normalize([self.feature(10.7, 20), self.feature(10, 10), self.feature(11, 30)])
        self.assertEqual([s['sequencia'] for s in result['paradas']], [10, 10.7, 11])
        self.assertEqual(len(result['trechos']), 2)

    def test_remote_javascript_is_not_executed(self):
        with self.assertRaises(ValueError):
            parse_geojson('alert(1);')
        self.assertEqual(parse_geojson('var geoJSONPtoItinerariosPontos = {"type":"FeatureCollection","features":[]};')['features'], [])

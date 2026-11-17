import unittest

import pandas as pd

from services.connection_finder import find_connections, find_new_stop_candidates
from services.road_router import trace_line


class ConnectionTests(unittest.TestCase):
    def test_nearby_stops_are_candidates_and_far_stops_are_excluded(self):
        stops = pd.DataFrame([
            {"linha": "1", "parada_id": "A", "latitude": 0.0, "longitude": 0.0},
            {"linha": "2", "parada_id": "B", "latitude": 0.0, "longitude": 0.0005},
            {"linha": "2", "parada_id": "C", "latitude": 0.0, "longitude": 0.01},
        ])
        found = find_connections(stops, "1", "2")
        self.assertEqual([(item["stop1"], item["stop2"]) for item in found], [("A", "B")])
        self.assertGreater(found[0]["distance_m"], 50)

    def test_same_stop_id_is_zero_distance(self):
        stops = pd.DataFrame([
            {"linha": "1", "parada_id": "A", "latitude": -22.9, "longitude": -47.0},
            {"linha": "2", "parada_id": "A", "latitude": -22.9, "longitude": -47.0},
        ])
        self.assertEqual(find_connections(stops, "1", "2")[0]["distance_m"], 0)

    def test_line_is_traced_through_streets_in_stop_order(self):
        edges = pd.DataFrame([
            {"linha": "1", "sentido": "1", "sequencia": "2", "origem": "B", "destino": "C"},
            {"linha": "1", "sentido": "1", "sequencia": "1", "origem": "A", "destino": "B"},
        ])
        coords = {"A": [0, 0], "B": [0, 1], "C": [0, 2]}
        received = []

        def router(stop_ids, _coords):
            received.append(stop_ids)
            return [[0, 0], [0.1, 1], [0, 2]]

        paths, fallback = trace_line(edges, coords, "1", router=router)
        self.assertEqual(received, [["A", "B", "C"]])
        self.assertEqual(fallback, 0)
        self.assertTrue(paths[0]["on_roads"])

    def test_new_stop_is_suggested_where_other_line_approaches_route(self):
        stops = pd.DataFrame([
            {"linha": "1", "parada_id": "A", "latitude": 0.0, "longitude": 0.0},
            {"linha": "1", "parada_id": "B", "latitude": 0.0, "longitude": 0.01},
            {"linha": "2", "parada_id": "X", "latitude": 0.001, "longitude": 0.005},
        ])
        paths = [{"line": "1", "points": [[0.0, 0.0], [0.0, 0.01]], "on_roads": True}]
        found = find_new_stop_candidates(stops, paths, "1", "2")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["feeder_stop"], "X")
        self.assertLessEqual(found[0]["distance_m"], 112)

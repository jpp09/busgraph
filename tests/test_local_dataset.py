import unittest

from data.local_loader import load_local_dataset
from services.graph_builder import build_graph
from core.route_optimizer import find_best_route
from services.map_view import load_map_stops, terminal_groups


class LocalDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.edges, cls.names, cls.report = load_local_dataset()
        cls.graph, _ = build_graph(cls.edges, 0, "custo_trecho")

    def test_real_dataset_has_unit_cost_without_invented_times(self):
        self.assertEqual(len(self.edges), self.report["trechos"])
        self.assertTrue((self.edges["duracao_min"] == "").all())
        self.assertTrue((self.edges["custo_trecho"] == 1).all())
        self.assertTrue(all(str(node[0]) in self.names for node in self.graph.adjacency))

    def test_route_between_consecutive_real_stops(self):
        edge = self.edges.iloc[0]
        result = find_best_route(self.graph, self.names,
                                 self.names[edge["origem"]], self.names[edge["destino"]])
        self.assertEqual(result["total_cost"], 1)
        self.assertEqual(result["ride_segments"], 1)

    def test_repeated_occurrences_are_separate_states(self):
        import pandas as pd
        edges = pd.DataFrame([
            dict(origem="A", destino="B", linha="1", custo_trecho=1,
                 estado_origem=("1", 1), estado_destino=("1", 2)),
            dict(origem="B", destino="C", linha="1", custo_trecho=1,
                 estado_origem=("2", 4), estado_destino=("2", 5)),
        ])
        graph, names = build_graph(edges, 0, "custo_trecho")
        self.assertIsNone(find_best_route(graph, names, "A", "C"))

    def test_campo_grande_platform_reaches_terminal_central(self):
        graph, _ = build_graph(self.edges, 0, "custo_trecho",
                               terminal_groups=terminal_groups(load_map_stops()))
        origin = self.names["61589"]
        destinations = [name for name in self.names.values() if name.startswith("TERMINAL CENTRAL")]
        self.assertTrue(any(find_best_route(graph, self.names, origin, name) for name in destinations))

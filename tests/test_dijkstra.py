import unittest
from core.graph import Graph
from core.dijkstra import shortest_path

class DijkstraTests(unittest.TestCase):
    def test_shortest_path(self):
        g = Graph()
        g.add_edge(("A", "1"), ("B", "1"), 10, line="1")
        g.add_edge(("A", "1"), ("C", "1"), 3, line="1")
        g.add_edge(("C", "1"), ("B", "1"), 2, line="1")
        cost, path = shortest_path(g, [("A", "1")], [("B", "1")])
        self.assertEqual(cost, 5)
        self.assertEqual(len(path), 2)

    def test_unreachable(self):
        g = Graph()
        g.add_edge(("A", "1"), ("B", "1"), 1)
        self.assertIsNone(shortest_path(g, [("A", "1")], [("Z", "1")]))

if __name__ == "__main__":
    unittest.main()

from collections import defaultdict

class Graph:
    """Grafo direcionado e ponderado: nó = (identificador da parada, linha)."""
    def __init__(self):
        self.adjacency = defaultdict(list)

    def add_edge(self, source, target, weight, kind="ride", line=None):
        if weight < 0:
            raise ValueError("Dijkstra exige pesos não negativos.")
        self.adjacency[source].append({
            "target": target, "weight": float(weight), "kind": kind, "line": line
        })
        self.adjacency.setdefault(target, [])

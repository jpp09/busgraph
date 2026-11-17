import heapq

def shortest_path(graph, starts, goals):
    """Dijkstra multi-origem/multi-destino. Retorna (custo, caminho de arestas)."""
    distances = {}
    previous = {}
    queue = []
    for node in starts:
        distances[node] = 0.0
        heapq.heappush(queue, (0.0, node))

    goal_set = set(goals)
    final = None
    while queue:
        distance, node = heapq.heappop(queue)
        if distance != distances.get(node):
            continue
        if node in goal_set:
            final = node
            break
        for edge in graph.adjacency.get(node, []):
            nxt = edge["target"]
            candidate = distance + edge["weight"]
            if candidate < distances.get(nxt, float("inf")):
                distances[nxt] = candidate
                previous[nxt] = (node, edge)
                heapq.heappush(queue, (candidate, nxt))

    if final is None:
        return None
    path = []
    current = final
    while current in previous:
        prev, edge = previous[current]
        path.append((prev, current, edge))
        current = prev
    path.reverse()
    return distances[final], path

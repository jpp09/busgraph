from core.dijkstra import shortest_path

def find_best_route(graph, stop_names, origin_name, destination_name):
    starts = [node for node in graph.adjacency if stop_names.get(node[0], node[0]) == origin_name]
    goals = [node for node in graph.adjacency if stop_names.get(node[0], node[0]) == destination_name]
    if not starts or not goals:
        return None
    result = shortest_path(graph, starts, goals)
    if result is None:
        return None
    total, path = result
    steps, lines = [], []
    transfers = 0
    platform_links = []
    for source, target, edge in path:
        if edge["kind"] == "transfer":
            if source[1] != target[1]:
                transfers += 1
            if source[0] != target[0]:
                platform_links.append((source[0], target[0]))
        if edge["kind"] == "ride":
            line = str(edge["line"] or source[1])
            if not lines or lines[-1] != line:
                lines.append(line)
            steps.append({
                "from_id": source[0],
                "to_id": target[0],
                "from": stop_names.get(source[0], source[0]),
                "to": stop_names.get(target[0], target[0]),
                "line": line,
                "minutes": edge["weight"]
            })
    return {
        "total_minutes": total,
        "total_cost": total,
        "ride_segments": len(steps),
        "steps": steps,
        "lines": lines,
        "transfers": transfers,
        "platform_links": platform_links
    }

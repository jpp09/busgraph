from core.graph import Graph

def build_graph(edges, transfer_penalty=5.0, weight_column="duracao_min", terminal_groups=None):
    graph = Graph()
    stop_names = {}
    routes_by_stop = {}

    for row in edges.to_dict("records"):
        origin, destination, line = str(row["origem"]), str(row["destino"]), str(row["linha"])
        duration = float(row[weight_column])
        source, target = (origin, line), (destination, line)
        if "estado_origem" in row:
            source = (origin, line, row["estado_origem"])
            target = (destination, line, row["estado_destino"])
        graph.add_edge(source, target, duration, "ride", line)
        stop_names.setdefault(origin, origin)
        stop_names.setdefault(destination, destination)
        routes_by_stop.setdefault(origin, set()).add(source)
        routes_by_stop.setdefault(destination, set()).add(target)

    # A baldeação é modelada como aresta entre estados da mesma parada em linhas diferentes.
    for stop_id, lines in routes_by_stop.items():
        for from_line in lines:
            for to_line in lines:
                if from_line[1] != to_line[1]:
                    graph.add_edge(from_line, to_line,
                                   transfer_penalty, "transfer", None)
    if terminal_groups:
        for stop_ids in terminal_groups.values():
            for from_stop in stop_ids:
                for to_stop in stop_ids:
                    if from_stop == to_stop:
                        continue
                    for source in routes_by_stop.get(from_stop, ()):
                        for target in routes_by_stop.get(to_stop, ()):
                            graph.add_edge(source, target, transfer_penalty,
                                           "transfer", None)
    return graph, stop_names

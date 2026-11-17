"""Encontra possíveis conexões a pé entre duas linhas de ônibus."""
from math import asin, cos, radians, sin, sqrt


def distance_m(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    return 12742000 * asin(sqrt(sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2))


def find_connections(stops, line1, line2, max_distance_m=150):
    """Retorna pares de IDs de parada próximos, ordenados pela distância."""
    first = stops[stops.linha == line1].drop_duplicates("parada_id")
    second = stops[stops.linha == line2].drop_duplicates("parada_id")
    result = []
    for a in first.itertuples():
        for b in second.itertuples():
            distance = distance_m((a.latitude, a.longitude), (b.latitude, b.longitude))
            if distance <= max_distance_m:
                result.append({"stop1": a.parada_id, "stop2": b.parada_id,
                               "distance_m": round(distance),
                               "point1": [a.latitude, a.longitude],
                               "point2": [b.latitude, b.longitude]})
    return sorted(result, key=lambda item: (item["distance_m"], item["stop1"], item["stop2"]))


def _nearest_point_on_segment(point, start, end):
    """Projeta um ponto em um segmento usando coordenadas locais em metros."""
    reference_lat = radians((point[0] + start[0] + end[0]) / 3)
    scale_x = 111320 * cos(reference_lat)
    scale_y = 110540
    px, py = point[1] * scale_x, point[0] * scale_y
    ax, ay = start[1] * scale_x, start[0] * scale_y
    bx, by = end[1] * scale_x, end[0] * scale_y
    dx, dy = bx - ax, by - ay
    length_squared = dx * dx + dy * dy
    ratio = 0 if length_squared == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / length_squared))
    projected = [(ay + ratio * dy) / scale_y, (ax + ratio * dx) / scale_x]
    return projected, distance_m(point, projected)


def find_new_stop_candidates(stops, road_paths, target_line, feeder_line,
                             max_route_distance_m=200, existing_stop_radius_m=120,
                             cluster_radius_m=250):
    """Sugere novos pontos na linha alvo próximos a paradas da outra linha."""
    target_paths = [path["points"] for path in road_paths if path["line"] == target_line]
    target_stops = stops[stops.linha == target_line].drop_duplicates("parada_id")
    feeder_stops = stops[stops.linha == feeder_line].drop_duplicates("parada_id")
    candidates = []
    for stop in feeder_stops.itertuples():
        source = [stop.latitude, stop.longitude]
        nearest_point, nearest_distance = None, float("inf")
        for path in target_paths:
            for start, end in zip(path, path[1:]):
                projected, distance = _nearest_point_on_segment(source, start, end)
                if distance < nearest_distance:
                    nearest_point, nearest_distance = projected, distance
        if nearest_point is None or nearest_distance > max_route_distance_m:
            continue
        if any(distance_m(nearest_point, [row.latitude, row.longitude]) <= existing_stop_radius_m
               for row in target_stops.itertuples()):
            continue
        candidates.append({"new_line": target_line, "feeder_line": feeder_line,
                           "feeder_stop": stop.parada_id, "point": nearest_point,
                           "distance_m": round(nearest_distance)})
    selected = []
    for candidate in sorted(candidates, key=lambda item: item["distance_m"]):
        if all(distance_m(candidate["point"], other["point"]) > cluster_radius_m
               for other in selected):
            selected.append(candidate)
    return selected

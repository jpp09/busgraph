"""Traçado viário estimado para uma rota de ônibus já escolhida pelo grafo."""
import time

import requests

OSRM_URL = "https://router.project-osrm.org/route/v1/driving/"
MAX_STOPS = 20
_last_request = 0.0


def road_geometry(stop_ids, coords, request=requests.get):
    """Retorna pontos [lat, lon] ou None quando o serviço não encontra rota."""
    global _last_request
    pairs = [coords[sid] for sid in stop_ids]
    path = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in pairs)
    delay = 1.0 - (time.monotonic() - _last_request)
    if delay > 0:
        time.sleep(delay)
    _last_request = time.monotonic()
    try:
        response = request(OSRM_URL + path,
                           params={"overview": "full", "geometries": "geojson", "steps": "false"},
                           headers={"User-Agent": "BusGraph-academic/1.0 (https://github.com/joaom/busgraph)"},
                           timeout=15)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != "Ok" or not payload.get("routes"):
            return None
        points = payload["routes"][0]["geometry"]["coordinates"]
        if len(points) < 2:
            return None
        return [[lat, lon] for lon, lat in points]
    except (requests.RequestException, ValueError, KeyError, TypeError, IndexError):
        return None


def trace_route(steps, coords, router=road_geometry):
    """Agrupa trechos consecutivos da mesma linha para reduzir consultas."""
    groups = []
    for step in steps:
        if (groups and groups[-1][0] == step["line"]
                and groups[-1][1][-1] == step["from_id"]):
            groups[-1][1].append(step["to_id"])
        else:
            groups.append((step["line"], [step["from_id"], step["to_id"]]))
    traced, fallback = [], 0
    for line, stop_ids in groups:
        for offset in range(0, len(stop_ids) - 1, MAX_STOPS - 1):
            chunk = stop_ids[offset:offset + MAX_STOPS]
            if len(chunk) < 2:
                continue
            if any(sid not in coords for sid in chunk):
                geometry = None
            else:
                geometry = router(chunk, coords)
            on_roads = geometry is not None
            if not on_roads:
                geometry = [coords[sid] for sid in chunk if sid in coords]
                fallback += 1
            if len(geometry) >= 2:
                traced.append({"line": line, "points": geometry, "on_roads": on_roads})
    return traced, fallback


def trace_line(edges, coords, line, router=road_geometry):
    """Traça os sentidos de uma linha pelas ruas, respeitando a ordem das paradas."""
    selected = edges[edges.linha == line].copy()
    selected["sequencia_num"] = selected["sequencia"].astype(float)
    selected = selected.sort_values(["sentido", "sequencia_num"])
    steps = [{"from_id": row.origem, "to_id": row.destino, "line": line}
             for row in selected.itertuples()]
    return trace_route(steps, coords, router=router)

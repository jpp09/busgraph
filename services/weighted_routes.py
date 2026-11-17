"""Grafo de distâncias viárias e propostas de paradas a cada ~300 m.

Arestas oficiais recebem o peso da respectiva ``legs[].distance`` do OSRM.
Propostas usam comprimento da polilinha viária (Haversine entre vértices)
para posicionar marcos de 300 m, sem modificar vias ou criar atalhos.
"""

from __future__ import annotations

from collections import defaultdict
from math import asin, cos, isfinite, radians, sin, sqrt

from services.road_router import road_route_details


def distance_m(a, b):
    dlat = radians(float(b[0]) - float(a[0]))
    dlon = radians(float(b[1]) - float(a[1]))
    lat1 = radians(float(a[0])); lat2 = radians(float(b[0]))
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 12742000 * asin(min(1.0, sqrt(h)))


def polyline_length(points):
    return sum(distance_m(a, b) for a, b in zip(points, points[1:]))


def _stop_meta(point, index):
    return {"stop_id": f"sem-id-{index}", "sequence": index,
            "key": ("parada", index), "point": [float(point[0]), float(point[1])]}


def _join_lines(parts, max_gap_m=25):
    result = []
    for part in parts:
        if not part:
            continue
        if result and distance_m(result[-1], part[0]) > max_gap_m:
            return None
        for point in part:
            if not result or distance_m(result[-1], point) >= 0.05:
                result.append([float(point[0]), float(point[1])])
    return result if len(result) >= 2 else None


def build_weighted_road_paths(paths, router=road_route_details, max_waypoints=20, snap_limit_m=120):
    """Roteia em lotes e gera aresta individual com peso viário por par de paradas.

    Um lote sem resposta é marcado sem peso; nunca usa distância reta como se
    fosse distância viária nem desenha atalhos entre os pontos.
    """
    if max_waypoints < 2:
        raise ValueError("max_waypoints deve ser >= 2")
    result = []
    rejected = 0
    for group_num, path in enumerate(paths):
        stops = path.get("stops") or [_stop_meta(p, i) for i, p in enumerate(path["points"])]
        if len(stops) != len(path["points"]):
            raise ValueError("As ocorrências de paradas não correspondem aos pontos da rota")
        group_id = path.get("group_id", f"{path.get('line', 'linha')}/{path.get('direction', 'ida')}/{group_num}")
        for offset in range(0, len(stops) - 1, max_waypoints - 1):
            selected = stops[offset: offset + max_waypoints]
            if len(selected) < 2:
                continue
            coords = {str(i): s["point"] for i, s in enumerate(selected)}
            details = None
            try:
                details = router(list(coords), coords)
            except Exception:
                pass
            valid = isinstance(details, dict) and isinstance(details.get("legs"), list)
            valid = bool(valid and len(details["legs"]) == len(selected) - 1)
            legs = []
            if valid:
                for idx, osrm_leg in enumerate(details["legs"]):
                    try:
                        geometry = osrm_leg["geometry"]
                        weight = float(osrm_leg["distance_m"])
                        good = (isfinite(weight) and weight >= 0 and isinstance(geometry, list)
                                and len(geometry) >= 2
                                and distance_m(geometry[0], selected[idx]["point"]) <= snap_limit_m
                                and distance_m(geometry[-1], selected[idx+1]["point"]) <= snap_limit_m)
                        if not good:
                            valid = False
                            break
                        legs.append({"from_stop": selected[idx], "to_stop": selected[idx + 1],
                                     "geometry": geometry, "weight_m": weight})
                    except (KeyError, ValueError, TypeError, IndexError, OverflowError):
                        valid = False
                        break
            polyline = _join_lines([leg["geometry"] for leg in legs]) if valid else None
            if polyline is None:
                valid = False
            if not valid:
                rejected += 1
            result.append({"line": str(path["line"]), "direction": str(path["direction"]),
                           "group_id": group_id, "points": polyline if valid else [s["point"] for s in selected],
                           "stops": selected, "segments": legs if valid else [],
                           "distance_m": sum(x["weight_m"] for x in legs) if valid else None,
                           "on_roads": valid,
                           "source": "OSRM: distância entre paradas, em metros" if valid else "Sem distância viária validada"})
    return result, rejected


def distance_table(routed_paths):
    """Tabela de distâncias: P0=0; arestas P0→P1 etc; acumulado por trecho conexo.

    Caso um lote não possua rota viária, o total acumulado é reiniciado
    num trecho novo; jamais se soma um intervalo de distância desconhecida.
    """
    records = []
    state = {}
    for path in routed_paths:
        group = path["group_id"]
        tracker = state.setdefault(group, {"fragment": 0, "last_key": None, "meters": 0., "broken": False})
        if not path["on_roads"]:
            tracker["broken"] = True
            tracker["last_key"] = None
            for stop in path["stops"]:
                records.append({"Linha": path["line"], "Trecho": group, "Fragmento": "sem rota",
                                "Ponto": "—", "Parada": stop["stop_id"],
                                "Sequência EMDEC": stop["sequence"],
                                "Distância anterior (m)": None, "Acumulado (m)": None,
                                "Situação": "OSRM indisponível / trecho não validado"})
            continue
        first = path["stops"][0]
        continuing = tracker["last_key"] == first["key"] and not tracker["broken"]
        if not continuing:
            tracker["fragment"] += 1
            tracker["meters"] = 0.
            tracker["index"] = 0
            records.append({"Linha": path["line"], "Trecho": group,
                            "Fragmento": tracker["fragment"], "Ponto": 0,
                            "Parada": first["stop_id"], "Sequência EMDEC": first["sequence"],
                            "Distância anterior (m)": 0., "Acumulado (m)": 0.,
                            "Situação": "Início" if not tracker["broken"] else "Retomada após lacuna"})
        tracker["broken"] = False
        for segment in path["segments"]:
            tracker["meters"] += segment["weight_m"]
            tracker["index"] += 1
            end = segment["to_stop"]
            records.append({"Linha": path["line"], "Trecho": group,
                            "Fragmento": tracker["fragment"], "Ponto": tracker["index"],
                            "Parada": end["stop_id"], "Sequência EMDEC": end["sequence"],
                            "Distância anterior (m)": round(segment["weight_m"], 1),
                            "Acumulado (m)": round(tracker["meters"], 1), "Situação": "Validado nas ruas"})
            tracker["last_key"] = end["key"]
    return records


def build_distance_graph(routed_paths):
    """Adjacência dirigida e ponderada; cada nó é ocorrência, não ID global.

    Dijkstra pode usar ``(node, peso_m)`` sem converter metros em minutos.
    """
    adjacency = defaultdict(list)
    for path in routed_paths:
        if not path["on_roads"]:
            continue
        for seg in path["segments"]:
            def vertex(stop):
                return (path["line"], path["direction"], path["group_id"],
                        str(stop["sequence"]), str(stop["stop_id"]))
            u, v = vertex(seg["from_stop"]), vertex(seg["to_stop"])
            adjacency[u].append((v, seg["weight_m"]))
            adjacency.setdefault(v, [])
    return dict(adjacency)


def _sample_polyline(points, target_m):
    remain = target_m
    for a, b in zip(points, points[1:]):
        length = distance_m(a, b)
        if remain <= length:
            factor = remain / length if length else 0.
            return [float(a[0]) + factor * (float(b[0]) - float(a[0])),
                    float(a[1]) + factor * (float(b[1]) - float(a[1]))]
        remain -= length
    return list(points[-1])


def suggest_route_300m(routed_paths, spacing_m=300., existing_tolerance_m=70.):
    """Gera novo plano de paradas SOBRE a mesma geometria viária validada.

    Não descobre outro itinerário de ruas: sugere uma redistribuição de pontos
    a cada ~300m, diferenciando paradas EMDEC já próximas ao marco e novos pontos.
    Lacunas na consulta OSRM quebram a rota sugerida, evitando atalhos fictícios.
    """
    if spacing_m <= 0:
        raise ValueError("spacing_m precisa ser positivo")
    if existing_tolerance_m < 0:
        raise ValueError("existing_tolerance_m não pode ser negativo")
    fragments = []
    current = None

    def finalize():
        nonlocal current
        if not current or not current["legs"]:
            current = None
            return
        geometry = _join_lines([x["geometry"] for x in current["legs"]])
        if geometry is None:
            current = None
            return
        total = polyline_length(geometry)
        if total <= 0:
            current = None
            return
        # As âncoras de paradas são medidas ao longo da geometria, não por
        # distância espacial: uma rota em U pode passar perto de outro ponto.
        anchors = [(0., current["legs"][0]["from_stop"])]
        progressed = 0.
        for leg in current["legs"]:
            progressed += polyline_length(leg["geometry"])
            anchors.append((progressed, leg["to_stop"]))
        # Ajusta a soma de pernas para a pequena diferença de deduplicação.
        scale = total / progressed if progressed else 1.
        anchors = [(d * scale, stop) for d, stop in anchors]
        targets = [0.]
        step = spacing_m
        while step < total - 1e-6:
            targets.append(step)
            step += spacing_m
        if total - targets[-1] > 1e-6:
            targets.append(total)
        points = []
        for idx, chainage in enumerate(targets):
            nearest_d, nearest_stop = min(anchors, key=lambda row: abs(row[0] - chainage))
            if idx == 0:
                kind = "Início"
            elif idx == len(targets) - 1:
                kind = "Terminal"
            elif abs(nearest_d - chainage) <= existing_tolerance_m:
                kind = "Existente próxima"
            else:
                kind = "Novo ponto sugerido"
            points.append({"index": idx, "distance_m": round(chainage, 1),
                           "gap_m": round(chainage - targets[idx - 1], 1) if idx else 0.,
                           "point": _sample_polyline(geometry, chainage), "kind": kind,
                           "near_stop_id": nearest_stop["stop_id"] if kind == "Existente próxima" else None})
        fragments.append({"line": current["line"], "direction": current["direction"],
                          "group_id": current["group_id"], "fragment": current["fragment"],
                          "points": points, "geometry": geometry,
                          "distance_m": round(total, 1),
                          "new_stop_count": sum(p["kind"] == "Novo ponto sugerido" for p in points)})
        current = None

    fragment_counter = defaultdict(int)
    for path in routed_paths:
        if not path["on_roads"]:
            finalize()
            continue
        connected = (current is not None and path["group_id"] == current["group_id"]
                     and current["legs"][-1]["to_stop"]["key"] == path["segments"][0]["from_stop"]["key"])
        if not connected:
            finalize()
            fragment_counter[path["group_id"]] += 1
            current = {"line": path["line"], "direction": path["direction"],
                       "group_id": path["group_id"], "fragment": fragment_counter[path["group_id"]],
                       "legs": []}
        current["legs"].extend(path["segments"])
    finalize()
    return fragments

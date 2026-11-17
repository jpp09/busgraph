"""Roteamento viário do BusGraph usando OSRM (geometria sobre ruas).

Recebe coordenadas em [latitude, longitude], conforme Folium, e faz a
conversão lon,lat exigida pela API do OSRM. Retorna None quando não existe
rota validável: o chamador não deve substituí-la por uma linha reta como
se fosse trajeto de ônibus.
"""

from __future__ import annotations

import math

import requests

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


def _coordinate(point):
    if not isinstance(point, (tuple, list)) or len(point) < 2:
        return None
    try:
        lat, lon = float(point[0]), float(point[1])
    except (ValueError, TypeError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def road_geometry(stop_ids, coords, *, base_url=OSRM_URL, request_get=None, max_snap_m=120):
    """Retorna geometria de rua [lat,lon] respeitando a ordem das paradas.

    É uma *estimativa viária*, não um itinerário homologado pela EMDEC.
    ``stop_ids`` mantém a ordem; ``coords`` é um dicionário stop_id -> [lat,lon].
    A função falha de forma segura para problemas HTTP, pontos distantes
    das ruas ou respostas inválidas.
    """
    if not 2 <= len(stop_ids) <= 50:
        return None
    points = []
    for stop_id in stop_ids:
        pt = _coordinate(coords.get(stop_id))
        if pt is None:
            return None
        points.append(pt)

    # A rota de carros percorre segmentos conectados da malha viária;
    # a origem e os pontos de passagem são preservados na ordem recebida.
    coords_path = ";".join(f"{lon:.7f},{lat:.7f}" for lat, lon in points)
    params = {"overview": "full", "geometries": "geojson", "steps": "false", "alternatives": "false"}
    getter = request_get or requests.get
    try:
        response = getter(f"{base_url}/{coords_path}", params=params,
                          timeout=(4, 15),
                          headers={"User-Agent": "BusGraph-Campinas-Academico/1.0"})
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError, TypeError):
        return None

    if not isinstance(payload, dict) or payload.get("code") != "Ok":
        return None
    routes = payload.get("routes") or []
    waypoints = payload.get("waypoints") or []
    if not isinstance(routes, list) or not routes or not isinstance(routes[0], dict):
        return None
    if not isinstance(waypoints, list) or len(waypoints) != len(points):
        return None
    for waypoint in waypoints:
        # OSRM retorna a distância entre a parada original e a rua escolhida.
        if not isinstance(waypoint, dict):
            return None
        try:
            snap_distance = float(waypoint.get("distance", float("inf")))
        except (TypeError, ValueError):
            return None
        if not math.isfinite(snap_distance) or snap_distance > max_snap_m:
            return None

    geometry = routes[0].get("geometry") or {}
    raw = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if not isinstance(raw, list) or len(raw) < 2:
        return None
    result = []
    for pair in raw:
        if not isinstance(pair, (tuple, list)) or len(pair) < 2:
            return None
        # GeoJSON fornece [lon,lat]; Folium espera [lat,lon].
        valid = _coordinate([pair[1], pair[0]])
        if valid is None:
            return None
        result.append([valid[0], valid[1]])
    return result


def road_route_details(stop_ids, coords, *, base_url=OSRM_URL, request_get=None, max_snap_m=120):
    """Retorna *cada perna* do OSRM com distância viária, em metros.

    Usa legs[i].distance como peso (não Haversine); geometria de cada leg
    é montada a partir de steps[i].geometry em GeoJSON, sempre [lat, lon].
    Nunca inventa peso ou geometria caso o provedor não os tenha retornado.
    """
    if not 2 <= len(stop_ids) <= 50:
        return None
    points = [_coordinate(coords.get(stop_id)) for stop_id in stop_ids]
    if any(point is None for point in points):
        return None
    coords_path = ";".join(f"{lon:.7f},{lat:.7f}" for lat, lon in points)
    params = {"overview": "full", "geometries": "geojson", "steps": "true",
              "alternatives": "false"}
    getter = request_get or requests.get
    try:
        response = getter(f"{base_url}/{coords_path}", params=params,
                          timeout=(4, 20),
                          headers={"User-Agent": "BusGraph-Campinas-Academico/1.0"})
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError, TypeError):
        return None
    if not isinstance(payload, dict) or payload.get("code") != "Ok":
        return None
    routes = payload.get("routes") or []
    waypoints = payload.get("waypoints") or []
    if not routes or not isinstance(routes[0], dict) or len(waypoints) != len(points):
        return None
    legs = routes[0].get("legs") or []
    if len(legs) != len(points) - 1:
        return None

    for waypoint in waypoints:
        if not isinstance(waypoint, dict):
            return None
        try:
            snap = float(waypoint.get("distance", float("inf")))
        except (ValueError, TypeError):
            return None
        if not math.isfinite(snap) or snap < 0 or snap > max_snap_m:
            return None

    from math import asin, cos, radians, sin, sqrt

    def distance(a, b):
        dlat = radians(a[0] - b[0])
        dlon = radians(a[1] - b[1])
        h = sin(dlat / 2) ** 2 + cos(radians(a[0])) * cos(radians(b[0])) * sin(dlon / 2) ** 2
        return 2 * 6371000 * asin(min(1.0, sqrt(h)))

    def parse_step(step):
        if not isinstance(step, dict):
            return None
        geometry = step.get("geometry") or {}
        raw = geometry.get("coordinates") if isinstance(geometry, dict) else None
        if not isinstance(raw, list):
            return None
        result = []
        for xy in raw:
            if not isinstance(xy, (list, tuple)) or len(xy) < 2:
                return None
            coordinate = _coordinate([xy[1], xy[0]])
            if coordinate is None:
                return None
            result.append([coordinate[0], coordinate[1]])
        return result

    detailed_legs = []
    for i, leg in enumerate(legs):
        if not isinstance(leg, dict):
            return None
        try:
            meters = float(leg["distance"])
        except (KeyError, TypeError, ValueError):
            return None
        if not math.isfinite(meters) or meters < 0:
            return None
        steps = leg.get("steps")
        if not isinstance(steps, list) or not steps:
            return None
        geometry = []
        for step in steps:
            partial = parse_step(step)
            if partial is None:
                return None
            if not partial:
                continue
            if geometry and distance(geometry[-1], partial[0]) > 25:
                return None  # ligação ausente: não inventar segmento reto
            for pt in partial:
                if not geometry or distance(geometry[-1], pt) > 0.05:
                    geometry.append(pt)
        if len(geometry) < 2:
            if meters > 0:
                return None
            # Permanecer no mesmo ponto pode gerar uma geometria sem deslocamento.
            if not geometry:
                return None
            geometry = [geometry[0], geometry[0]]
        if distance(geometry[0], points[i]) > max_snap_m or distance(geometry[-1], points[i + 1]) > max_snap_m:
            return None
        detailed_legs.append({"distance_m": meters, "geometry": geometry})
    return {"legs": detailed_legs,
            "distance_m": sum(leg["distance_m"] for leg in detailed_legs),
            "source": "OSRM legs.distance; geometria de steps"}

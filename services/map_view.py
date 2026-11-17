"""Mapa da rota calculada sobre OpenStreetMap."""
from html import escape
from math import asin, cos, radians, sin, sqrt
import re
import unicodedata

import folium
import pandas as pd
from branca.element import Element
from folium.plugins import MarkerCluster

from data.local_loader import DEFAULT_DATASET

COLORS = ["#2563eb", "#dc2626", "#059669", "#9333ea", "#d97706"]


def load_map_stops():
    stops = pd.read_csv(DEFAULT_DATASET / "paradas.csv", dtype=str, keep_default_na=False)
    for column in ("latitude", "longitude"):
        stops[column] = pd.to_numeric(stops[column], errors="coerce")
    return stops[stops.latitude.between(-90, 90) & stops.longitude.between(-180, 180)]


def stop_coordinates(stops):
    points = stops.drop_duplicates("parada_id").set_index("parada_id")
    return {sid: [row.latitude, row.longitude] for sid, row in points.iterrows()}


def terminal_groups(stops, max_distance_m=180):
    """Agrupa plataformas próximas identificadas com o mesmo terminal."""
    candidates = {}
    for row in stops.drop_duplicates("parada_id").itertuples():
        label = unicodedata.normalize("NFKD", row.logradouro).encode("ascii", "ignore").decode().upper()
        label = re.sub(r"\s+(BXC|CXB)$", "", label).strip()
        if label.startswith("TERMINAL "):
            candidates.setdefault(label, []).append((row.parada_id, row.latitude, row.longitude))
    groups = {}
    for label, points in candidates.items():
        # Componentes por proximidade: terminais com o mesmo nome em locais
        # diferentes não são unidos automaticamente.
        parent = {sid: sid for sid, _, _ in points}
        def root(sid):
            while parent[sid] != sid:
                sid = parent[sid]
            return sid
        for i, (a, lat1, lon1) in enumerate(points):
            for b, lat2, lon2 in points[i + 1:]:
                dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
                radius = 6371000
                distance = 2 * radius * asin(sqrt(sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2))
                if distance <= max_distance_m:
                    parent[root(b)] = root(a)
        components = {}
        for sid, _, _ in points:
            components.setdefault(root(sid), set()).add(sid)
        for first, ids in components.items():
            if len(ids) > 1:
                groups[f"{label}:{first}"] = ids
    return groups


def build_map(stops, names, result=None, origin_id=None, destination_id=None, road_paths=None):
    coords = stop_coordinates(stops)
    map_obj = folium.Map(location=[-22.9056, -47.0608], zoom_start=12,
                         tiles="OpenStreetMap", prefer_canvas=True)
    route_points = []
    if result:
        for start, end in result.get("platform_links", []):
            if start in coords and end in coords:
                route_points.extend([coords[start], coords[end]])
                folium.PolyLine([coords[start], coords[end]], color="#f59e0b",
                                weight=3, dash_array="5, 6",
                                tooltip="Conexão aproximada entre plataformas").add_to(map_obj)
        colors = {line: COLORS[i % len(COLORS)] for i, line in enumerate(dict.fromkeys(result["lines"]))}
        previous_line = None
        for step in result["steps"]:
            start, end = step["from_id"], step["to_id"]
            if start in coords and end in coords:
                route_points.extend([coords[start], coords[end]])
                if previous_line is not None and previous_line != step["line"]:
                    folium.Marker(coords[start], tooltip="Baldeação",
                                  icon=folium.Icon(color="orange", icon="exchange", prefix="fa")).add_to(map_obj)
            previous_line = step["line"]
        for path in road_paths or []:
            folium.PolyLine(path["points"], color=colors[path["line"]], weight=6,
                            dash_array=None if path["on_roads"] else "8, 8",
                            tooltip=f"Linha {escape(path['line'])}" + (" (aproximação)" if not path["on_roads"] else "")).add_to(map_obj)
    for sid, label, color in [(origin_id, "Origem", "green"), (destination_id, "Destino", "red")]:
        if sid in coords:
            folium.Marker(coords[sid], tooltip=f"{label}: {escape(names[sid])}",
                          icon=folium.Icon(color=color)).add_to(map_obj)
    bounds = route_points or [coords[sid] for sid in (origin_id, destination_id) if sid in coords]
    if bounds:
        map_obj.fit_bounds(bounds, max_zoom=16)
    return map_obj


def build_connection_map(stops, edges, line1, line2, connections, names, road_paths=None,
                         new_stops_line1=None, new_stops_line2=None):
    """Exibe os dois itinerários sobre as ruas e conexões candidatas."""
    coords = stop_coordinates(stops)
    map_obj = folium.Map(location=[-22.9056, -47.0608], zoom_start=12,
                         tiles="OpenStreetMap", prefer_canvas=True)
    for line, color in ((line1, COLORS[0]), (line2, COLORS[1])):
        layer = folium.FeatureGroup(name=f"Linha {line}").add_to(map_obj)
        paths = [path for path in (road_paths or []) if path["line"] == line]
        if paths:
            for path in paths:
                folium.PolyLine(path["points"], color=color, weight=5, opacity=0.85,
                                dash_array=None if path["on_roads"] else "8, 8",
                                tooltip=f"Linha {escape(line)}" +
                                        (" (aproximação)" if not path["on_roads"] else "")).add_to(layer)
        else:
            for row in edges[edges.linha == line].itertuples():
                if row.origem in coords and row.destino in coords:
                    folium.PolyLine([coords[row.origem], coords[row.destino]], color=color,
                                    weight=5, opacity=0.85, dash_array="8, 8",
                                    tooltip=f"Linha {escape(line)} (aproximação)").add_to(layer)
    cluster = MarkerCluster(name="Possíveis conexões").add_to(map_obj)
    for i, item in enumerate(connections, 1):
        a, b = item["point1"], item["point2"]
        midpoint = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]
        folium.CircleMarker(midpoint, radius=8, color="#f59e0b", fill=True,
                            fill_color="#f59e0b", fill_opacity=0.9,
                            tooltip=f"Conexão {i}: {item['distance_m']} m",
                            popup=(f"Linhas {escape(line1)} ↔ {escape(line2)}<br>"
                                   f"{escape(names.get(item['stop1'], item['stop1']))}<br>"
                                   f"{escape(names.get(item['stop2'], item['stop2']))}<br>"
                                   f"Distância em linha reta: {item['distance_m']} m")).add_to(cluster)
        if a != b:
            folium.PolyLine([a, b], color="#f59e0b", weight=2,
                            dash_array="4, 6", opacity=0.7).add_to(map_obj)
    for suggestions, line, color in ((new_stops_line1 or [], line1, COLORS[0]),
                                      (new_stops_line2 or [], line2, COLORS[1])):
        layer = folium.FeatureGroup(name=f"Novos pontos na linha {line}").add_to(map_obj)
        for i, item in enumerate(suggestions, 1):
            folium.Circle(item["point"], radius=120, color=color, weight=2,
                          fill=True, fill_color=color, fill_opacity=0.14,
                          tooltip=f"Área candidata para novo ponto na linha {escape(line)}").add_to(layer)
            folium.CircleMarker(item["point"], radius=7, color="white", weight=2,
                                fill=True, fill_color=color, fill_opacity=1,
                                popup=(f"Novo ponto candidato na linha {escape(line)}<br>"
                                       f"Conecta com a linha {escape(item['feeder_line'])}<br>"
                                       f"Próximo à parada {escape(item['feeder_stop'])}<br>"
                                       f"Distância até o trajeto: {item['distance_m']} m")).add_to(layer)
    visible = stops[stops.linha.isin([line1, line2])]
    bounds = [coords[sid] for sid in visible.parada_id.unique() if sid in coords]
    if bounds:
        map_obj.fit_bounds(bounds, max_zoom=15)
    if line1 and line2:
        legend = f"""
        <div style="position: fixed; bottom: 28px; left: 28px; z-index: 9999;
                    background: white; border: 2px solid #d1d5db; border-radius: 8px;
                    padding: 10px 14px; box-shadow: 0 2px 8px rgba(0,0,0,.2);
                    font: 14px/1.5 Arial, sans-serif; color: #111827;">
          <div style="font-weight: 700; margin-bottom: 6px;">Legenda</div>
          <div><span style="display:inline-block;width:28px;border-top:5px solid {COLORS[0]};margin-right:8px;vertical-align:middle"></span>Linha {escape(line1)}</div>
          <div><span style="display:inline-block;width:28px;border-top:5px solid {COLORS[1]};margin-right:8px;vertical-align:middle"></span>Linha {escape(line2)}</div>
          <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#f59e0b;margin:0 16px 0 8px;vertical-align:middle"></span>Possível conexão</div>
          <div><span style="display:inline-block;width:28px;border-top:2px dashed #f59e0b;margin-right:8px;vertical-align:middle"></span>Distância entre paradas</div>
          <div><span style="display:inline-block;width:12px;height:12px;border:3px solid {COLORS[0]};border-radius:50%;margin:0 13px 0 5px;vertical-align:middle"></span>Novo ponto na linha {escape(line1)}</div>
          <div><span style="display:inline-block;width:12px;height:12px;border:3px solid {COLORS[1]};border-radius:50%;margin:0 13px 0 5px;vertical-align:middle"></span>Novo ponto na linha {escape(line2)}</div>
        </div>
        """
        map_obj.get_root().html.add_child(Element(legend))
    folium.LayerControl().add_to(map_obj)
    return map_obj

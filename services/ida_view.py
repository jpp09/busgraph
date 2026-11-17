"""Visualização de ida do BusGraph com paradas ancoradas na base EMDEC.

Não modifica a base de dados. Não assume que um trajeto viário estimado
seja o itinerário oficial de ônibus.
"""

from __future__ import annotations

from html import escape
from math import asin, atan2, cos, degrees, radians, sin, sqrt
import unicodedata

import folium
import pandas as pd

from services.road_router import road_geometry

CENTER = (-22.9056, -47.0608)  # Campinas, somente para o centro inicial do mapa
COLORS = ("#2563eb", "#dc2626")


def _add_direction_arrow(geometry, parent, color):
    """Adiciona uma seta no meio do trecho sem depender de plugin externo."""
    if len(geometry) < 2:
        return
    lengths = [_distance_m(a, b) for a, b in zip(geometry, geometry[1:])]
    total = sum(lengths)
    if total <= 0:
        return
    target = total / 2
    travelled = 0.0
    for start, end, length in zip(geometry, geometry[1:], lengths):
        if travelled + length < target or length <= 0:
            travelled += length
            continue
        fraction = (target - travelled) / length
        lat = float(start[0]) + (float(end[0]) - float(start[0])) * fraction
        lon = float(start[1]) + (float(end[1]) - float(start[1])) * fraction
        mean_lat = radians((float(start[0]) + float(end[0])) / 2)
        east = (float(end[1]) - float(start[1])) * cos(mean_lat)
        north = float(end[0]) - float(start[0])
        angle = degrees(atan2(-north, east))
        icon = folium.DivIcon(
            class_name="route-direction-arrow",
            icon_size=(22, 22),
            icon_anchor=(11, 11),
            html=(f'<div style="color:{color};font-size:20px;font-weight:900;line-height:22px;'
                  f'text-shadow:-1px -1px 0 #fff,1px -1px 0 #fff,-1px 1px 0 #fff,1px 1px 0 #fff;'
                  f'transform:rotate({angle:.1f}deg)">➤</div>'),
        )
        folium.Marker([lat, lon], icon=icon, tooltip="Sentido da rota").add_to(parent)
        return


def _text(value):
    return str(value).strip()


def _ascii(value):
    return unicodedata.normalize("NFKD", _text(value)).encode("ascii", "ignore").decode().lower()


def choose_ida(sentidos):
    """Resolve rótulos de ida. Retorna (valor_original, confianca, explicacao).

    O valor 0 representa ida no GTFS, mas CSVs de terceiros podem adotar
    convenções próprias. Ambiguidades não são resolvidas por posição na lista.
    """
    values = sorted({_text(v) for v in sentidos if _text(v)})
    if not values:
        return None, False, "A linha não possui identificação do sentido."

    explicit = [v for v in values if _ascii(v) in ("ida", "outbound", "out", "i", "ida (0)")]
    if len(explicit) == 1:
        return explicit[0], True, "Sentido identificado pelo rótulo de ida."
    if len(explicit) > 1:
        return None, False, "Mais de um valor foi identificado como ida."

    numeric = set(values)
    if numeric == {"0", "1"} or ("0" in numeric and "1" in numeric and numeric <= {"0", "1", "2"}):
        return "0", False, "Usando a convenção GTFS (0 = ida). Confirme a convenção da EMDEC."
    if numeric == {"1", "2"}:
        return "1", False, "Usando a convenção 1 = ida. Confirme no cadastro da linha."
    if len(values) == 1 and values[0] in ("0", "1"):
        return values[0], False, "Há somente um sentido numérico cadastrado; confirme se é ida."
    return None, False, f"Sentido ambíguo: {', '.join(values)}. Não exibido automaticamente."


def _valid_campinas(lat, lon):
    # Limites amplos para identificar coordenadas invertidas ou fora da região.
    return -23.65 <= lat <= -22.25 and -47.95 <= lon <= -46.25


def clean_stop_coordinates(stops):
    """Valida lat/lon e corrige inversões somente quando inequívocas.

    A correção é feita em memória; o CSV original permanece intocado.
    """
    data = stops.copy()
    data["latitude"] = pd.to_numeric(data["latitude"], errors="coerce")
    data["longitude"] = pd.to_numeric(data["longitude"], errors="coerce")
    swapped = 0
    invalid = 0
    for idx, row in data.iterrows():
        lat, lon = row["latitude"], row["longitude"]
        if pd.notna(lat) and pd.notna(lon) and _valid_campinas(lon, lat) and not _valid_campinas(lat, lon):
            data.at[idx, "latitude"] = lon
            data.at[idx, "longitude"] = lat
            swapped += 1
    valid = data["latitude"].notna() & data["longitude"].notna()
    valid &= data.apply(lambda row: _valid_campinas(row["latitude"], row["longitude"]), axis=1)
    invalid = len(data) - int(valid.sum())
    data = data.loc[valid].copy()
    data["sequencia_num"] = pd.to_numeric(data["sequencia"], errors="coerce")
    data = data.dropna(subset=["sequencia_num"])
    return data, {"inverted": swapped, "invalid": invalid}


def _distance_m(a, b):
    lat1, lon1 = map(float, a)
    lat2, lon2 = map(float, b)
    delta_lat, delta_lon = radians(lat2 - lat1), radians(lon2 - lon1)
    h = sin(delta_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(delta_lon / 2) ** 2
    return 2 * 6371000 * asin(min(1.0, sqrt(h)))


def filter_direction(edges, stops, line_to_direction):
    """Filtra paradas e arestas exatamente pelos mesmos (linha, sentido).

    Isso impede que o mapa e o cálculo de candidatos usem volta sem perceber.
    """
    if not line_to_direction:
        return edges.iloc[0:0].copy(), stops.iloc[0:0].copy()
    selected = {(str(line), str(direction)) for line, direction in line_to_direction.items() if direction is not None}
    edge_mask = [(_text(line), _text(direction)) in selected for line, direction in zip(edges.linha, edges.sentido)]
    stop_mask = [(_text(line), _text(direction)) in selected for line, direction in zip(stops.linha, stops.sentido)]
    return edges.loc[edge_mask].copy(), stops.loc[stop_mask].copy()


def _occurrences(stops):
    """Endereça cada parada pela ocorrência real (linha, sentido, sequência, ID).

    O mesmo ID pode existir mais de uma vez; não há deduplicação global de ID.
    Ocorrências duplicadas espacialmente conflitantes são ignoradas.
    """
    found = {}
    conflicting = set()
    for row in stops.itertuples(index=False):
        if pd.isna(row.sequencia_num):
            continue
        key = (_text(row.linha), _text(row.sentido), float(row.sequencia_num), _text(row.parada_id))
        pt = (float(row.latitude), float(row.longitude))
        if key in found and _distance_m(found[key], pt) > 30:
            conflicting.add(key)
        else:
            found.setdefault(key, pt)
    for key in conflicting:
        found.pop(key, None)
    return found, len(conflicting)


def _group_segments(segments):
    """Une exclusivamente arestas que compartilham a MESMA ocorrência final/inicial."""
    groups = []
    last_key = None
    for edge in segments:
        if groups and edge["a_key"] == last_key:
            groups[-1].append(edge["b"])
        else:
            groups.append([edge["a"], edge["b"]])
        last_key = edge["b_key"]
    return groups


def route_paths_from_local(edges, stops, line, direction):
    """Cria traços entre as coordenadas originais, por sentido e sequência.

    Não mistura sentidos, não une lacunas e não simula vias sem geometria oficial.
    """
    occurrences, conflicting = _occurrences(stops)
    selected = edges[(edges.linha.astype(str) == str(line)) & (edges.sentido.astype(str) == str(direction))].copy()
    if selected.empty:
        return [], {"missing_segments": 0, "conflicting_occurrences": conflicting}
    selected["sequence_num"] = pd.to_numeric(selected["sequencia"], errors="coerce")
    selected = selected.dropna(subset=["sequence_num"]).sort_values("sequence_num")
    segments = []
    missing = 0
    for row in selected.itertuples(index=False):
        # local_loader acrescenta estado_destino=(sentido, próxima sequência).
        following = getattr(row, "estado_destino", None)
        if not isinstance(following, (tuple, list)) or len(following) < 2:
            missing += 1
            continue
        a_key = (str(line), str(direction), float(row.sequence_num), _text(row.origem))
        b_key = (str(line), str(direction), float(following[1]), _text(row.destino))
        if a_key not in occurrences or b_key not in occurrences:
            missing += 1
            continue
        segments.append({"a_key": a_key, "b_key": b_key,
                         "a": occurrences[a_key], "b": occurrences[b_key]})
    # Preserva a ocorrência (linha, sentido, sequência, ID) em cada vértice.
    # O cálculo posterior atribui pesos a cada par consecutivo, e não apenas
    # à polilinha inteira. Não aproxima nem mescla duas ocorrências distintas.
    grouped = []
    for edge in segments:
        def as_stop(key, location):
            return {"key": key, "sequence": key[2], "stop_id": key[3],
                    "point": [float(location[0]), float(location[1])]}
        if grouped and grouped[-1]["last_key"] == edge["a_key"]:
            grouped[-1]["stops"].append(as_stop(edge["b_key"], edge["b"]))
            grouped[-1]["last_key"] = edge["b_key"]
        else:
            grouped.append({"stops": [as_stop(edge["a_key"], edge["a"]),
                                       as_stop(edge["b_key"], edge["b"])],
                            "last_key": edge["b_key"]})
    paths = []
    for idx, group in enumerate(grouped, start=1):
        route_stops = group["stops"]
        paths.append({"line": str(line), "direction": str(direction),
                      "group_id": f"{line}/{direction}/{idx}",
                      "points": [s["point"] for s in route_stops],
                      "stops": route_stops, "on_roads": False,
                      "source": "segmentos entre paradas oficiais"})
    return paths, {"missing_segments": missing, "conflicting_occurrences": conflicting}


def _min_path_distance(point, path):
    """Distância em metros até a *polilinha*, não apenas seus vértices.

    Uma parada pode estar no meio de uma rua longa; medir apenas vértices
    rejeitava geometria viária válida e provocava o fallback em linha reta.
    """
    if not path:
        return float("inf")
    lat0, lon0 = float(point[0]), float(point[1])
    scale_x = 111_320 * cos(radians(lat0))
    scale_y = 111_320
    px, py = lon0 * scale_x, lat0 * scale_y

    def xy(v):
        return float(v[1]) * scale_x, float(v[0]) * scale_y

    last_x, last_y = xy(path[0])
    best = ((last_x - px) ** 2 + (last_y - py) ** 2) ** 0.5
    for vertex in path[1:]:
        x, y = xy(vertex)
        vx, vy = x - last_x, y - last_y
        length2 = vx * vx + vy * vy
        fraction = max(0.0, min(1.0, ((px - last_x) * vx + (py - last_y) * vy) / length2)) if length2 else 0.0
        cx, cy = last_x + fraction * vx, last_y + fraction * vy
        best = min(best, ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5)
        last_x, last_y = x, y
    return best


def estimate_road_paths(paths, router=road_geometry, max_waypoints=20, snap_limit_m=120):
    """Desenha somente trechos validados pelo OSRM.

    Quando a consulta falha, preserva o segmento apenas como dado oculto;
    a camada de mapa não exibe linha reta no lugar de uma rua.
    """
    if max_waypoints < 2:
        raise ValueError("max_waypoints deve ser pelo menos 2")
    results = []
    rejected = 0
    for path in paths:
        points = path["points"]
        # Sobrepõe o ponto final da partição anterior com o ponto inicial
        # da seguinte, preservando a continuidade do percurso na ida.
        for i in range(0, len(points) - 1, max_waypoints - 1):
            part = points[i:i + max_waypoints]
            if len(part) < 2:
                continue
            coords = {str(j): p for j, p in enumerate(part)}
            try:
                geometry = router(list(coords), coords)
            except Exception:
                geometry = None
            try:
                validated = (isinstance(geometry, (list, tuple)) and len(geometry) >= 2
                             and all(_min_path_distance(pt, geometry) <= snap_limit_m for pt in part)
                             and _distance_m(part[0], geometry[0]) <= snap_limit_m
                             and _distance_m(part[-1], geometry[-1]) <= snap_limit_m)
            except (TypeError, ValueError, IndexError, OverflowError):
                validated = False
            if not validated:
                rejected += 1
            results.append({**path, "points": geometry if validated else part,
                            "on_roads": bool(validated),
                            "source": "OSRM: ruas estimadas" if validated else "sem geometria viária válida"})
    return results, rejected


def find_connections_ida(stops, line1, line2, max_distance_m=150):
    """Busca a proximidade entre OCORRÊNCIAS de paradas e não por ID global."""
    first = stops[stops.linha.astype(str) == str(line1)]
    second = stops[stops.linha.astype(str) == str(line2)]
    nearby = []
    for a in first.itertuples(index=False):
        for b in second.itertuples(index=False):
            point_a = [float(a.latitude), float(a.longitude)]
            point_b = [float(b.latitude), float(b.longitude)]
            dist = _distance_m(point_a, point_b)
            if dist <= max_distance_m:
                nearby.append({"stop1": str(a.parada_id), "stop2": str(b.parada_id),
                               "point1": point_a, "point2": point_b,
                               "seq1": str(a.sequencia), "seq2": str(b.sequencia),
                               "distance_m": round(dist)})
    return sorted(nearby, key=lambda x: (x["distance_m"], x["stop1"], x["stop2"]))


def build_ida_map(stops, line_to_direction, routes, connections=(), names=None, suggestions=None, show_schematic=False, proposed_routes=None, weighted_rows=None):
    """Mapa com paradas EMDEC e rotas nas ruas; sem atalhos retilíneos."""
    names = names or {}
    suggestions = suggestions or {}
    proposed_routes = proposed_routes or []
    weighted_rows = weighted_rows or []
    weighted_lookup = {}
    for item in weighted_rows:
        if item.get("Distância anterior (m)") is None:
            continue
        key = (str(item["Linha"]), str(item["Sequência EMDEC"]), str(item["Parada"]))
        weighted_lookup[key] = item
    map_obj = folium.Map(location=CENTER, zoom_start=12, tiles="OpenStreetMap", prefer_canvas=True)
    colors = {line: COLORS[i % len(COLORS)] for i, line in enumerate(line_to_direction)}
    plotted = []

    for line, direction in line_to_direction.items():
        if direction is None:
            continue
        color = colors[line]
        group = folium.FeatureGroup(name=f"Linha {line} — somente ida ({direction})", show=True).add_to(map_obj)
        for path in routes:
            if str(path["line"]) != str(line):
                continue
            # Nunca representa linhas retas como trajeto viário real.
            if not path["on_roads"] and not show_schematic:
                continue
            if path["on_roads"] and path.get("segments"):
                # Cada aresta tem seu peso (metros por ruas), exibido no hover.
                for segment in path["segments"]:
                    origin = segment["from_stop"]; dest = segment["to_stop"]
                    weight_m = segment["weight_m"]
                    route_line = folium.PolyLine(
                        segment["geometry"], color=color, weight=4, opacity=0.82,
                        tooltip=(f"Linha {escape(str(line))} · "
                                 f"{escape(str(origin['stop_id']))} → "
                                 f"{escape(str(dest['stop_id']))}: {weight_m:.1f} m pelas ruas"),
                    ).add_to(group)
                    _add_direction_arrow(segment["geometry"], group, color)
            else:
                route_line = folium.PolyLine(
                    path["points"], color=color, weight=4, opacity=0.82,
                    dash_array=None if path["on_roads"] else "3, 9",
                    tooltip=f"Linha {escape(str(line))} · {'via estimada pelo OSRM' if path['on_roads'] else 'REFERÊNCIA RETA, não é rota'}",
                ).add_to(group)
                if path["on_roads"]:
                    _add_direction_arrow(path["points"], group, color)
        line_stops = stops[(stops.linha.astype(str) == str(line)) &
                           (stops.sentido.astype(str) == str(direction))].sort_values("sequencia_num")
        for row in line_stops.itertuples(index=False):
            position = [float(row.latitude), float(row.longitude)]
            plotted.append(position)
            # O endereço é o da OCORRÊNCIA selecionada; um mesmo ID pode aparecer
            # em diferentes linhas e não deve herdar o nome de outra linha.
            raw_address = " ".join(v for v in [str(getattr(row, "logradouro", "")).strip(),
                                                str(getattr(row, "numero", "")).strip()] if v)
            address = escape(raw_address or "Parada sem endereço")
            status = escape(str(getattr(row, "status", "Não informado")))
            usage = escape(str(getattr(row, "tipo_uso", "Não informado")))
            lookup_key = (str(line), str(float(row.sequencia_num)), str(row.parada_id))
            weight_row = weighted_lookup.get(lookup_key)
            weight_popup = ""
            if weight_row:
                weight_popup = (f"<br><b>Distância anterior:</b> {weight_row['Distância anterior (m)']:.1f} m"
                                f"<br><b>Acumulado do trecho:</b> {weight_row['Acumulado (m)']:.1f} m")
            folium.CircleMarker(
                location=position, radius=4, color="#ffffff", weight=1.2,
                fill=True, fill_color=color, fill_opacity=0.96,
                tooltip=f"Linha {escape(str(line))} | Parada {escape(str(row.sequencia))}",
                popup=(f"<b>Linha {escape(str(line))} — ida</b><br>"
                       f"Sequência: {escape(str(row.sequencia))}<br>"
                       f"Parada ID: {escape(str(row.parada_id))}<br>{address}<br>"
                       f"Situação informada: {status}<br>Uso: {usage}"
                       f"{weight_popup}<br>"
                       f"Coordenadas EMDEC: {row.latitude:.6f}, {row.longitude:.6f}")
            ).add_to(group)

    if connections:
        connection_group = folium.FeatureGroup(
            name="Conexões entre paradas da ida", show=True
        ).add_to(map_obj)
        for i, item in enumerate(connections, 1):
            a, b = item["point1"], item["point2"]
            mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]
            folium.CircleMarker(mid, radius=6, color="#d97706", fill=True, fill_color="#fbbf24",
                                fill_opacity=0.95, tooltip=f"Conexão {i}: {item['distance_m']} m",
                                popup=(f"Conexão candidata, {item['distance_m']} m em linha reta<br>"
                                       f"Paradas {escape(item['stop1'])} ↔ {escape(item['stop2'])}")).add_to(connection_group)
            folium.PolyLine([a, b], color="#d97706", weight=2, opacity=0.65,
                            dash_array="3, 6").add_to(connection_group)

    for line, candidates in suggestions.items():
        group = folium.FeatureGroup(name=f"Possíveis pontos — linha {line}", show=True).add_to(map_obj)
        for item in candidates:
            pt = item["point"]
            color = colors.get(line, COLORS[0])
            folium.Circle(pt, radius=120, color=color, weight=2, fill=True,
                          fill_color=color, fill_opacity=0.10,
                          tooltip="Área de estudo (não é ponto validado)").add_to(group)
            folium.CircleMarker(pt, radius=6, color="white", weight=1, fill=True, fill_color=color,
                                fill_opacity=0.95,
                                popup=f"Sugestão geométrica para linha {escape(str(line))}; requer validação em campo").add_to(group)

    # A rota sugerida segue a MESMA geometria viária validada.
    # A novidade é a distribuição/implantação de paradas em intervalos de 300m.
    suggested_layers = {}
    for proposed in proposed_routes:
        line = str(proposed["line"])
        if line not in suggested_layers:
            suggested_layers[line] = folium.FeatureGroup(
                name=f"Rota sugerida + pontos a cada 300m — linha {line}", show=False).add_to(map_obj)
        layer = suggested_layers[line]
        folium.PolyLine(proposed["geometry"], color="#7c3aed", weight=6, opacity=0.58,
                        dash_array="10, 7",
                        tooltip=f"Proposta da linha {escape(line)}: novos pontos a cada ~300m de rua").add_to(layer)
        for point in proposed["points"]:
            kind = point["kind"]
            if kind == "Novo ponto sugerido":
                fill = "#7c3aed"
                radius = 6
            elif kind == "Existente próxima":
                fill = "#059669"
                radius = 5
            else:
                fill = "#334155"
                radius = 5
            near = (f"<br>Parada EMDEC próxima: {escape(str(point['near_stop_id']))}"
                    if point.get("near_stop_id") else "")
            folium.CircleMarker(
                location=point["point"], radius=radius, color="#ffffff", weight=1.2,
                fill=True, fill_color=fill, fill_opacity=0.98,
                tooltip=(f"{escape(kind)} · {point['distance_m']:.0f} m desde o início "
                         "da seção viária"),
                popup=(f"<b>Proposta — linha {escape(line)}</b><br>"
                       f"{escape(kind)}<br>Distância da origem desta seção: {point['distance_m']:.1f} m"
                       f"<br>Intervalo anterior: {point['gap_m']:.1f} m{near}"
                       "<br><i>Ponto conceitual: validar calçada, segurança e operação em campo.</i>")
            ).add_to(layer)

    if plotted:
        map_obj.fit_bounds(plotted, max_zoom=16)
    folium.LayerControl(collapsed=False).add_to(map_obj)
    return map_obj

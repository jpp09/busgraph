"""BusGraph Campinas — rotas de ida e pesos de distância viária."""

import pandas as pd
import streamlit as st

from data.local_loader import load_local_dataset, load_map_stops
from services.ida_view import (
    build_ida_map,
    choose_ida,
    clean_stop_coordinates,
    filter_direction,
    route_paths_from_local,
)
from services.weighted_routes import (
    build_distance_graph,
    build_weighted_road_paths,
    distance_table,
    suggest_route_300m,
)

st.set_page_config(page_title="BusGraph Campinas", page_icon="🚌", layout="wide")
st.title("🚌 BusGraph — distâncias reais e rota sugerida")
st.caption("EMDEC municipal · somente ida · peso das arestas = metros percorridos pelas ruas (OSRM)")


@st.cache_data
def load_data():
    edges, names, _ = load_local_dataset()
    valid_stops, report = clean_stop_coordinates(load_map_stops())
    return edges, valid_stops, names, report


@st.cache_data(ttl=86400, show_spinner=False)
def weighted_roads_cached(paths):
    return build_weighted_road_paths(paths)


try:
    edges, stops, names, coordinate_report = load_data()
except (OSError, KeyError, ValueError) as exc:
    st.error(f"Erro ao carregar a base EMDEC local: {exc}")
    st.stop()

if coordinate_report["inverted"]:
    st.warning(f"{coordinate_report['inverted']} coordenadas invertidas foram corrigidas em memória.")
if coordinate_report["invalid"]:
    st.warning(f"{coordinate_report['invalid']} ocorrências com coordenadas inválidas foram ocultadas.")

lines = sorted(set(edges.linha.astype(str)), key=lambda v: (not v.isdigit(), int(v) if v.isdigit() else v))
col1, col2 = st.columns(2)
with col1:
    line1 = st.selectbox("Linha 1", lines, index=None, placeholder="Selecione a primeira linha")
with col2:
    line2 = st.selectbox("Linha 2", lines, index=None, placeholder="Selecione a segunda linha")

if not line1 or not line2:
    st.info("Selecione duas linhas para calcular as distâncias entre paradas na ida.")
    empty = build_ida_map(stops.iloc[:0], {}, [])
    st.components.v1.html(empty.get_root().render(), height=610)
    st.stop()
if line1 == line2:
    st.warning("Selecione duas linhas diferentes.")
    st.stop()

selected_directions = {}
for line in (line1, line2):
    directions = sorted(set(edges.loc[edges.linha.astype(str) == line, "sentido"].astype(str)))
    detected, _, note = choose_ida(directions)
    if detected is None:
        st.error(f"Linha {line}: {note}")
        st.stop()
    selected_directions[line] = detected

filtered_edges, filtered_stops = filter_direction(edges, stops, selected_directions)
if filtered_edges.empty or filtered_stops.empty:
    st.error("As linhas selecionadas não possuem trechos de ida com coordenadas válidas.")
    st.stop()

raw_routes, quality = [], {}
for line, direction in selected_directions.items():
    paths, diagnostics = route_paths_from_local(filtered_edges, filtered_stops, line, direction)
    raw_routes.extend(paths)
    quality[line] = diagnostics

with st.spinner("Calculando pesos por cada par de paradas pelas ruas (OSRM)..."):
    routed, rejected = weighted_roads_cached(raw_routes) if raw_routes else ([], 0)

if rejected:
    st.warning(f"{rejected} blocos não tiveram retorno viário válido. Seus pesos ficaram indefinidos "
               "e não foram ligados em linha reta.")
if not any(path["on_roads"] for path in routed):
    st.error("Nenhum trecho pôde ser calculado pelo OSRM. "
             "Verifique a internet; não é possível determinar pesos viários reais offline com esta fonte.")

weights = distance_table(routed)
weighted_graph = build_distance_graph(routed)
proposals = suggest_route_300m(routed, spacing_m=300)

number_segments = sum(len(p["segments"]) for p in routed if p["on_roads"])
total_road_m = sum(p["distance_m"] or 0 for p in routed)
new_stop_count = sum(p["new_stop_count"] for p in proposals)
metric1, metric2, metric3 = st.columns(3)
metric1.metric("Arestas ponderadas", number_segments)
metric2.metric("Distância viária validada", f"{total_road_m / 1000:.2f} km")
metric3.metric("Novos pontos sugeridos", new_stop_count)

for line, diagnostics in quality.items():
    if diagnostics["missing_segments"] or diagnostics["conflicting_occurrences"]:
        st.warning(f"Linha {line}: {diagnostics['missing_segments']} trechos sem coordenadas "
                   f"e {diagnostics['conflicting_occurrences']} ocorrências conflitantes não foram roteados.")

st.subheader("Mapa — trajetos, pesos e nova distribuição de paradas")
map_obj = build_ida_map(filtered_stops, selected_directions, routed, names=names,
                        proposed_routes=proposals, weighted_rows=weights)
st.components.v1.html(map_obj.get_root().render(), height=710)
st.caption("Linhas azul/vermelha: geometria OSRM sobre ruas; as setas indicam o sentido do fluxo. "
           "Passe o mouse em cada trecho para ver o peso "
           "em metros. Camada roxa tracejada: proposta de distribuição de paradas a cada ~300m; "
           "roxo = novo ponto, verde = parada existente próxima. "
           "O OSRM não garante o itinerário oficial do ônibus, e pontos propostos exigem vistoria de campo.")

st.subheader("Pesos do grafo — cada aresta é a distância entre duas paradas")
st.write("O vértice **P0 começa com 0 m**. Cada próximo ponto recebe o peso da aresta anterior "
         "e seu acumulado. As distâncias são medidas ao longo das ruas, não em linha reta.")
if weights:
    for line in (line1, line2):
        relevant = [item for item in weights if item["Linha"] == line]
        if not relevant:
            continue
        with st.expander(f"Linha {line} — pesos entre paradas", expanded=True):
            st.dataframe(pd.DataFrame(relevant), hide_index=True, use_container_width=True)
    st.download_button("Baixar pesos das arestas (CSV)",
                       pd.DataFrame(weights).to_csv(index=False).encode("utf-8-sig"),
                       file_name="busgraph_pesos_distancia_ida.csv", mime="text/csv")
else:
    st.info("Nenhum peso viário disponível para mostrar.")

st.subheader("Nova rota sugerida — proposta de pontos a cada 300 m")
st.write("A proposta mantém as ruas calculadas pelo OSRM e cria um **novo plano de paradas**: "
         "marcos a 0, 300, 600, 900 m etc. Se já existir uma parada EMDEC a até 70 m "
         "*ao longo do percurso*, ela é aproveitada; caso contrário, o marco é um novo ponto sugerido.")
proposed_rows = []
for route in proposals:
    for proposal in route["points"]:
        proposed_rows.append({"Linha": route["line"], "Seção": route["group_id"],
                              "Fragmento": route["fragment"], "Ponto": proposal["index"],
                              "Metros desde início": proposal["distance_m"],
                              "Metros do anterior": proposal["gap_m"],
                              "Classificação": proposal["kind"],
                              "Parada existente": proposal["near_stop_id"],
                              "Latitude": round(proposal["point"][0], 7),
                              "Longitude": round(proposal["point"][1], 7)})
if proposed_rows:
    st.dataframe(pd.DataFrame(proposed_rows), hide_index=True, use_container_width=True)
    st.download_button("Baixar rota sugerida (CSV)",
                       pd.DataFrame(proposed_rows).to_csv(index=False).encode("utf-8-sig"),
                       file_name="busgraph_rota_sugerida_300m.csv", mime="text/csv")
else:
    st.info("Não foi possível gerar uma rota sugerida sem trechos viários validados.")

st.caption(f"Grafo direcionado: {len(weighted_graph)} vértices. Peso = metros de cada aresta de ida. "
           "Blocos sem dados válidos não entram no grafo. A proposta altera a distribuição dos pontos, "
           "não cria um novo itinerário de ruas ou uma rota oficial.")

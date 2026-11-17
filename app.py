"""Explora possíveis pontos de conexão entre duas linhas da base EMDEC."""
import streamlit as st

from data.local_loader import load_local_dataset
from services.connection_finder import find_connections, find_new_stop_candidates
from services.map_view import build_connection_map, load_map_stops, stop_coordinates
from services.road_router import trace_line

st.set_page_config(page_title="BusGraph Campinas", page_icon="🚌", layout="wide")
st.title("🚌 Conexões entre linhas de Campinas")
st.caption("Compare duas linhas para encontrar paradas próximas onde uma conexão pode ser possível.")


@st.cache_data
def load_data():
    edges, names, _ = load_local_dataset()
    stops = load_map_stops()
    return edges, stops, names


@st.cache_data(ttl=86400, show_spinner=False)
def trace_line_cached(line):
    route_edges, _, _ = load_local_dataset()
    route_stops = load_map_stops()
    return trace_line(route_edges, stop_coordinates(route_stops), line)


try:
    edges, stops, names = load_data()
except (OSError, ValueError, KeyError) as exc:
    st.error(f"Não foi possível carregar a base local: {exc}")
    st.stop()

lines = sorted(set(edges.linha), key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value))
c1, c2 = st.columns(2)
with c1:
    line1 = st.selectbox("Linha 1", lines, index=None, placeholder="Selecione a primeira linha")
with c2:
    line2 = st.selectbox("Linha 2", lines, index=None, placeholder="Selecione a segunda linha")

f1, f2 = st.columns(2)
with f1:
    show_new_line1 = st.checkbox("Mostrar novos pontos na Linha 1", value=True,
                                 disabled=not (line1 and line2 and line1 != line2))
with f2:
    show_new_line2 = st.checkbox("Mostrar novos pontos na Linha 2", value=True,
                                 disabled=not (line1 and line2 and line1 != line2))

connections = []
if line1 and line2:
    if line1 == line2:
        st.info("Escolha duas linhas diferentes para comparar.")
    else:
        connections = find_connections(stops, line1, line2)
        with st.spinner("Ajustando as linhas às ruas..."):
            paths1, fallback1 = trace_line_cached(line1)
            paths2, fallback2 = trace_line_cached(line2)
        road_paths = paths1 + paths2
        new_line1 = find_new_stop_candidates(stops, road_paths, line1, line2) if show_new_line1 else []
        new_line2 = find_new_stop_candidates(stops, road_paths, line2, line1) if show_new_line2 else []
        if connections:
            st.write(f"**{len(connections)} pares de paradas próximos** (até 150 m em linha reta). "
                     "Pontos laranja indicam possíveis conexões; clique para ver os IDs das paradas.")
            with st.expander("Ver pontos encontrados"):
                st.dataframe([{"Parada linha 1": names.get(item["stop1"], item["stop1"]),
                               "Parada linha 2": names.get(item["stop2"], item["stop2"]),
                               "Distância em linha reta (m)": item["distance_m"]}
                              for item in connections], hide_index=True)
        else:
            st.info("Não encontramos paradas dessas duas linhas a até 150 m uma da outra.")
        if fallback1 + fallback2:
            st.caption(f"{fallback1 + fallback2} parte(s) sem resposta do serviço aparecem pontilhadas.")
        if show_new_line1 or show_new_line2:
            st.write(f"**Sugestões de novos pontos:** Linha {line1}: {len(new_line1)} · "
                     f"Linha {line2}: {len(new_line2)}")
        map_obj = build_connection_map(stops, edges, line1, line2, connections, names,
                                       road_paths=road_paths, new_stops_line1=new_line1,
                                       new_stops_line2=new_line2)
        st.iframe(map_obj.get_root().render(), height=650)
else:
    st.iframe(build_connection_map(stops.iloc[:0], edges.iloc[:0], "", "", [], names).get_root().render(),
              height=650)

st.caption("Conexões candidatas baseadas apenas na proximidade. A distância a pé, acessibilidade, sentido de viagem e horários ainda precisam ser validados. Os trajetos pelas ruas são estimados pelo OSRM e podem diferir do itinerário oficial; o mapa requer internet.")

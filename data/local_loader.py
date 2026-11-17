"""Carga da topologia EMDEC sem atribuir tempos fictícios aos trechos."""
from pathlib import Path
import json

import pandas as pd

DEFAULT_DATASET = Path(__file__).resolve().parents[1] / "datasets" / "emdec" / "consolidado"


def load_local_dataset(directory=DEFAULT_DATASET):
    directory = Path(directory)
    stops = pd.read_csv(directory / "paradas.csv", dtype=str, keep_default_na=False)
    edges = pd.read_csv(directory / "trechos.csv", dtype=str, keep_default_na=False)
    if edges.empty:
        raise ValueError("A base local não contém trechos.")
    # Cada ocorrência é um estado distinto: não unir sentidos, visitas repetidas
    # ou sequências interrompidas apenas porque usam a mesma parada e linha.
    occurrences = {}
    names = {}
    for row in stops.to_dict("records"):
        key = (row["linha"], row["sentido"], float(row["sequencia"]))
        occurrences.setdefault(key, []).append(row["parada_id"])
        address = " ".join(filter(None, [row["logradouro"], row["numero"]]))
        names.setdefault(row["parada_id"], f"{address or 'Parada'} [ID {row['parada_id']}]")
    sequences_by_route = {}
    for line, direction, sequence in occurrences:
        sequences_by_route.setdefault((line, direction), []).append(sequence)
    successors = {}
    for (line, direction), sequences in sequences_by_route.items():
        ordered = sorted(sequences)
        for current, following in zip(ordered, ordered[1:]):
            successors[(line, direction, current)] = following
    states_from, states_to = [], []
    for row in edges.to_dict("records"):
        line, direction = row["linha"], row["sentido"]
        sequence = float(row["sequencia"])
        next_sequence = successors.get((line, direction, sequence))
        if (occurrences.get((line, direction, sequence)) != [row["origem"]]
                or occurrences.get((line, direction, next_sequence)) != [row["destino"]]
                or next_sequence - sequence > 1):
            raise ValueError("Trecho local incompatível com a sequência de paradas.")
        states_from.append((direction, sequence))
        states_to.append((direction, next_sequence))
    edges["estado_origem"] = states_from
    edges["estado_destino"] = states_to
    edges["custo_trecho"] = 1.0
    report = json.loads((directory / "relatorio.json").read_text(encoding="utf-8"))
    return edges, names, report

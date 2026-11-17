import pandas as pd

def _read_gtfs(zip_file, filename, required=True):
    try:
        return pd.read_csv(zip_file, compression="zip", encoding="utf-8-sig", dtype=str, usecols=None) if filename == "__all__" else pd.read_csv(
            zip_file, compression="zip", encoding="utf-8-sig", dtype=str, usecols=None
        )
    except Exception:
        raise ValueError("Não foi possível ler o ZIP GTFS. Confira se os arquivos TXT estão na raiz ou em uma única pasta.")

def _read_member(zf, filename, required=True):
    import io
    matches = [n for n in zf.namelist() if n.lower().endswith("/" + filename.lower()) or n.lower() == filename.lower()]
    if not matches:
        if required:
            raise ValueError(f"Arquivo obrigatório ausente no GTFS: {filename}")
        return None
    return pd.read_csv(io.BytesIO(zf.read(matches[0])), dtype=str)

def load_gtfs(uploaded_zip):
    import zipfile
    import io
    try:
        zf = zipfile.ZipFile(uploaded_zip)
    except Exception as exc:
        raise ValueError("Arquivo ZIP inválido.") from exc

    stops = _read_member(zf, "stops.txt")
    routes = _read_member(zf, "routes.txt")
    trips = _read_member(zf, "trips.txt")
    stop_times = _read_member(zf, "stop_times.txt")

    for df, cols, label in [
        (stops, ["stop_id", "stop_name"], "stops.txt"),
        (routes, ["route_id"], "routes.txt"),
        (trips, ["trip_id", "route_id"], "trips.txt"),
        (stop_times, ["trip_id", "stop_id", "stop_sequence", "arrival_time", "departure_time"], "stop_times.txt")
    ]:
        missing = set(cols) - set(df.columns)
        if missing:
            raise ValueError(f"{label}: colunas ausentes: {', '.join(sorted(missing))}")

    route_names = {}
    if "route_short_name" in routes.columns:
        route_names = dict(zip(routes["route_id"], routes["route_short_name"]))
    if "route_long_name" in routes.columns:
        for rid, name in zip(routes["route_id"], routes["route_long_name"]):
            route_names.setdefault(rid, name)
    route_names = {k: (v if pd.notna(v) and str(v).strip() else k) for k, v in route_names.items()}

    trip_routes = dict(zip(trips["trip_id"], trips["route_id"]))
    stop_times = stop_times.copy()
    stop_times["stop_sequence_num"] = pd.to_numeric(stop_times["stop_sequence"], errors="coerce")
    stop_times = stop_times.dropna(subset=["stop_sequence_num"])
    stop_times = stop_times.sort_values(["trip_id", "stop_sequence_num"])

    def seconds(value):
        try:
            h, m, s = str(value).split(":")
            return int(h) * 3600 + int(m) * 60 + int(s)
        except Exception:
            return None

    segment_samples = {}
    for trip_id, group in stop_times.groupby("trip_id"):
        route_id = trip_routes.get(trip_id)
        if route_id is None:
            continue
        rows = list(group.to_dict("records"))
        for a, b in zip(rows, rows[1:]):
            dep = seconds(a.get("departure_time"))
            arr = seconds(b.get("arrival_time"))
            if dep is None or arr is None:
                continue
            duration = (arr - dep) / 60
            if duration < 0:
                duration += 24 * 60
            if duration <= 0 or duration > 240:
                continue
            key = (a["stop_id"], b["stop_id"], route_id)
            segment_samples.setdefault(key, []).append(duration)

    records = [{
        "origem": a, "destino": b, "linha": route_names.get(rid, rid),
        "duracao_min": sum(vals) / len(vals)
    } for (a, b, rid), vals in segment_samples.items()]

    if not records:
        raise ValueError("Não foram encontrados trechos válidos entre paradas consecutivas.")
    return stops, pd.DataFrame(records)

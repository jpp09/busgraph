from io import BytesIO
import requests

# Primeiro tenta o endpoint da aplicação original; se falhar, usa o ZIP do GitHub.
FEED_URLS = [
    ("endpoint Emdec-GTFS", "https://emdec.paulo.costa.nom.br/route/all.gtfs"),
    ("repositório GitHub", "https://github.com/paulo-raca/emdec-gtfs/archive/refs/heads/master.zip"),
]

def download_emdec_gtfs(timeout=45):
    errors = []
    for source_name, url in FEED_URLS:
        try:
            response = requests.get(
                url, timeout=timeout, allow_redirects=True,
                headers={"User-Agent": "BusGraph-Academic-Prototype/1.0"}
            )
            response.raise_for_status()
            content = response.content
            if not content.startswith(b"PK"):
                raise ValueError("A resposta recebida não é um arquivo ZIP.")
            # Verifica se o ZIP contém os arquivos básicos do GTFS.
            import zipfile
            from io import BytesIO as _BytesIO
            with zipfile.ZipFile(_BytesIO(content)) as zf:
                names = [n.lower() for n in zf.namelist()]
                required = ["stops.txt", "routes.txt", "trips.txt", "stop_times.txt"]
                missing = [f for f in required if not any(n.endswith("/" + f) or n == f for n in names)]
                if missing:
                    raise ValueError("ZIP sem arquivos GTFS necessários: " + ", ".join(missing))
            result = BytesIO(content)
            result.source_name = source_name
            return result
        except Exception as exc:
            errors.append(f"{source_name}: {exc}")
    raise RuntimeError(
        "Não foi possível obter o GTFS por nenhuma fonte. " + " | ".join(errors) +
        ". Use o upload manual ou tente novamente mais tarde."
    )

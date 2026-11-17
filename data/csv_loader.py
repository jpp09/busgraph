import pandas as pd

REQUIRED = {"origem", "destino", "linha", "duracao_min"}

def load_csv(file_obj):
    df = pd.read_csv(file_obj)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError("Colunas ausentes no CSV: " + ", ".join(sorted(missing)))
    df = df.dropna(subset=list(REQUIRED))
    df["duracao_min"] = pd.to_numeric(df["duracao_min"], errors="coerce")
    df = df.dropna(subset=["duracao_min"])
    if (df["duracao_min"] < 0).any():
        raise ValueError("A duração não pode ser negativa.")
    if df.empty:
        raise ValueError("O CSV não contém conexões válidas.")
    return df

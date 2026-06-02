from __future__ import annotations

import pandas as pd

from src.carregar_dados import COLUNAS_DEZENAS


def frequencia_dezenas(df: pd.DataFrame) -> pd.DataFrame:
    dezenas = df[COLUNAS_DEZENAS].to_numpy().ravel()
    frequencia = pd.Series(dezenas).value_counts().reindex(range(1, 61), fill_value=0)
    resultado = frequencia.rename_axis("Dezena").reset_index(name="Frequência")
    resultado["Dezena"] = resultado["Dezena"].astype(int)
    resultado["Dezena formatada"] = resultado["Dezena"].map(lambda valor: f"{valor:02d}")
    return resultado


def dezenas_mais_sorteadas(df: pd.DataFrame, limite: int = 10) -> pd.DataFrame:
    return frequencia_dezenas(df).sort_values(
        ["Frequência", "Dezena"],
        ascending=[False, True],
    ).head(limite)


def dezenas_menos_sorteadas(df: pd.DataFrame, limite: int = 10) -> pd.DataFrame:
    return frequencia_dezenas(df).sort_values(
        ["Frequência", "Dezena"],
        ascending=[True, True],
    ).head(limite)


def resumo_base(df: pd.DataFrame) -> dict[str, int]:
    concursos = df["Concurso"].astype(int)
    return {
        "total_concursos": int(len(df)),
        "primeiro_concurso": int(concursos.min()),
        "ultimo_concurso": int(concursos.max()),
    }

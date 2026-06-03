from __future__ import annotations

from collections import Counter
from itertools import combinations

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


def pares_mais_frequentes(df: pd.DataFrame, limite: int = 20) -> pd.DataFrame:
    contador: Counter[tuple[int, int]] = Counter()
    for linha in df[COLUNAS_DEZENAS].to_numpy():
        dezenas = sorted(int(dezena) for dezena in linha)
        contador.update(combinations(dezenas, 2))

    registros = [
        {
            "Par": f"{par[0]:02d} - {par[1]:02d}",
            "Dezena 1": par[0],
            "Dezena 2": par[1],
            "Frequência": frequencia,
        }
        for par, frequencia in contador.most_common(limite)
    ]
    return pd.DataFrame(registros, columns=["Par", "Dezena 1", "Dezena 2", "Frequência"])


def trincas_mais_frequentes(df: pd.DataFrame, limite: int = 20) -> pd.DataFrame:
    contador: Counter[tuple[int, int, int]] = Counter()
    for linha in df[COLUNAS_DEZENAS].to_numpy():
        dezenas = sorted(int(dezena) for dezena in linha)
        contador.update(combinations(dezenas, 3))

    registros = [
        {
            "Trinca": f"{trinca[0]:02d} - {trinca[1]:02d} - {trinca[2]:02d}",
            "Dezena 1": trinca[0],
            "Dezena 2": trinca[1],
            "Dezena 3": trinca[2],
            "Frequência": frequencia,
        }
        for trinca, frequencia in contador.most_common(limite)
    ]
    return pd.DataFrame(registros, columns=["Trinca", "Dezena 1", "Dezena 2", "Dezena 3", "Frequência"])


def mapa_correlacao_dezenas(df: pd.DataFrame) -> pd.DataFrame:
    contador: Counter[tuple[int, int]] = Counter()
    for linha in df[COLUNAS_DEZENAS].to_numpy():
        dezenas = sorted(int(dezena) for dezena in linha)
        contador.update(combinations(dezenas, 2))

    registros = [
        {
            "Dezena A": dezena_a,
            "Dezena B": dezena_b,
            "Frequência conjunta": int(frequencia),
        }
        for (dezena_a, dezena_b), frequencia in sorted(contador.items())
    ]
    return pd.DataFrame(registros, columns=["Dezena A", "Dezena B", "Frequência conjunta"])


def ultimos_concursos(df: pd.DataFrame, quantidade: int) -> pd.DataFrame:
    return df.sort_values("Concurso", ascending=False).head(quantidade)


def dezenas_mais_sorteadas_ultimos_concursos(
    df: pd.DataFrame,
    quantidade_concursos: int,
    limite: int = 10,
) -> pd.DataFrame:
    return dezenas_mais_sorteadas(ultimos_concursos(df, quantidade_concursos), limite=limite)


def dezenas_menos_sorteadas_ultimos_concursos(
    df: pd.DataFrame,
    quantidade_concursos: int,
    limite: int = 10,
) -> pd.DataFrame:
    return dezenas_menos_sorteadas(ultimos_concursos(df, quantidade_concursos), limite=limite)


def dezenas_atrasadas(df: pd.DataFrame) -> pd.DataFrame:
    ultimo_concurso = int(df["Concurso"].astype(int).max())
    registros = []

    for dezena in range(1, 61):
        apareceu = df[COLUNAS_DEZENAS].eq(dezena).any(axis=1)
        concursos = df.loc[apareceu, "Concurso"].astype(int)
        ultimo_aparecimento = int(concursos.max()) if not concursos.empty else None
        atraso = ultimo_concurso - ultimo_aparecimento if ultimo_aparecimento else len(df)
        registros.append(
            {
                "Dezena": dezena,
                "Dezena formatada": f"{dezena:02d}",
                "Último concurso": ultimo_aparecimento or "-",
                "Atraso": int(atraso),
            }
        )

    return pd.DataFrame(registros).sort_values(
        ["Atraso", "Dezena"],
        ascending=[False, True],
    ).reset_index(drop=True)


def estatistica_pares_impares(df: pd.DataFrame) -> pd.DataFrame:
    dados = df[["Concurso", "Data", *COLUNAS_DEZENAS]].copy()
    dados["Pares"] = dados[COLUNAS_DEZENAS].apply(
        lambda linha: int(sum(int(dezena) % 2 == 0 for dezena in linha)),
        axis=1,
    )
    dados["Ímpares"] = 6 - dados["Pares"]
    return dados[["Concurso", "Data", "Pares", "Ímpares"]].sort_values(
        "Concurso",
        ascending=False,
    ).reset_index(drop=True)


def estatistica_soma_dezenas(df: pd.DataFrame) -> dict[str, float | int | pd.DataFrame]:
    somas = df[COLUNAS_DEZENAS].sum(axis=1)
    por_concurso = df[["Concurso", "Data"]].copy()
    por_concurso["Soma"] = somas.astype(int)
    por_concurso = por_concurso.sort_values("Concurso", ascending=False).reset_index(drop=True)

    return {
        "média": float(somas.mean()),
        "mínima": int(somas.min()),
        "máxima": int(somas.max()),
        "por_concurso": por_concurso,
    }


def padrao_jogo(df: pd.DataFrame) -> dict[str, object]:
    pares_impares = estatistica_pares_impares(df)
    soma = estatistica_soma_dezenas(df)

    return {
        "média da soma": soma["média"],
        "média de pares": float(pares_impares["Pares"].mean()),
        "média de ímpares": float(pares_impares["Ímpares"].mean()),
        "dezenas mais frequentes": dezenas_mais_sorteadas(df, limite=10),
        "dezenas menos frequentes": dezenas_menos_sorteadas(df, limite=10),
        "dezenas mais atrasadas": dezenas_atrasadas(df).head(10),
    }


def resumo_base(df: pd.DataFrame) -> dict[str, int]:
    concursos = df["Concurso"].astype(int)
    return {
        "total_concursos": int(len(df)),
        "primeiro_concurso": int(concursos.min()),
        "ultimo_concurso": int(concursos.max()),
    }

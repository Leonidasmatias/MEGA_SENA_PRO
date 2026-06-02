from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import pandas as pd


CAMINHO_BASE_PADRAO = Path("dados") / "mega_sena_historico.csv"
COLUNAS_OBRIGATORIAS = ["Concurso", "Data", "D1", "D2", "D3", "D4", "D5", "D6"]
COLUNAS_DEZENAS = ["D1", "D2", "D3", "D4", "D5", "D6"]


def validar_base(df: pd.DataFrame) -> pd.DataFrame:
    dados = df.copy()
    dados.columns = [str(coluna).strip() for coluna in dados.columns]

    faltantes = [coluna for coluna in COLUNAS_OBRIGATORIAS if coluna not in dados.columns]
    if faltantes:
        raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(faltantes)}")

    dados = dados[COLUNAS_OBRIGATORIAS].copy()
    dados["Concurso"] = pd.to_numeric(dados["Concurso"], errors="coerce")
    dados["Data"] = pd.to_datetime(dados["Data"], errors="coerce", dayfirst=True)

    for coluna in COLUNAS_DEZENAS:
        dados[coluna] = pd.to_numeric(dados[coluna], errors="coerce")

    dados = dados.dropna(subset=COLUNAS_OBRIGATORIAS).copy()
    dados["Concurso"] = dados["Concurso"].astype(int)
    for coluna in COLUNAS_DEZENAS:
        dados[coluna] = dados[coluna].astype(int)

    fora_intervalo = ~dados[COLUNAS_DEZENAS].apply(
        lambda linha: linha.between(1, 60).all(),
        axis=1,
    )
    if fora_intervalo.any():
        raise ValueError("A base contém dezenas fora do intervalo de 1 a 60.")

    repetidas = dados[COLUNAS_DEZENAS].apply(lambda linha: len(set(linha)) != 6, axis=1)
    if repetidas.any():
        raise ValueError("A base contém concursos com dezenas repetidas.")

    dados = dados.drop_duplicates("Concurso", keep="last")
    dados = dados.sort_values("Concurso", ascending=False).reset_index(drop=True)
    dados["Data"] = dados["Data"].dt.strftime("%d/%m/%Y")
    return dados


def carregar_base(caminho: str | Path = CAMINHO_BASE_PADRAO) -> pd.DataFrame:
    arquivo = Path(caminho)
    if not arquivo.exists():
        raise FileNotFoundError(str(arquivo))

    return validar_base(pd.read_csv(arquivo, dtype=str))


def carregar_upload(arquivo: BinaryIO) -> pd.DataFrame:
    return validar_base(pd.read_csv(arquivo, dtype=str))

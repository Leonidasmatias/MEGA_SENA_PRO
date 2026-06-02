from __future__ import annotations

import random

import pandas as pd

from src.estatisticas import frequencia_dezenas


def gerar_jogo(df: pd.DataFrame, quantidade: int = 6) -> list[int]:
    if quantidade != 6:
        raise ValueError("Este gerador cria jogos com exatamente 6 dezenas.")

    frequencia = frequencia_dezenas(df)
    pesos = (frequencia["Frequência"] + 1).astype(float).tolist()
    dezenas = frequencia["Dezena"].astype(int).tolist()

    escolhidas: set[int] = set()
    while len(escolhidas) < quantidade:
        escolhida = random.choices(dezenas, weights=pesos, k=1)[0]
        escolhidas.add(int(escolhida))

    return sorted(escolhidas)

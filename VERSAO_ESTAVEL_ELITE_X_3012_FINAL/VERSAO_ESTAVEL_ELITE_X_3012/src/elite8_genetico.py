from __future__ import annotations

import random

import pandas as pd

from src.elite8_cobertura import gerar_portfolio_elite8, score_diversidade


def _normalizar(jogo: list[int] | tuple[int, ...]) -> tuple[int, ...]:
    dezenas = tuple(sorted(set(int(dezena) for dezena in jogo)))
    while len(dezenas) < 6:
        dezenas = tuple(sorted(set(dezenas) | {random.randint(1, 60)}))
    return tuple(sorted(dezenas[:6]))


def crossover(jogo_a: list[int] | tuple[int, ...], jogo_b: list[int] | tuple[int, ...]) -> tuple[int, ...]:
    pai_a = list(_normalizar(jogo_a))
    pai_b = list(_normalizar(jogo_b))
    corte = random.randint(2, 4)
    filho = pai_a[:corte] + pai_b[corte:]
    return _normalizar(filho)


def mutacao(jogo: list[int] | tuple[int, ...], taxa: float = 0.18) -> tuple[int, ...]:
    dezenas = list(_normalizar(jogo))
    for indice in range(len(dezenas)):
        if random.random() <= taxa:
            novas = set(dezenas)
            novas.discard(dezenas[indice])
            while len(novas) < 6:
                novas.add(random.randint(1, 60))
            dezenas = sorted(novas)
    return _normalizar(dezenas)


def selecionar(populacao: list[tuple[int, ...]], quantidade: int) -> list[tuple[int, ...]]:
    ordenada = sorted(populacao, key=lambda jogo: score_diversidade(jogo, populacao), reverse=True)
    return ordenada[: max(1, int(quantidade))]


def evoluir_portfolio_elite8(
    geracoes: int = 40,
    tamanho_populacao: int = 200,
    tamanho_portfolio: int = 20,
    seed: int | None = 88,
) -> pd.DataFrame:
    if seed is not None:
        random.seed(seed)

    base = gerar_portfolio_elite8(
        quantidade_candidatos=max(5000, tamanho_populacao * 50),
        top_intermediario=max(200, tamanho_populacao),
        top_filtrado=max(100, tamanho_portfolio * 5),
        top_final=max(tamanho_portfolio, min(tamanho_populacao, 100)),
        seed=seed,
    )
    populacao = [
        tuple(int(parte.strip()) for parte in str(jogo).split("-") if parte.strip())
        for jogo in base["Jogo"].astype(str).tolist()
    ]
    while len(populacao) < tamanho_populacao:
        populacao.append(tuple(sorted(random.sample(range(1, 61), 6))))

    for _ in range(max(1, int(geracoes))):
        elite = selecionar(populacao, max(2, tamanho_populacao // 4))
        filhos: list[tuple[int, ...]] = []
        while len(elite) + len(filhos) < tamanho_populacao:
            pai_a, pai_b = random.sample(elite, 2)
            filhos.append(mutacao(crossover(pai_a, pai_b)))
        populacao = elite + filhos

    melhores = selecionar(populacao, tamanho_portfolio)
    linhas = []
    anteriores: list[tuple[int, ...]] = []
    for ranking, jogo in enumerate(melhores, start=1):
        linhas.append(
            {
                "Ranking": ranking,
                "Jogo": " - ".join(f"{dezena:02d}" for dezena in jogo),
                "Score genetico": score_diversidade(jogo, anteriores),
            }
        )
        anteriores.append(jogo)
    return pd.DataFrame(linhas)

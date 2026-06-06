from __future__ import annotations

from collections import Counter
from itertools import combinations
import random

import pandas as pd

from src.carregar_dados import COLUNAS_DEZENAS


PONTOS_PREMIACAO = {2: 1, 3: 5, 4: 50, 5: 500, 6: 5000}
FAIXAS = ["01-10", "11-20", "21-30", "31-40", "41-50", "51-60"]


def _normalizar_jogo(jogo: list[int] | tuple[int, ...]) -> tuple[int, ...]:
    dezenas = tuple(sorted(int(dezena) for dezena in jogo))
    if len(dezenas) != 6 or len(set(dezenas)) != 6:
        raise ValueError("O jogo deve conter exatamente 6 dezenas unicas.")
    if any(dezena < 1 or dezena > 60 for dezena in dezenas):
        raise ValueError("As dezenas devem estar entre 1 e 60.")
    return dezenas


def _historico_sets(historico: pd.DataFrame, janela: int = 1000) -> list[set[int]]:
    if historico is None or historico.empty:
        return []
    dados = historico.sort_values("Concurso", ascending=False).head(max(1, int(janela)))
    return [
        {int(linha[coluna]) for coluna in COLUNAS_DEZENAS}
        for _, linha in dados.iterrows()
    ]


def _jogos_historicos(historico: pd.DataFrame) -> set[tuple[int, ...]]:
    if historico is None or historico.empty:
        return set()
    return {
        tuple(sorted(int(linha[coluna]) for coluna in COLUNAS_DEZENAS))
        for _, linha in historico.iterrows()
    }


def _faixa(dezena: int) -> int:
    return min((int(dezena) - 1) // 10, 5)


def _distribuicao_faixas(jogo: tuple[int, ...]) -> tuple[int, ...]:
    distribuicao = [0] * 6
    for dezena in jogo:
        distribuicao[_faixa(dezena)] += 1
    return tuple(distribuicao)


def _max_consecutivas(jogo: tuple[int, ...]) -> int:
    maior = 1
    atual = 1
    for anterior, dezena in zip(jogo, jogo[1:]):
        if dezena == anterior + 1:
            atual += 1
            maior = max(maior, atual)
        else:
            atual = 1
    return maior


def _valido(
    jogo: tuple[int, ...],
    historicos: set[tuple[int, ...]],
    soma_minima: int,
    soma_maxima: int,
    max_consecutivas: int,
) -> bool:
    if jogo in historicos:
        return False
    soma = sum(jogo)
    pares = sum(dezena % 2 == 0 for dezena in jogo)
    distribuicao = _distribuicao_faixas(jogo)
    if soma < soma_minima or soma > soma_maxima:
        return False
    if pares not in {2, 3, 4}:
        return False
    if max(distribuicao) > 3:
        return False
    if sum(1 for total in distribuicao if total > 0) < 4:
        return False
    if _max_consecutivas(jogo) > max_consecutivas:
        return False
    return True


def score_premiacao(jogo: list[int] | tuple[int, ...], historico: pd.DataFrame, janela: int = 1000) -> float:
    jogo_norm = _normalizar_jogo(jogo)
    sorteios = _historico_sets(historico, janela=janela)
    return _score_premiacao_sorteios(jogo_norm, sorteios)


def _score_premiacao_sorteios(jogo_norm: tuple[int, ...], sorteios: list[set[int]]) -> float:
    if not sorteios:
        return 0.0
    jogo_set = set(jogo_norm)
    pontos = 0
    for resultado in sorteios:
        acertos = len(jogo_set & resultado)
        pontos += PONTOS_PREMIACAO.get(acertos, 0)
    return round(float(pontos), 4)


def score_pico(jogo: list[int] | tuple[int, ...], historico: pd.DataFrame, janela: int = 1000) -> float:
    jogo_norm = _normalizar_jogo(jogo)
    sorteios = _historico_sets(historico, janela=janela)
    return _score_pico_sorteios(jogo_norm, sorteios)


def _score_pico_sorteios(jogo_norm: tuple[int, ...], sorteios: list[set[int]]) -> float:
    if not sorteios:
        return 0.0
    jogo_set = set(jogo_norm)
    contagem = Counter(len(jogo_set & resultado) for resultado in sorteios)
    score = (
        contagem[6] * 5000
        + contagem[5] * 900
        + contagem[4] * 120
        + contagem[3] * 10
        + contagem[2]
    )
    bonus_melhor = max(contagem.keys(), default=0) * 25
    return round(float(score + bonus_melhor), 4)


def score_diversidade_elite9(
    jogo: list[int] | tuple[int, ...],
    portfolio: list[list[int] | tuple[int, ...]] | None = None,
) -> float:
    jogo_norm = _normalizar_jogo(jogo)
    portfolio_norm = [_normalizar_jogo(item) for item in portfolio or []]
    soma = sum(jogo_norm)
    pares = sum(dezena % 2 == 0 for dezena in jogo_norm)
    distribuicao = _distribuicao_faixas(jogo_norm)
    faixas_ocupadas = sum(1 for total in distribuicao if total > 0)
    soma_score = 100.0 if 155 <= soma <= 215 else 75.0 if 135 <= soma <= 235 else 35.0
    paridade_score = 100.0 if pares == 3 else 85.0 if pares in {2, 4} else 35.0
    faixa_score = min(100.0, faixas_ocupadas / 5 * 100.0)
    if max(distribuicao) > 3:
        faixa_score = min(faixa_score, 35.0)
    distancia_score = 100.0
    if portfolio_norm:
        distancias = [6 - len(set(jogo_norm) & set(outro)) for outro in portfolio_norm]
        distancia_media = sum(distancias) / len(distancias)
        distancia_minima = min(distancias)
        distancia_score = min(100.0, distancia_media / 6 * 70.0 + distancia_minima / 6 * 30.0)
    return round(max(0.0, min(100.0, soma_score * 0.20 + paridade_score * 0.20 + faixa_score * 0.25 + distancia_score * 0.35)), 4)


def crossover_jogos(pai1: list[int] | tuple[int, ...], pai2: list[int] | tuple[int, ...]) -> tuple[int, ...]:
    a = list(_normalizar_jogo(pai1))
    b = list(_normalizar_jogo(pai2))
    corte = random.randint(2, 4)
    filho = set(a[:corte] + b[corte:])
    while len(filho) < 6:
        filho.add(random.randint(1, 60))
    return tuple(sorted(filho))


def mutar_jogo(jogo: list[int] | tuple[int, ...], taxa_mutacao: float = 0.12) -> tuple[int, ...]:
    dezenas = set(_normalizar_jogo(jogo))
    for dezena in list(dezenas):
        if random.random() <= taxa_mutacao:
            dezenas.remove(dezena)
            while len(dezenas) < 6:
                dezenas.add(random.randint(1, 60))
    return tuple(sorted(dezenas))


def _score_final(
    jogo: tuple[int, ...],
    historico: pd.DataFrame,
    portfolio: list[tuple[int, ...]] | None = None,
    janela: int = 1000,
) -> dict[str, float]:
    sorteios = _historico_sets(historico, janela=janela)
    return _score_final_sorteios(jogo, sorteios, portfolio)


def _score_final_sorteios(
    jogo: tuple[int, ...],
    sorteios: list[set[int]],
    portfolio: list[tuple[int, ...]] | None = None,
) -> dict[str, float]:
    premiacao = _score_premiacao_sorteios(jogo, sorteios)
    pico = _score_pico_sorteios(jogo, sorteios)
    diversidade = score_diversidade_elite9(jogo, portfolio)
    final = premiacao * 0.45 + pico * 0.40 + diversidade * 0.15
    return {
        "Score premiacao": round(premiacao, 4),
        "Score pico": round(pico, 4),
        "Score diversidade": round(diversidade, 4),
        "Score final": round(final, 4),
    }


def _gerar_candidatos(
    quantidade: int,
    historicos: set[tuple[int, ...]],
    soma_minima: int,
    soma_maxima: int,
    max_consecutivas: int,
    seed: int | None,
) -> list[tuple[int, ...]]:
    rng = random.Random(seed)
    candidatos: set[tuple[int, ...]] = set()
    tentativas = 0
    limite = max(int(quantidade) * 8, 20000)
    while len(candidatos) < quantidade and tentativas < limite:
        tentativas += 1
        jogo = tuple(sorted(rng.sample(range(1, 61), 6)))
        if _valido(jogo, historicos, soma_minima, soma_maxima, max_consecutivas):
            candidatos.add(jogo)
    return list(candidatos)


def evoluir_populacao_elite9(
    populacao: list[list[int] | tuple[int, ...]],
    historico: pd.DataFrame,
    geracoes: int = 30,
    tamanho_populacao: int = 1000,
    taxa_mutacao: float = 0.12,
    soma_minima: int = 120,
    soma_maxima: int = 240,
    max_consecutivas: int = 2,
    janela_historico: int = 1000,
) -> list[tuple[int, ...]]:
    historicos = _jogos_historicos(historico)
    sorteios = _historico_sets(historico, janela=janela_historico)
    atual = [_normalizar_jogo(jogo) for jogo in populacao]
    atual = [jogo for jogo in atual if _valido(jogo, historicos, soma_minima, soma_maxima, max_consecutivas)]
    if not atual:
        atual = _gerar_candidatos(tamanho_populacao, historicos, soma_minima, soma_maxima, max_consecutivas, seed=9)

    for _ in range(max(1, int(geracoes))):
        avaliados = sorted(
            set(atual),
            key=lambda jogo: _score_final_sorteios(jogo, sorteios)["Score final"],
            reverse=True,
        )
        elite = avaliados[: max(2, min(len(avaliados), tamanho_populacao // 5))]
        filhos: set[tuple[int, ...]] = set(elite)
        while len(filhos) < tamanho_populacao:
            pai1, pai2 = random.sample(elite, 2)
            filho = mutar_jogo(crossover_jogos(pai1, pai2), taxa_mutacao=taxa_mutacao)
            if _valido(filho, historicos, soma_minima, soma_maxima, max_consecutivas):
                filhos.add(filho)
        atual = list(filhos)
    return sorted(
        set(atual),
        key=lambda jogo: _score_final_sorteios(jogo, sorteios)["Score final"],
        reverse=True,
    )


def gerar_jogos_elite9(
    historico: pd.DataFrame,
    quantidade_candidatos: int = 300000,
    top_intermediario: int = 10000,
    top_diversidade: int = 1000,
    seed: int | None = 9,
    soma_minima: int = 120,
    soma_maxima: int = 240,
    max_consecutivas: int = 2,
    janela_historico: int = 1000,
) -> list[tuple[int, ...]]:
    historicos = _jogos_historicos(historico)
    sorteios = _historico_sets(historico, janela=janela_historico)
    candidatos = _gerar_candidatos(
        quantidade_candidatos,
        historicos,
        soma_minima,
        soma_maxima,
        max_consecutivas,
        seed,
    )
    top = sorted(
        candidatos,
        key=lambda jogo: _score_premiacao_sorteios(jogo, sorteios),
        reverse=True,
    )[: max(1, min(int(top_intermediario), len(candidatos)))]
    portfolio: list[tuple[int, ...]] = []
    for jogo in top:
        if len(portfolio) >= top_diversidade:
            break
        if score_diversidade_elite9(jogo, portfolio) >= 58.0:
            portfolio.append(jogo)
    return portfolio or top[: max(1, int(top_diversidade))]


def gerar_portfolio_elite9(
    historico: pd.DataFrame,
    quantidade_candidatos: int = 300000,
    geracoes: int = 30,
    tamanho_populacao: int = 1000,
    taxa_mutacao: float = 0.12,
    quantidade_final: int = 20,
    seed: int | None = 9,
    soma_minima: int = 120,
    soma_maxima: int = 240,
    max_consecutivas: int = 2,
    janela_historico: int = 1000,
) -> pd.DataFrame:
    base = gerar_jogos_elite9(
        historico,
        quantidade_candidatos=quantidade_candidatos,
        top_intermediario=10000,
        top_diversidade=tamanho_populacao,
        seed=seed,
        soma_minima=soma_minima,
        soma_maxima=soma_maxima,
        max_consecutivas=max_consecutivas,
        janela_historico=janela_historico,
    )
    evoluida = evoluir_populacao_elite9(
        base,
        historico,
        geracoes=geracoes,
        tamanho_populacao=tamanho_populacao,
        taxa_mutacao=taxa_mutacao,
        soma_minima=soma_minima,
        soma_maxima=soma_maxima,
        max_consecutivas=max_consecutivas,
        janela_historico=janela_historico,
    )
    selecionados: list[tuple[int, ...]] = []
    for jogo in evoluida:
        if len(selecionados) >= quantidade_final:
            break
        if score_diversidade_elite9(jogo, selecionados) >= 55.0:
            selecionados.append(jogo)
    if len(selecionados) < quantidade_final:
        for jogo in evoluida:
            if jogo not in selecionados:
                selecionados.append(jogo)
            if len(selecionados) >= quantidade_final:
                break

    linhas = []
    anteriores: list[tuple[int, ...]] = []
    for ranking, jogo in enumerate(selecionados[:quantidade_final], start=1):
        scores = _score_final(jogo, historico, anteriores, janela=janela_historico)
        pares = sum(dezena % 2 == 0 for dezena in jogo)
        linhas.append(
            {
                "Ranking": ranking,
                "Jogo": " - ".join(f"{dezena:02d}" for dezena in jogo),
                **scores,
                "Soma": sum(jogo),
                "Pares": pares,
                "Impares": 6 - pares,
                "Faixas": " / ".join(str(total) for total in _distribuicao_faixas(jogo)),
            }
        )
        anteriores.append(jogo)
    return pd.DataFrame(linhas)

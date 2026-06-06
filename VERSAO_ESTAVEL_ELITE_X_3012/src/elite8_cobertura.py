from __future__ import annotations

from itertools import combinations
import random

import pandas as pd


FAIXAS_ELITE8 = ["01-10", "11-20", "21-30", "31-40", "41-50", "51-60"]
SOMA_MINIMA = 120
SOMA_MAXIMA = 240
SOMA_BUCKET = 10


def _normalizar_jogo(jogo: list[int] | tuple[int, ...]) -> tuple[int, ...]:
    dezenas = tuple(sorted(int(dezena) for dezena in jogo))
    if len(dezenas) != 6 or len(set(dezenas)) != 6:
        raise ValueError("Um jogo Elite 8 deve conter exatamente 6 dezenas unicas.")
    if any(dezena < 1 or dezena > 60 for dezena in dezenas):
        raise ValueError("As dezenas devem estar entre 1 e 60.")
    return dezenas


def _faixa(dezena: int) -> int:
    return min((int(dezena) - 1) // 10, 5)


def _distribuicao_faixas(jogo: tuple[int, ...]) -> tuple[int, ...]:
    distribuicao = [0] * 6
    for dezena in jogo:
        distribuicao[_faixa(dezena)] += 1
    return tuple(distribuicao)


def _bucket_soma(jogo: tuple[int, ...]) -> int:
    return sum(jogo) // SOMA_BUCKET


def _padrao_paridade(jogo: tuple[int, ...]) -> tuple[int, int]:
    pares = sum(dezena % 2 == 0 for dezena in jogo)
    return pares, 6 - pares


def _tem_mais_de_duas_consecutivas(jogo: tuple[int, ...]) -> bool:
    sequencia = 1
    for anterior, atual in zip(jogo, jogo[1:]):
        if atual == anterior + 1:
            sequencia += 1
            if sequencia > 2:
                return True
        else:
            sequencia = 1
    return False


def _distancia(jogo: tuple[int, ...], outro: tuple[int, ...]) -> int:
    return 6 - len(set(jogo) & set(outro))


def _score_estatico(jogo: tuple[int, ...]) -> float:
    soma = sum(jogo)
    pares, _impares = _padrao_paridade(jogo)
    distribuicao = _distribuicao_faixas(jogo)
    faixas_ocupadas = sum(1 for total in distribuicao if total > 0)
    maior_concentracao = max(distribuicao)
    soma_score = 100.0 if 160 <= soma <= 210 else 80.0 if 140 <= soma <= 230 else 50.0
    paridade_score = 100.0 if pares == 3 else 85.0 if pares in {2, 4} else 35.0
    faixa_score = min(100.0, (faixas_ocupadas / 5) * 100.0)
    if maior_concentracao > 3:
        faixa_score = min(faixa_score, 45.0)
    sequencia_penalidade = 18.0 if _tem_mais_de_duas_consecutivas(jogo) else 0.0
    return round(max(0.0, min(100.0, soma_score * 0.30 + paridade_score * 0.30 + faixa_score * 0.40 - sequencia_penalidade)), 4)


def score_diversidade(
    jogo: list[int] | tuple[int, ...],
    portfolio: list[list[int] | tuple[int, ...]] | None = None,
) -> float:
    jogo_norm = _normalizar_jogo(jogo)
    portfolio_norm = [_normalizar_jogo(item) for item in portfolio or []]
    score_base = _score_estatico(jogo_norm)
    if not portfolio_norm:
        return score_base

    distancias = [_distancia(jogo_norm, outro) for outro in portfolio_norm]
    distancia_media = sum(distancias) / len(distancias)
    distancia_minima = min(distancias)
    score_distancia = min(100.0, (distancia_media / 6.0) * 80.0 + (distancia_minima / 6.0) * 20.0)
    return round(max(0.0, min(100.0, score_base * 0.45 + score_distancia * 0.55)), 4)


def _jogo_valido(jogo: tuple[int, ...]) -> bool:
    soma = sum(jogo)
    pares, _impares = _padrao_paridade(jogo)
    distribuicao = _distribuicao_faixas(jogo)
    if soma < SOMA_MINIMA or soma > SOMA_MAXIMA:
        return False
    if pares not in {2, 3, 4}:
        return False
    if sum(1 for total in distribuicao if total > 0) < 4:
        return False
    if max(distribuicao) > 3:
        return False
    if _tem_mais_de_duas_consecutivas(jogo):
        return False
    return True


def gerar_candidatos_elite8(
    quantidade: int = 100000,
    seed: int | None = None,
) -> list[tuple[int, ...]]:
    rng = random.Random(seed)
    candidatos: set[tuple[int, ...]] = set()
    tentativas = 0
    limite_tentativas = max(int(quantidade) * 8, 10000)
    while len(candidatos) < quantidade and tentativas < limite_tentativas:
        tentativas += 1
        jogo = tuple(sorted(rng.sample(range(1, 61), 6)))
        if _jogo_valido(jogo):
            candidatos.add(jogo)
    return list(candidatos)


def _metricas_cobertura(portfolio: list[tuple[int, ...]]) -> dict[str, float | int]:
    dezenas = set()
    pares = set()
    faixas = set()
    somas = set()
    padroes = set()
    for jogo in portfolio:
        dezenas.update(jogo)
        pares.update(tuple(par) for par in combinations(jogo, 2))
        faixas.update(_faixa(dezena) for dezena in jogo)
        somas.add(_bucket_soma(jogo))
        padroes.add((_padrao_paridade(jogo), _distribuicao_faixas(jogo), _bucket_soma(jogo)))
    return {
        "Cobertura dezenas": len(dezenas),
        "Cobertura dezenas (%)": round(len(dezenas) / 60 * 100, 4),
        "Cobertura pares": len(pares),
        "Cobertura pares (%)": round(len(pares) / 1770 * 100, 4),
        "Cobertura faixas": len(faixas),
        "Cobertura somas": len(somas),
        "Cobertura padroes": len(padroes),
    }


def _ganho_marginal(
    jogo: tuple[int, ...],
    selecionados: list[tuple[int, ...]],
    cobertura: dict[str, set],
) -> float:
    pares_jogo = set(tuple(par) for par in combinations(jogo, 2))
    faixas_jogo = {_faixa(dezena) for dezena in jogo}
    soma_jogo = {_bucket_soma(jogo)}
    padrao_jogo = {(_padrao_paridade(jogo), _distribuicao_faixas(jogo), _bucket_soma(jogo))}
    novas_dezenas = len(set(jogo) - cobertura["dezenas"])
    novos_pares = len(pares_jogo - cobertura["pares"])
    novas_faixas = len(faixas_jogo - cobertura["faixas"])
    novas_somas = len(soma_jogo - cobertura["somas"])
    novos_padroes = len(padrao_jogo - cobertura["padroes"])
    score_cobertura = (
        novas_dezenas * 8.0
        + novos_pares * 1.2
        + novas_faixas * 5.0
        + novas_somas * 3.0
        + novos_padroes * 3.0
    )
    score_distancia = score_diversidade(jogo, selecionados)
    return round(score_cobertura * 0.55 + score_distancia * 0.45, 4)


def _selecionar_portfolio(candidatos: list[tuple[int, ...]], quantidade: int) -> list[tuple[int, ...]]:
    selecionados: list[tuple[int, ...]] = []
    restantes = list(candidatos)
    cobertura = {"dezenas": set(), "pares": set(), "faixas": set(), "somas": set(), "padroes": set()}
    while restantes and len(selecionados) < quantidade:
        melhor = max(restantes, key=lambda jogo: _ganho_marginal(jogo, selecionados, cobertura))
        selecionados.append(melhor)
        restantes.remove(melhor)
        cobertura["dezenas"].update(melhor)
        cobertura["pares"].update(tuple(par) for par in combinations(melhor, 2))
        cobertura["faixas"].update(_faixa(dezena) for dezena in melhor)
        cobertura["somas"].add(_bucket_soma(melhor))
        cobertura["padroes"].add((_padrao_paridade(melhor), _distribuicao_faixas(melhor), _bucket_soma(melhor)))
    return selecionados


def _linhas_portfolio(portfolio: list[tuple[int, ...]]) -> list[dict]:
    metricas = _metricas_cobertura(portfolio)
    linhas = []
    anteriores: list[tuple[int, ...]] = []
    for ranking, jogo in enumerate(portfolio, start=1):
        pares, impares = _padrao_paridade(jogo)
        distribuicao = _distribuicao_faixas(jogo)
        linhas.append(
            {
                "Ranking": ranking,
                "Jogo": " - ".join(f"{dezena:02d}" for dezena in jogo),
                "Score": score_diversidade(jogo, anteriores),
                "Diversidade": score_diversidade(jogo, anteriores),
                "Soma": sum(jogo),
                "Pares": pares,
                "Impares": impares,
                "Faixas ocupadas": sum(1 for total in distribuicao if total > 0),
                "Padrao faixas": " / ".join(str(total) for total in distribuicao),
                **metricas,
            }
        )
        anteriores.append(jogo)
    return linhas


def gerar_portfolio_elite8(
    quantidade_candidatos: int = 100000,
    top_intermediario: int = 1000,
    top_filtrado: int = 100,
    top_final: int = 20,
    seed: int | None = 8,
) -> pd.DataFrame:
    candidatos = gerar_candidatos_elite8(quantidade_candidatos, seed=seed)
    if not candidatos:
        return pd.DataFrame()
    ranqueados = sorted(candidatos, key=_score_estatico, reverse=True)
    top_1000 = ranqueados[: max(1, min(int(top_intermediario), len(ranqueados)))]
    filtrados = [jogo for jogo in top_1000 if _jogo_valido(jogo)]
    portfolio_100 = _selecionar_portfolio(filtrados, max(1, int(top_filtrado)))
    portfolio_final = portfolio_100[: max(1, min(int(top_final), len(portfolio_100)))]
    return pd.DataFrame(_linhas_portfolio(portfolio_final))


def gerar_portfolio_elite8_completo(
    quantidade_candidatos: int = 100000,
    seed: int | None = 8,
) -> pd.DataFrame:
    return gerar_portfolio_elite8(
        quantidade_candidatos=quantidade_candidatos,
        top_intermediario=1000,
        top_filtrado=100,
        top_final=100,
        seed=seed,
    )

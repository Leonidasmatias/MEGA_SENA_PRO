from __future__ import annotations

from itertools import combinations
import random

import pandas as pd

from src.carregar_dados import COLUNAS_DEZENAS
from src.estatisticas import (
    dezenas_atrasadas,
    frequencia_dezenas,
    pares_mais_frequentes,
    trincas_mais_frequentes,
    ultimos_concursos,
)


def _coluna_frequencia(df: pd.DataFrame) -> str:
    for coluna in df.columns:
        if str(coluna).lower().startswith("frequ"):
            return str(coluna)
    raise ValueError("Coluna de frequência não encontrada.")


def gerar_jogo(df: pd.DataFrame, quantidade: int = 6) -> list[int]:
    if quantidade != 6:
        raise ValueError("Este gerador cria jogos com exatamente 6 dezenas.")

    frequencia = frequencia_dezenas(df)
    coluna_freq = _coluna_frequencia(frequencia)
    pesos = (frequencia[coluna_freq] + 1).astype(float).tolist()
    dezenas = frequencia["Dezena"].astype(int).tolist()

    escolhidas: set[int] = set()
    while len(escolhidas) < quantidade:
        escolhida = random.choices(dezenas, weights=pesos, k=1)[0]
        escolhidas.add(int(escolhida))

    return sorted(escolhidas)


def _normalizar_serie(serie: pd.Series) -> pd.Series:
    maior = float(serie.max())
    if maior <= 0:
        return pd.Series([0.0] * len(serie), index=serie.index)
    return (serie.astype(float) / maior) * 100


def _frequencia_janela(df: pd.DataFrame, quantidade: int | None, nome_coluna: str) -> pd.DataFrame:
    dados = ultimos_concursos(df, quantidade) if quantidade else df
    frequencia = frequencia_dezenas(dados)
    coluna_freq = _coluna_frequencia(frequencia)
    return frequencia.rename(columns={coluna_freq: nome_coluna})


def _regularidade_dezena(df: pd.DataFrame, dezena: int) -> float:
    concursos = df.loc[df[COLUNAS_DEZENAS].eq(dezena).any(axis=1), "Concurso"].astype(int).sort_values()
    if len(concursos) < 3:
        return 0.0

    intervalos = concursos.diff().dropna()
    media = float(intervalos.mean())
    desvio = float(intervalos.std(ddof=0))
    if media <= 0:
        return 0.0

    coeficiente_variacao = desvio / media
    return round(max(0.0, 100 - min(coeficiente_variacao, 1.0) * 100), 2)


def calcular_score_dezenas(df: pd.DataFrame) -> pd.DataFrame:
    frequencia_geral = _frequencia_janela(df, None, "Frequência geral")
    frequencia_20 = _frequencia_janela(df, 20, "Frequência últimos 20")
    frequencia_50 = _frequencia_janela(df, 50, "Frequência últimos 50")
    frequencia_100 = _frequencia_janela(df, 100, "Frequência últimos 100")
    atrasadas = dezenas_atrasadas(df)[["Dezena", "Atraso"]]

    score = frequencia_geral[["Dezena", "Dezena formatada", "Frequência geral"]].copy()
    score = score.merge(frequencia_20[["Dezena", "Frequência últimos 20"]], on="Dezena")
    score = score.merge(frequencia_50[["Dezena", "Frequência últimos 50"]], on="Dezena")
    score = score.merge(frequencia_100[["Dezena", "Frequência últimos 100"]], on="Dezena")
    score = score.merge(atrasadas, on="Dezena")
    score["Regularidade"] = score["Dezena"].apply(lambda dezena: _regularidade_dezena(df, int(dezena)))

    freq_geral_norm = _normalizar_serie(score["Frequência geral"])
    freq_20_norm = _normalizar_serie(score["Frequência últimos 20"])
    freq_50_norm = _normalizar_serie(score["Frequência últimos 50"])
    freq_100_norm = _normalizar_serie(score["Frequência últimos 100"])
    atraso_norm = _normalizar_serie(score["Atraso"])
    regularidade_norm = score["Regularidade"].astype(float).clip(lower=0, upper=100)

    score["Score"] = (
        (freq_geral_norm * 0.20)
        + (freq_20_norm * 0.22)
        + (freq_50_norm * 0.22)
        + (freq_100_norm * 0.16)
        + (atraso_norm * 0.10)
        + (regularidade_norm * 0.10)
    ).clip(lower=0, upper=100).round(2)

    colunas = [
        "Dezena",
        "Dezena formatada",
        "Frequência geral",
        "Frequência últimos 20",
        "Frequência últimos 50",
        "Frequência últimos 100",
        "Atraso",
        "Regularidade",
        "Score",
    ]
    return score[colunas].sort_values(["Score", "Dezena"], ascending=[False, True]).reset_index(drop=True)


def _jogos_sorteados(df: pd.DataFrame) -> set[tuple[int, ...]]:
    return {
        tuple(sorted(int(dezena) for dezena in linha))
        for linha in df[COLUNAS_DEZENAS].to_numpy()
    }


def _tem_mais_de_duas_consecutivas(jogo: list[int]) -> bool:
    sequencia = 1
    for anterior, atual in zip(jogo, jogo[1:]):
        if atual == anterior + 1:
            sequencia += 1
            if sequencia > 2:
                return True
        else:
            sequencia = 1
    return False


def _distribuicao_faixas(jogo: list[int]) -> dict[int, int]:
    faixas = {indice: 0 for indice in range(6)}
    for dezena in jogo:
        faixa = min((int(dezena) - 1) // 10, 5)
        faixas[faixa] += 1
    return faixas


def _jogo_valido(
    df: pd.DataFrame,
    jogo: list[int],
    jogos_sorteados: set[tuple[int, ...]],
    exigir_tres_pares: bool,
) -> bool:
    if len(jogo) != 6:
        return False
    if len(set(jogo)) != 6:
        return False
    if any(int(dezena) < 1 or int(dezena) > 60 for dezena in jogo):
        return False

    jogo_ordenado = sorted(int(dezena) for dezena in jogo)
    pares = sum(dezena % 2 == 0 for dezena in jogo_ordenado)
    impares = 6 - pares
    soma = sum(jogo_ordenado)

    if exigir_tres_pares and pares != 3:
        return False
    if pares not in {2, 3, 4} or impares not in {2, 3, 4}:
        return False
    if soma < 120 or soma > 240:
        return False
    if _tem_mais_de_duas_consecutivas(jogo_ordenado):
        return False
    if max(_distribuicao_faixas(jogo_ordenado).values()) > 3:
        return False
    return tuple(jogo_ordenado) not in jogos_sorteados


def _sortear_dezenas_ponderadas(score: pd.DataFrame, tamanho_pool: int = 35) -> list[int]:
    pool = score.head(tamanho_pool).copy()
    dezenas = pool["Dezena"].astype(int).tolist()
    pesos = (pool["Score"].astype(float) + 1).tolist()
    escolhidas: set[int] = set()

    while len(escolhidas) < 6:
        escolhida = random.choices(dezenas, weights=pesos, k=1)[0]
        escolhidas.add(int(escolhida))

    return sorted(escolhidas)


def gerar_jogo_inteligente(df: pd.DataFrame) -> list[int]:
    score = calcular_score_dezenas(df)
    jogos_sorteados = _jogos_sorteados(df)

    for tamanho_pool, exigir_tres_pares in ((30, True), (40, True), (50, False), (60, False)):
        for _ in range(5000):
            jogo = _sortear_dezenas_ponderadas(score, tamanho_pool=tamanho_pool)
            if _jogo_valido(df, jogo, jogos_sorteados, exigir_tres_pares):
                return jogo

    dezenas_ordenadas = score["Dezena"].astype(int).tolist()
    for tamanho_pool in (18, 24, 30, 40, 60):
        pool = dezenas_ordenadas[:tamanho_pool]
        for inicio in range(0, max(0, len(pool) - 5)):
            jogo = sorted(pool[inicio : inicio + 6])
            if _jogo_valido(df, jogo, jogos_sorteados, exigir_tres_pares=False):
                return jogo

    for _ in range(10000):
        jogo = sorted(random.sample(range(1, 61), 6))
        if _jogo_valido(df, jogo, jogos_sorteados, exigir_tres_pares=False):
            return jogo

    return sorted(dezenas_ordenadas[:6])


def gerar_varios_jogos_inteligentes(df: pd.DataFrame, quantidade: int = 5) -> list[list[int]]:
    jogos: list[list[int]] = []
    combinacoes: set[tuple[int, ...]] = set()
    tentativas = 0

    while len(jogos) < quantidade and tentativas < quantidade * 1500:
        jogo = gerar_jogo_inteligente(df)
        combinacao = tuple(jogo)
        if combinacao not in combinacoes:
            jogos.append(jogo)
            combinacoes.add(combinacao)
        tentativas += 1

    return jogos


def _pontuar_par_impar(jogo: list[int]) -> float:
    pares = sum(dezena % 2 == 0 for dezena in jogo)
    if pares == 3:
        return 100.0
    if pares in {2, 4}:
        return 80.0
    return 30.0


def _pontuar_soma(jogo: list[int]) -> float:
    soma = sum(jogo)
    if 160 <= soma <= 210:
        return 100.0
    if 140 <= soma <= 230:
        return 80.0
    if 120 <= soma <= 240:
        return 55.0
    return 0.0


def _pontuar_faixas(jogo: list[int]) -> float:
    distribuicao = _distribuicao_faixas(jogo)
    faixas_ocupadas = sum(1 for total in distribuicao.values() if total > 0)
    maior_concentracao = max(distribuicao.values())
    if maior_concentracao > 3:
        return 0.0
    return min(100.0, (faixas_ocupadas / 5) * 100)


def _score_jogo_base_com_ranking(score: pd.DataFrame, jogo: list[int]) -> float:
    jogo_ordenado = sorted(int(dezena) for dezena in jogo)
    score_indexado = score.set_index("Dezena")
    scores = [float(score_indexado.loc[dezena, "Score"]) for dezena in jogo_ordenado]

    media_dezenas = sum(scores) / len(scores)
    equilibrio = _pontuar_par_impar(jogo_ordenado)
    soma = _pontuar_soma(jogo_ordenado)
    faixas = _pontuar_faixas(jogo_ordenado)
    penalizacao_sequencia = 20.0 if _tem_mais_de_duas_consecutivas(jogo_ordenado) else 0.0

    score_final = (
        (media_dezenas * 0.65)
        + (equilibrio * 0.12)
        + (soma * 0.12)
        + (faixas * 0.11)
        - penalizacao_sequencia
    )
    return round(max(0.0, min(100.0, score_final)), 2)


def _mapas_correlacao(df: pd.DataFrame) -> tuple[dict[tuple[int, int], int], dict[tuple[int, int, int], int]]:
    pares = {
        tuple(sorted((int(linha["Dezena 1"]), int(linha["Dezena 2"])))): int(linha["Frequência"])
        for _, linha in pares_mais_frequentes(df, limite=1770).iterrows()
    }
    trincas = {
        tuple(sorted((int(linha["Dezena 1"]), int(linha["Dezena 2"]), int(linha["Dezena 3"])))): int(linha["Frequência"])
        for _, linha in trincas_mais_frequentes(df, limite=34220).iterrows()
    }
    return pares, trincas


def _scores_correlacao_com_mapas(
    jogo: list[int],
    mapa_pares: dict[tuple[int, int], int],
    mapa_trincas: dict[tuple[int, int, int], int],
) -> tuple[float, float]:
    jogo_ordenado = sorted(int(dezena) for dezena in jogo)
    pares_jogo = list(combinations(jogo_ordenado, 2))
    trincas_jogo = list(combinations(jogo_ordenado, 3))
    maior_par = max(mapa_pares.values(), default=0)
    maior_trinca = max(mapa_trincas.values(), default=0)

    media_pares = sum(mapa_pares.get(tuple(par), 0) for par in pares_jogo) / len(pares_jogo)
    media_trincas = sum(mapa_trincas.get(tuple(trinca), 0) for trinca in trincas_jogo) / len(trincas_jogo)
    score_pares = (media_pares / maior_par * 100) if maior_par else 0.0
    score_trincas = (media_trincas / maior_trinca * 100) if maior_trinca else 0.0
    return round(max(0.0, min(100.0, score_pares)), 2), round(max(0.0, min(100.0, score_trincas)), 2)


def _score_correlacao_com_mapas(
    jogo: list[int],
    mapa_pares: dict[tuple[int, int], int],
    mapa_trincas: dict[tuple[int, int, int], int],
) -> float:
    score_pares, score_trincas = _scores_correlacao_com_mapas(jogo, mapa_pares, mapa_trincas)
    return round((score_pares * 0.67) + (score_trincas * 0.33), 2)


def score_correlacao_jogo(df: pd.DataFrame, jogo: list[int]) -> float:
    mapa_pares, mapa_trincas = _mapas_correlacao(df)
    return _score_correlacao_com_mapas(jogo, mapa_pares, mapa_trincas)


def score_jogo(df: pd.DataFrame, jogo: list[int]) -> float:
    score = calcular_score_dezenas(df)
    score_base = _score_jogo_base_com_ranking(score, jogo)
    mapa_pares, mapa_trincas = _mapas_correlacao(df)
    score_pares, score_trincas = _scores_correlacao_com_mapas(jogo, mapa_pares, mapa_trincas)
    score_final = (score_base * 0.70) + (score_pares * 0.20) + (score_trincas * 0.10)
    return round(max(0.0, min(100.0, score_final)), 2)


def classificar_jogo_por_score(score: float) -> str:
    if score >= 85:
        return "Elite"
    if score >= 75:
        return "Excelente"
    if score >= 65:
        return "Muito Forte"
    if score >= 55:
        return "Forte"
    if score >= 45:
        return "Moderado"
    return "Baixo"


def gerar_ranking_melhores_jogos(
    df: pd.DataFrame,
    quantidade_candidatos: int = 500,
    top: int = 10,
) -> pd.DataFrame:
    score = calcular_score_dezenas(df)
    mapa_pares, mapa_trincas = _mapas_correlacao(df)
    jogos_sorteados = _jogos_sorteados(df)
    candidatos: dict[tuple[int, ...], dict[str, float]] = {}
    tentativas = 0
    limite_tentativas = max(int(quantidade_candidatos) * 20, 1000)

    while len(candidatos) < int(quantidade_candidatos) and tentativas < limite_tentativas:
        tamanho_pool = random.choice([30, 35, 40, 45, 50, 60])
        jogo = _sortear_dezenas_ponderadas(score, tamanho_pool=tamanho_pool)
        tentativas += 1
        if not _jogo_valido(df, jogo, jogos_sorteados, exigir_tres_pares=False):
            continue
        combinacao = tuple(jogo)
        if combinacao not in candidatos:
            score_base = _score_jogo_base_com_ranking(score, jogo)
            score_pares, score_trincas = _scores_correlacao_com_mapas(jogo, mapa_pares, mapa_trincas)
            score_correlacao = _score_correlacao_com_mapas(jogo, mapa_pares, mapa_trincas)
            score_final = (score_base * 0.70) + (score_pares * 0.20) + (score_trincas * 0.10)
            candidatos[combinacao] = {
                "Score Base": round(score_base, 2),
                "Score Correlação": round(score_correlacao, 2),
                "Score Final": round(max(0.0, min(100.0, score_final)), 2),
            }

    dezenas_ordenadas = score["Dezena"].astype(int).tolist()
    for inicio in range(0, len(dezenas_ordenadas) - 5):
        if len(candidatos) >= int(quantidade_candidatos):
            break
        jogo = sorted(dezenas_ordenadas[inicio : inicio + 6])
        if not _jogo_valido(df, jogo, jogos_sorteados, exigir_tres_pares=False):
            continue
        combinacao = tuple(jogo)
        if combinacao not in candidatos:
            score_base = _score_jogo_base_com_ranking(score, jogo)
            score_pares, score_trincas = _scores_correlacao_com_mapas(jogo, mapa_pares, mapa_trincas)
            score_correlacao = _score_correlacao_com_mapas(jogo, mapa_pares, mapa_trincas)
            score_final = (score_base * 0.70) + (score_pares * 0.20) + (score_trincas * 0.10)
            candidatos[combinacao] = {
                "Score Base": round(score_base, 2),
                "Score Correlação": round(score_correlacao, 2),
                "Score Final": round(max(0.0, min(100.0, score_final)), 2),
            }

    linhas = []
    ordenados = sorted(candidatos.items(), key=lambda item: item[1]["Score Final"], reverse=True)
    for jogo, scores in ordenados[: int(top)]:
        score_final = scores["Score Final"]
        pares = sum(dezena % 2 == 0 for dezena in jogo)
        linhas.append(
            {
                "Ranking": len(linhas) + 1,
                "Jogo": " - ".join(f"{dezena:02d}" for dezena in jogo),
                "Score": scores["Score Final"],
                "Score Base": scores["Score Base"],
                "Score Correlação": scores.get("Score Correlação", scores.get("Score CorrelaÃ§Ã£o", 0.0)),
                "Score Final": scores["Score Final"],
                "Soma": sum(jogo),
                "Pares": pares,
                "Ímpares": 6 - pares,
                "Classificação": classificar_jogo_por_score(float(score_final)),
            }
        )

    colunas_ranking = [
        "Ranking",
        "Jogo",
        "Score",
        "Score Base",
        "Score Correlação",
        "Score Final",
        "Soma",
        "Pares",
        "Ímpares",
        "Classificação",
    ]
    return pd.DataFrame(linhas).reindex(columns=colunas_ranking)


def _parse_jogo_formatado(jogo: str) -> list[int]:
    return [int(dezena.strip()) for dezena in str(jogo).split("-") if dezena.strip()]


def validar_ranking_historico(
    df: pd.DataFrame,
    quantidade_concursos: int = 100,
    quantidade_candidatos: int = 500,
    top: int = 10,
) -> dict:
    dados = df.sort_values("Concurso", ascending=True).reset_index(drop=True)
    concursos_teste = dados.tail(min(int(quantidade_concursos), len(dados)))
    contagem_acertos = {acertos: 0 for acertos in range(7)}
    melhor_resultado = 0
    concursos_analisados = 0
    total_jogos = 0

    for _, concurso_real in concursos_teste.iterrows():
        concurso = int(concurso_real["Concurso"])
        historico = dados[dados["Concurso"].astype(int) < concurso]
        if historico.empty:
            continue

        ranking = gerar_ranking_melhores_jogos(
            historico,
            quantidade_candidatos=quantidade_candidatos,
            top=top,
        )
        if ranking.empty:
            continue

        resultado_real = {int(concurso_real[coluna]) for coluna in COLUNAS_DEZENAS}
        concursos_analisados += 1

        for _, linha in ranking.iterrows():
            jogo = _parse_jogo_formatado(str(linha["Jogo"]))
            acertos = len(set(jogo) & resultado_real)
            contagem_acertos[acertos] += 1
            melhor_resultado = max(melhor_resultado, acertos)
            total_jogos += 1

    jogos_3_mais = sum(contagem_acertos[acertos] for acertos in range(3, 7))
    jogos_4_mais = sum(contagem_acertos[acertos] for acertos in range(4, 7))

    return {
        "concursos_analisados": concursos_analisados,
        "total_jogos": total_jogos,
        "melhor_resultado": melhor_resultado,
        "jogos_3_mais": jogos_3_mais,
        "jogos_4_mais": jogos_4_mais,
        "taxa_3_mais": round((jogos_3_mais / total_jogos * 100) if total_jogos else 0.0, 2),
        "taxa_4_mais": round((jogos_4_mais / total_jogos * 100) if total_jogos else 0.0, 2),
        "quantidade_candidatos": int(quantidade_candidatos),
        "top": int(top),
    }


def validar_algoritmo_historico(df: pd.DataFrame, quantidade_concursos: int = 500) -> dict:
    dados = df.sort_values("Concurso", ascending=True).reset_index(drop=True)
    concursos_teste = dados.tail(min(int(quantidade_concursos), len(dados)))
    contagem_acertos = {acertos: 0 for acertos in range(7)}
    melhor_resultado = 0
    total_jogos = 0

    for _, concurso_real in concursos_teste.iterrows():
        concurso = int(concurso_real["Concurso"])
        historico = dados[dados["Concurso"].astype(int) < concurso]
        if historico.empty:
            continue

        jogo = gerar_jogo_inteligente(historico)
        resultado_real = {int(concurso_real[coluna]) for coluna in COLUNAS_DEZENAS}
        acertos = len(set(jogo) & resultado_real)

        contagem_acertos[acertos] += 1
        melhor_resultado = max(melhor_resultado, acertos)
        total_jogos += 1

    jogos_3_mais = sum(contagem_acertos[acertos] for acertos in range(3, 7))
    jogos_4_mais = sum(contagem_acertos[acertos] for acertos in range(4, 7))

    return {
        "concursos_analisados": total_jogos,
        "total_jogos": total_jogos,
        "melhor_resultado": melhor_resultado,
        "jogos_3_mais": jogos_3_mais,
        "jogos_4_mais": jogos_4_mais,
        "taxa_3_mais": round((jogos_3_mais / total_jogos * 100) if total_jogos else 0.0, 2),
        "taxa_4_mais": round((jogos_4_mais / total_jogos * 100) if total_jogos else 0.0, 2),
    }

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


FAIXAS_APRENDIZADO = ["1-10", "11-20", "21-30", "31-40", "41-50", "51-60"]
_ULTIMO_APRENDIZADO_HISTORICO: dict | None = None
_CACHE_CORRELACAO_MOTOR: dict[tuple[int, int, int], tuple[dict[tuple[int, int], int], dict[tuple[int, int, int], int]]] = {}
_CACHE_ATRASO_MOTOR: dict[tuple[int, int, int], tuple[dict[int, float], float]] = {}
_CACHE_FREQUENCIA_MOTOR: dict[tuple[int, int, int], dict[int, float]] = {}


def _chave_cache_df(df: pd.DataFrame) -> tuple[int, int, int]:
    ultimo_concurso = int(df["Concurso"].max()) if df is not None and not df.empty and "Concurso" in df.columns else 0
    return (id(df), len(df) if df is not None else 0, ultimo_concurso)


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
    chave_cache = _chave_cache_df(df)
    if chave_cache in _CACHE_CORRELACAO_MOTOR:
        mapa_pares, mapa_trincas = _CACHE_CORRELACAO_MOTOR[chave_cache]
    else:
        mapa_pares, mapa_trincas = _mapas_correlacao(df)
        _CACHE_CORRELACAO_MOTOR[chave_cache] = (mapa_pares, mapa_trincas)
    return _score_correlacao_com_mapas(jogo, mapa_pares, mapa_trincas)


def _perfil_aprendizado_atual() -> dict:
    if _ULTIMO_APRENDIZADO_HISTORICO and _ULTIMO_APRENDIZADO_HISTORICO.get("jogos_analisados", 0) > 0:
        return _ULTIMO_APRENDIZADO_HISTORICO

    return {
        "media_soma": 180.0,
        "media_pares": 3.0,
        "media_impares": 3.0,
        "faixas_medias": {faixa: 1.0 for faixa in FAIXAS_APRENDIZADO},
    }


def _registrar_aprendizado_historico(resultado: dict) -> dict:
    global _ULTIMO_APRENDIZADO_HISTORICO
    _ULTIMO_APRENDIZADO_HISTORICO = resultado
    return resultado


def score_aprendizado_historico(jogo: list[int]) -> float:
    perfil = _perfil_aprendizado_atual()
    jogo_ordenado = sorted(int(dezena) for dezena in jogo)
    soma = sum(jogo_ordenado)
    pares = sum(dezena % 2 == 0 for dezena in jogo_ordenado)
    distribuicao = _distribuicao_faixas(jogo_ordenado)

    media_soma = float(perfil.get("media_soma", 180.0))
    media_pares = float(perfil.get("media_pares", 3.0))
    faixas_medias = perfil.get("faixas_medias", {})

    score_soma = max(0.0, 100.0 - (abs(soma - media_soma) / 60.0 * 100.0))
    score_pares = max(0.0, 100.0 - (abs(pares - media_pares) / 3.0 * 100.0))

    desvio_faixas = 0.0
    for indice, faixa in enumerate(FAIXAS_APRENDIZADO):
        desvio_faixas += abs(float(distribuicao.get(indice, 0)) - float(faixas_medias.get(faixa, 1.0)))
    score_faixas = max(0.0, 100.0 - (desvio_faixas / 6.0 * 100.0))

    score_final = (score_soma * 0.40) + (score_pares * 0.25) + (score_faixas * 0.35)
    return round(max(0.0, min(100.0, score_final)), 2)


def score_repeticao_ultimo_concurso(df: pd.DataFrame, jogo: list[int]) -> float:
    ultimo_concurso = df.sort_values("Concurso", ascending=False).iloc[0]
    dezenas_ultimo = {int(ultimo_concurso[coluna]) for coluna in COLUNAS_DEZENAS}
    repetidas = len(set(int(dezena) for dezena in jogo) & dezenas_ultimo)

    if repetidas == 0:
        return 40.0
    if repetidas == 1:
        return 85.0
    if repetidas == 2:
        return 100.0
    if repetidas == 3:
        return 80.0
    return 30.0


def score_soma_estrategica(jogo: list[int]) -> float:
    soma = sum(int(dezena) for dezena in jogo)
    if 170 <= soma <= 200:
        return 100.0
    if 150 <= soma <= 220:
        return 80.0
    if 130 <= soma <= 240:
        return 50.0
    return 20.0


def score_distribuicao_estrategica(jogo: list[int]) -> float:
    distribuicao = _distribuicao_faixas([int(dezena) for dezena in jogo])
    faixas_ocupadas = sum(1 for total in distribuicao.values() if total > 0)

    if faixas_ocupadas >= 5:
        score = 100.0
    elif faixas_ocupadas == 4:
        score = 85.0
    elif faixas_ocupadas == 3:
        score = 55.0
    else:
        score = 25.0

    if max(distribuicao.values()) >= 4:
        score = min(score, 40.0)
    return float(score)

def _distancia_jogos(jogo: list[int] | tuple[int, ...], referencia: list[int] | tuple[int, ...]) -> int:
    return 6 - len(set(int(dezena) for dezena in jogo) & set(int(dezena) for dezena in referencia))


def _distancia_media_jogos(
    jogo: list[int] | tuple[int, ...],
    jogos_referencia: list[list[int] | tuple[int, ...]],
) -> float:
    if not jogos_referencia:
        return 6.0
    distancias = [_distancia_jogos(jogo, referencia) for referencia in jogos_referencia[:50]]
    return round(sum(distancias) / len(distancias), 2)


def score_diversidade_historica(
    jogo: list[int] | tuple[int, ...],
    jogos_referencia: list[list[int] | tuple[int, ...]] | None = None,
) -> float:
    referencias = jogos_referencia or []
    if not referencias:
        return 100.0

    distancia_media = _distancia_media_jogos(jogo, referencias)
    distribuicao_jogo = _distribuicao_faixas([int(dezena) for dezena in jogo])
    diferencas_faixas = []
    for referencia in referencias[:50]:
        distribuicao_referencia = _distribuicao_faixas([int(dezena) for dezena in referencia])
        diferenca = sum(
            abs(distribuicao_jogo[indice] - distribuicao_referencia[indice])
            for indice in distribuicao_jogo
        )
        diferencas_faixas.append(diferenca)

    media_diferenca_faixas = sum(diferencas_faixas) / len(diferencas_faixas)
    score_distancia = (distancia_media / 6.0) * 80.0
    bonus_distribuicao = min(20.0, (media_diferenca_faixas / 12.0) * 20.0)
    score = score_distancia + bonus_distribuicao

    if distancia_media <= 2:
        score = min(score, 45.0)
    elif distancia_media <= 3:
        score = min(score, 70.0)

    return round(max(0.0, min(100.0, score)), 2)
def _dezenas_repetidas_ultimo_concurso(df: pd.DataFrame, jogo: list[int]) -> int:
    ultimo_concurso = df.sort_values("Concurso", ascending=False).iloc[0]
    dezenas_ultimo = {int(ultimo_concurso[coluna]) for coluna in COLUNAS_DEZENAS}
    return len(set(int(dezena) for dezena in jogo) & dezenas_ultimo)


def _componentes_score_jogo(
    df: pd.DataFrame,
    score: pd.DataFrame,
    mapa_pares: dict[tuple[int, int], int],
    mapa_trincas: dict[tuple[int, int, int], int],
    jogo: list[int],
    jogos_referencia: list[list[int] | tuple[int, ...]] | None = None,
) -> dict[str, float]:
    score_base = _score_jogo_base_com_ranking(score, jogo)
    score_correlacao = _score_correlacao_com_mapas(jogo, mapa_pares, mapa_trincas)
    score_aprendizado = score_aprendizado_historico(jogo)
    score_modelo = (score_base * 0.55) + (score_correlacao * 0.25) + (score_aprendizado * 0.20)

    score_repeticao = score_repeticao_ultimo_concurso(df, jogo)
    score_soma = score_soma_estrategica(jogo)
    score_distribuicao = score_distribuicao_estrategica(jogo)
    score_estrategico = (score_repeticao * 0.35) + (score_soma * 0.35) + (score_distribuicao * 0.30)
    referencias = jogos_referencia or []
    score_diversidade = score_diversidade_historica(jogo, referencias)
    distancia_media = _distancia_media_jogos(jogo, referencias)
    score_final = (score_modelo * 0.65) + (score_estrategico * 0.20) + (score_diversidade * 0.15)

    return {
        "Score Base": round(score_base, 2),
        "Score Correlação": round(score_correlacao, 2),
        "Score Aprendizado": round(score_aprendizado, 2),
        "Score Estratégico": round(score_estrategico, 2),
        "Score Diversidade": round(score_diversidade, 2),
        "Distância Média": round(distancia_media, 2),
        "Repetidas Último Concurso": float(_dezenas_repetidas_ultimo_concurso(df, jogo)),
        "Score Repetição": round(score_repeticao, 2),
        "Score Soma": round(score_soma, 2),
        "Score Distribuição": round(score_distribuicao, 2),
        "Score Final": round(max(0.0, min(100.0, score_final)), 2),
    }


def score_jogo(df: pd.DataFrame, jogo: list[int]) -> float:
    score = calcular_score_dezenas(df)
    mapa_pares, mapa_trincas = _mapas_correlacao(df)
    componentes = _componentes_score_jogo(df, score, mapa_pares, mapa_trincas, jogo)
    return round(float(componentes["Score Final"]), 2)


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
    quantidade_candidatos = max(1, int(quantidade_candidatos))
    top = max(1, min(int(top), quantidade_candidatos))
    score = calcular_score_dezenas(df)
    mapa_pares, mapa_trincas = _mapas_correlacao(df)
    jogos_sorteados = _jogos_sorteados(df)
    candidatos: dict[tuple[int, ...], dict[str, float]] = {}
    tentativas = 0
    limite_tentativas = max(quantidade_candidatos * 40, 5000)

    while len(candidatos) < quantidade_candidatos and tentativas < limite_tentativas:
        tamanho_pool = random.choice([30, 35, 40, 45, 50, 60])
        jogo = _sortear_dezenas_ponderadas(score, tamanho_pool=tamanho_pool)
        tentativas += 1
        if not _jogo_valido(df, jogo, jogos_sorteados, exigir_tres_pares=False):
            continue
        combinacao = tuple(jogo)
        if combinacao not in candidatos:
            candidatos[combinacao] = _componentes_score_jogo(df, score, mapa_pares, mapa_trincas, jogo)

    dezenas_ordenadas = score["Dezena"].astype(int).tolist()
    for inicio in range(0, len(dezenas_ordenadas) - 5):
        if len(candidatos) >= quantidade_candidatos:
            break
        jogo = sorted(dezenas_ordenadas[inicio : inicio + 6])
        if not _jogo_valido(df, jogo, jogos_sorteados, exigir_tres_pares=False):
            continue
        combinacao = tuple(jogo)
        if combinacao not in candidatos:
            candidatos[combinacao] = _componentes_score_jogo(df, score, mapa_pares, mapa_trincas, jogo)

    referencias_diversidade: list[tuple[int, ...]] = []
    candidatos_diversos: dict[tuple[int, ...], dict[str, float]] = {}
    preliminares = sorted(candidatos.items(), key=lambda item: item[1]["Score Final"], reverse=True)
    for jogo, _scores in preliminares:
        referencias = referencias_diversidade[:50]
        candidatos_diversos[jogo] = _componentes_score_jogo(
            df,
            score,
            mapa_pares,
            mapa_trincas,
            list(jogo),
            referencias,
        )
        referencias_diversidade.append(jogo)

    linhas = []
    ordenados = sorted(candidatos_diversos.items(), key=lambda item: item[1]["Score Final"], reverse=True)
    for jogo, scores in ordenados[:top]:
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
                "Score Estratégico": scores.get("Score Estratégico", 0.0),
                "Score Diversidade": scores.get("Score Diversidade", 0.0),
                "Distância Média": scores.get("Distância Média", 0.0),
                "Repetidas Último Concurso": int(scores.get("Repetidas Último Concurso", 0)),
                "Score Repetição": scores.get("Score Repetição", 0.0),
                "Score Soma": scores.get("Score Soma", 0.0),
                "Score Distribuição": scores.get("Score Distribuição", 0.0),
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
        "Score Estratégico",
        "Score Diversidade",
        "Distância Média",
        "Repetidas Último Concurso",
        "Score Repetição",
        "Score Soma",
        "Score Distribuição",
        "Soma",
        "Pares",
        "Ímpares",
        "Classificação",
    ]
    return pd.DataFrame(linhas).reindex(columns=colunas_ranking)


def gerar_previsao_concurso_alvo(df: pd.DataFrame, concurso_alvo: int) -> dict:
    """Gera um pacote de previsao focado no proximo concurso futuro."""
    dados = df.sort_values("Concurso", ascending=True).reset_index(drop=True)
    if dados.empty:
        raise ValueError("Base historica vazia.")

    ultimo_concurso = int(dados["Concurso"].max())
    concurso_alvo = int(concurso_alvo)
    if concurso_alvo <= 0:
        concurso_alvo = ultimo_concurso + 1

    score_dezenas = calcular_score_dezenas(dados)
    top_20 = score_dezenas.head(20).copy().reset_index(drop=True)
    top_20.insert(0, "Ranking", range(1, len(top_20) + 1))

    ranking = gerar_ranking_melhores_jogos(dados, quantidade_candidatos=900, top=12)
    if ranking.empty:
        jogos_base = gerar_varios_jogos_inteligentes(dados, quantidade=6)
        ranking = pd.DataFrame(
            [
                {
                    "Ranking": indice,
                    "Jogo": " - ".join(f"{dezena:02d}" for dezena in jogo),
                    "Score": score_jogo(dados, jogo),
                    "Score Final": score_jogo(dados, jogo),
                    "Soma": sum(jogo),
                    "Pares": sum(dezena % 2 == 0 for dezena in jogo),
                    "Impares": sum(dezena % 2 != 0 for dezena in jogo),
                    "Classificacao": "Fallback",
                }
                for indice, jogo in enumerate(jogos_base, start=1)
            ]
        )

    ranking = ranking.copy().head(6).reset_index(drop=True)
    ranking.insert(0, "Concurso alvo", concurso_alvo)
    ranking["Tipo"] = ["Principal"] + [f"Alternativo {indice}" for indice in range(1, len(ranking))]
    coluna_impares = next((coluna for coluna in ranking.columns if "mpares" in str(coluna)), "Impares")
    ranking["Justificativa estatistica"] = ranking.apply(
        lambda linha: (
            "Jogo selecionado para o concurso alvo "
            f"{concurso_alvo} combinando frequencia geral, janelas de 20/50/100 concursos, "
            f"atraso, regularidade, correlacao, soma {int(linha.get('Soma', 0))}, "
            f"{int(linha.get('Pares', 0))} pares, distribuicao por faixas e repeticao controlada "
            "do ultimo concurso."
        ),
        axis=1,
    )

    dezenas_top_20 = top_20["Dezena"].astype(int).head(20).sort_values().tolist()
    jogo_principal = _parse_jogo_formatado(str(ranking.iloc[0]["Jogo"])) if not ranking.empty else []
    jogos_alternativos = ranking.iloc[1:6].copy().reset_index(drop=True)
    jogo_20 = " - ".join(f"{dezena:02d}" for dezena in dezenas_top_20)
    score_20 = round(float(top_20["Score"].astype(float).head(20).mean()), 2) if not top_20.empty else 0.0

    cobertura_20 = pd.DataFrame(
        [
            {
                "Concurso alvo": concurso_alvo,
                "Tipo": "Cobertura 20 dezenas",
                "Jogo": jogo_20,
                "Score": score_20,
                "Score Final": score_20,
                "Soma": sum(dezenas_top_20),
                "Pares": sum(dezena % 2 == 0 for dezena in dezenas_top_20),
                coluna_impares: sum(dezena % 2 != 0 for dezena in dezenas_top_20),
                "Justificativa estatistica": (
                    "Jogo unico de cobertura formado pelas 20 dezenas mais fortes do ranking "
                    "para ampliar combinacoes a partir do concurso alvo."
                ),
            }
        ]
    )

    exportacao = pd.concat([ranking, cobertura_20], ignore_index=True)
    justificativa = (
        f"Previsao calculada para o concurso alvo {concurso_alvo}, mantendo como base historica "
        f"os concursos carregados ate {ultimo_concurso}. O ranking pondera frequencia geral, "
        "frequencias recentes de 20, 50 e 100 concursos, atraso atual, regularidade, correlacao "
        "entre dezenas, equilibrio par/impar, distribuicao por faixas, soma provavel, repeticao "
        "controlada do ultimo concurso e penalizacao de padroes improvaveis."
    )

    return {
        "concurso_alvo": concurso_alvo,
        "ultimo_concurso": ultimo_concurso,
        "top_20_dezenas": top_20,
        "jogo_principal": ranking.iloc[[0]].reset_index(drop=True) if not ranking.empty else pd.DataFrame(),
        "jogos_alternativos": jogos_alternativos,
        "jogo_20_dezenas": cobertura_20,
        "exportacao": exportacao,
        "jogo_principal_dezenas": jogo_principal,
        "jogo_20_dezenas_lista": dezenas_top_20,
        "justificativa_estatistica": justificativa,
    }


def _parse_jogo_formatado(jogo: str) -> list[int]:
    return [int(dezena.strip()) for dezena in str(jogo).split("-") if dezena.strip()]


def validar_ranking_historico(
    df: pd.DataFrame,
    quantidade_concursos: int = 100,
    quantidade_candidatos: int = 500,
    top: int = 10,
) -> dict:
    dados = df.sort_values("Concurso", ascending=True).reset_index(drop=True)
    quantidade_concursos = max(1, min(int(quantidade_concursos), len(dados)))
    quantidade_candidatos = max(1, int(quantidade_candidatos))
    top = max(1, min(int(top), quantidade_candidatos))
    concursos_teste = dados.tail(quantidade_concursos)
    contagem_acertos = {acertos: 0 for acertos in range(7)}
    melhor_resultado = 0
    concursos_analisados = 0
    total_jogos = 0
    jogos_por_concurso = 0
    soma_score_diversidade = 0.0
    soma_distancia_media = 0.0

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
        jogos_por_concurso = max(jogos_por_concurso, len(ranking))

        for _, linha in ranking.iterrows():
            jogo = _parse_jogo_formatado(str(linha["Jogo"]))
            acertos = len(set(jogo) & resultado_real)
            contagem_acertos[acertos] += 1
            melhor_resultado = max(melhor_resultado, acertos)
            soma_score_diversidade += float(linha.get("Score Diversidade", 0.0))
            soma_distancia_media += float(linha.get("Distância Média", 0.0))
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
        "quantidade_candidatos": quantidade_candidatos,
        "top": top,
        "jogos_por_concurso": int(top),
        "media_score_diversidade": round((soma_score_diversidade / total_jogos) if total_jogos else 0.0, 2),
        "media_distancia": round((soma_distancia_media / total_jogos) if total_jogos else 0.0, 2),
        "observacao": f"Validação baseada no Top {top} de {quantidade_candidatos} candidatos por concurso.",
    }


def _validar_base_motor_elite(df: pd.DataFrame) -> None:
    if df is None or df.empty:
        raise ValueError("Base historica vazia ou indisponivel para o Motor Elite.")

    colunas_obrigatorias = {"Concurso", *COLUNAS_DEZENAS}
    colunas_faltantes = sorted(colunas_obrigatorias - set(df.columns))
    if colunas_faltantes:
        raise ValueError(
            "Base historica fora do padrao. Colunas ausentes: "
            + ", ".join(colunas_faltantes)
        )


def score_equilibrio_jogo(jogo: list[int]) -> float:
    jogo_ordenado = sorted(int(dezena) for dezena in jogo)
    if len(jogo_ordenado) != 6 or len(set(jogo_ordenado)) != 6:
        return 0.0

    pares = sum(dezena % 2 == 0 for dezena in jogo_ordenado)
    if pares == 3:
        score_paridade = 100.0
    elif pares in (2, 4):
        score_paridade = 85.0
    elif pares in (1, 5):
        score_paridade = 45.0
    else:
        score_paridade = 20.0

    score_distribuicao = score_distribuicao_estrategica(jogo_ordenado)
    score = (score_paridade * 0.60) + (score_distribuicao * 0.40)
    return round(max(0.0, min(100.0, score)), 2)


def score_atraso_dezenas(df: pd.DataFrame, jogo: list[int]) -> float:
    chave_cache = _chave_cache_df(df)
    if chave_cache in _CACHE_ATRASO_MOTOR:
        mapa_atraso, maior_atraso = _CACHE_ATRASO_MOTOR[chave_cache]
    else:
        atrasadas = dezenas_atrasadas(df)
        if atrasadas.empty or "Atraso" not in atrasadas.columns:
            return 0.0

        mapa_atraso = {
            int(linha["Dezena"]): float(linha["Atraso"])
            for _, linha in atrasadas.iterrows()
        }
        maior_atraso = max(mapa_atraso.values()) if mapa_atraso else 0.0
        _CACHE_ATRASO_MOTOR[chave_cache] = (mapa_atraso, maior_atraso)

    maior_atraso = max(mapa_atraso.values()) if mapa_atraso else 0.0
    if maior_atraso <= 0:
        return 0.0

    media_atraso = sum(mapa_atraso.get(int(dezena), 0.0) for dezena in jogo) / 6
    return round(max(0.0, min(100.0, (media_atraso / maior_atraso) * 100)), 2)


def score_frequencia_quente_fria(df: pd.DataFrame, jogo: list[int]) -> float:
    chave_cache = _chave_cache_df(df)
    if chave_cache in _CACHE_FREQUENCIA_MOTOR:
        mapa_score = _CACHE_FREQUENCIA_MOTOR[chave_cache]
    else:
        score_dezenas = calcular_score_dezenas(df)
        mapa_score = {
            int(linha["Dezena"]): float(linha["Score"])
            for _, linha in score_dezenas.iterrows()
        }
        _CACHE_FREQUENCIA_MOTOR[chave_cache] = mapa_score

    if not mapa_score:
        return 0.0

    score = sum(mapa_score.get(int(dezena), 0.0) for dezena in jogo) / 6
    return round(max(0.0, min(100.0, score)), 2)


def score_monte_carlo(jogo: list[int]) -> float:
    jogo_ordenado = sorted(int(dezena) for dezena in jogo)
    if len(jogo_ordenado) != 6 or len(set(jogo_ordenado)) != 6:
        return 0.0

    score = (
        (score_soma_estrategica(jogo_ordenado) * 0.35)
        + (score_distribuicao_estrategica(jogo_ordenado) * 0.35)
        + (score_equilibrio_jogo(jogo_ordenado) * 0.30)
    )
    return round(max(0.0, min(100.0, score)), 2)


def _dezenas_ultimo_concurso(df: pd.DataFrame) -> set[int]:
    if df is None or df.empty:
        return set()
    ultimo_concurso = df.sort_values("Concurso", ascending=False).iloc[0]
    return {int(ultimo_concurso[coluna]) for coluna in COLUNAS_DEZENAS}


def _jogo_valido_motor_elite(
    jogo: list[int],
    jogos_sorteados: set[tuple[int, ...]],
    dezenas_ultimo_concurso: set[int] | None = None,
) -> bool:
    jogo_ordenado = sorted(int(dezena) for dezena in jogo)
    if len(jogo_ordenado) != 6 or len(set(jogo_ordenado)) != 6:
        return False
    if any(dezena < 1 or dezena > 60 for dezena in jogo_ordenado):
        return False
    if tuple(jogo_ordenado) in jogos_sorteados:
        return False

    soma = sum(jogo_ordenado)
    pares = sum(dezena % 2 == 0 for dezena in jogo_ordenado)
    distribuicao = _distribuicao_faixas(jogo_ordenado)
    faixas_ocupadas = sum(1 for total in distribuicao.values() if total > 0)

    if soma < 150 or soma > 230:
        return False
    if pares < 2 or pares > 4:
        return False
    if faixas_ocupadas < 4:
        return False
    if max(distribuicao.values()) > 3:
        return False
    if _tem_mais_de_duas_consecutivas(jogo_ordenado):
        return False
    if dezenas_ultimo_concurso and len(set(jogo_ordenado) & dezenas_ultimo_concurso) > 3:
        return False
    return True


def _linha_motor_elite(
    df: pd.DataFrame,
    score_dezenas: pd.DataFrame,
    mapa_pares: dict[tuple[int, int], int],
    mapa_trincas: dict[tuple[int, int, int], int],
    jogo: list[int],
) -> dict:
    componentes = _componentes_score_jogo(df, score_dezenas, mapa_pares, mapa_trincas, jogo)
    score_jogo_valor = float(componentes["Score Final"])
    score_correlacao = score_correlacao_jogo(df, jogo)
    score_aprendizado = score_aprendizado_historico(jogo)
    score_repeticao = score_repeticao_ultimo_concurso(df, jogo)
    score_soma = score_soma_estrategica(jogo)
    score_distribuicao = score_distribuicao_estrategica(jogo)
    score_equilibrio = score_equilibrio_jogo(jogo)
    score_atraso = score_atraso_dezenas(df, jogo)
    score_frequencia = score_frequencia_quente_fria(df, jogo)
    score_monte = score_monte_carlo(jogo)
    score_elite = (
        (score_jogo_valor * 0.30)
        + (score_correlacao * 0.18)
        + (score_aprendizado * 0.12)
        + (score_repeticao * 0.08)
        + (score_soma * 0.08)
        + (score_distribuicao * 0.07)
        + (score_equilibrio * 0.07)
        + (score_atraso * 0.05)
        + (score_frequencia * 0.03)
        + (score_monte * 0.02)
    )

    jogo_ordenado = sorted(int(dezena) for dezena in jogo)
    pares = sum(dezena % 2 == 0 for dezena in jogo_ordenado)
    distribuicao = _distribuicao_faixas(jogo_ordenado)
    return {
        "Jogo": " - ".join(f"{dezena:02d}" for dezena in jogo_ordenado),
        "Score Elite": round(max(0.0, min(100.0, score_elite)), 2),
        "Score Final": round(max(0.0, min(100.0, score_elite)), 2),
        "Score Jogo": round(score_jogo_valor, 2),
        "Score Correlação": round(score_correlacao, 2),
        "Score Aprendizado": round(score_aprendizado, 2),
        "Score Repetição": round(score_repeticao, 2),
        "Score Soma": round(score_soma, 2),
        "Score Distribuição": round(score_distribuicao, 2),
        "Score Equilibrio": round(score_equilibrio, 2),
        "Score Atraso": round(score_atraso, 2),
        "Score Frequencia": round(score_frequencia, 2),
        "Score Monte Carlo": round(score_monte, 2),
        "Soma": sum(jogo_ordenado),
        "Pares": pares,
        "Ímpares": 6 - pares,
        "Faixas ocupadas": sum(1 for total in distribuicao.values() if total > 0),
        "Classificacao": classificar_jogo_por_score(round(max(0.0, min(100.0, score_elite)), 2)),
        "Justificativa": (
            f"Correlacao {round(score_correlacao, 2):.1f}; "
            f"soma {sum(jogo_ordenado)}; "
            f"{pares} pares; "
            f"{sum(1 for total in distribuicao.values() if total > 0)} faixas; "
            f"{_dezenas_repetidas_ultimo_concurso(df, jogo_ordenado)} repetidas do ultimo concurso."
        ),
        "Repetidas último concurso": _dezenas_repetidas_ultimo_concurso(df, jogo_ordenado),
    }


def gerar_motor_elite_6(
    df: pd.DataFrame,
    quantidade_candidatos: int = 50000,
    top: int = 50,
) -> pd.DataFrame:
    _validar_base_motor_elite(df)
    quantidade_candidatos = max(1, int(quantidade_candidatos))
    top = max(1, min(int(top), quantidade_candidatos))
    score_dezenas = calcular_score_dezenas(df)
    mapa_pares, mapa_trincas = _mapas_correlacao(df)
    jogos_sorteados = _jogos_sorteados(df)
    dezenas_ultimo = _dezenas_ultimo_concurso(df)
    candidatos: dict[tuple[int, ...], dict] = {}
    tentativas = 0
    limite_tentativas = max(quantidade_candidatos * 12, 20000)

    while len(candidatos) < quantidade_candidatos and tentativas < limite_tentativas:
        tentativas += 1
        if tentativas % 5 == 0:
            jogo = sorted(random.sample(range(1, 61), 6))
        else:
            tamanho_pool = random.choice([35, 40, 45, 50, 60])
            jogo = _sortear_dezenas_ponderadas(score_dezenas, tamanho_pool=tamanho_pool)

        if not _jogo_valido_motor_elite(jogo, jogos_sorteados, dezenas_ultimo):
            continue

        combinacao = tuple(jogo)
        if combinacao not in candidatos:
            candidatos[combinacao] = _linha_motor_elite(df, score_dezenas, mapa_pares, mapa_trincas, jogo)

    ordenados = sorted(candidatos.values(), key=lambda linha: linha["Score Elite"], reverse=True)
    linhas = []
    for indice, linha in enumerate(ordenados[:top], start=1):
        linha = dict(linha)
        linha["Ranking"] = indice
        linhas.append(linha)

    colunas = [
        "Ranking",
        "Jogo",
        "Score Elite",
        "Score Final",
        "Score Jogo",
        "Score Correlação",
        "Score Aprendizado",
        "Score Repetição",
        "Score Soma",
        "Score Distribuição",
        "Score Equilibrio",
        "Score Atraso",
        "Score Frequencia",
        "Score Monte Carlo",
        "Soma",
        "Pares",
        "Ímpares",
        "Faixas ocupadas",
        "Classificacao",
        "Justificativa",
        "Repetidas último concurso",
    ]
    return pd.DataFrame(linhas).reindex(columns=colunas)


def validar_motor_elite_6(
    df: pd.DataFrame,
    quantidade_concursos: int = 100,
    quantidade_candidatos: int = 50000,
    top: int = 50,
) -> dict:
    _validar_base_motor_elite(df)
    dados = df.sort_values("Concurso", ascending=True).reset_index(drop=True)
    quantidade_concursos = max(1, min(int(quantidade_concursos), len(dados)))
    quantidade_candidatos = max(1, int(quantidade_candidatos))
    top = max(1, min(int(top), quantidade_candidatos))
    concursos_teste = dados.tail(quantidade_concursos)
    contagem_acertos = {acertos: 0 for acertos in range(7)}
    concursos_analisados = 0
    total_jogos = 0
    melhor_resultado = 0

    for _, concurso_real in concursos_teste.iterrows():
        concurso = int(concurso_real["Concurso"])
        historico = dados[dados["Concurso"].astype(int) < concurso]
        if historico.empty:
            continue

        ranking = gerar_motor_elite_6(
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
    jogos_5_mais = sum(contagem_acertos[acertos] for acertos in range(5, 7))
    jogos_6 = contagem_acertos[6]

    return {
        "concursos_analisados": concursos_analisados,
        "total_jogos": total_jogos,
        "melhor_resultado": melhor_resultado,
        "jogos_3_mais": jogos_3_mais,
        "jogos_4_mais": jogos_4_mais,
        "jogos_5_mais": jogos_5_mais,
        "jogos_6": jogos_6,
        "taxa_3_mais": round((jogos_3_mais / total_jogos * 100) if total_jogos else 0.0, 2),
        "taxa_4_mais": round((jogos_4_mais / total_jogos * 100) if total_jogos else 0.0, 2),
        "taxa_5_mais": round((jogos_5_mais / total_jogos * 100) if total_jogos else 0.0, 2),
        "taxa_6": round((jogos_6 / total_jogos * 100) if total_jogos else 0.0, 2),
    }


def analisar_frequencia_geral(df: pd.DataFrame) -> pd.DataFrame:
    return _frequencia_janela(df, None, "Frequência geral").sort_values(
        ["Frequência geral", "Dezena"],
        ascending=[False, True],
    ).reset_index(drop=True)


def analisar_frequencia_recente(df: pd.DataFrame, quantidade_concursos: int = 50) -> pd.DataFrame:
    return _frequencia_janela(df, int(quantidade_concursos), "Frequência recente").sort_values(
        ["Frequência recente", "Dezena"],
        ascending=[False, True],
    ).reset_index(drop=True)


def analisar_atraso(df: pd.DataFrame) -> pd.DataFrame:
    return dezenas_atrasadas(df)


def analisar_regularidade(df: pd.DataFrame) -> pd.DataFrame:
    registros = [
        {"Dezena": dezena, "Dezena formatada": f"{dezena:02d}", "Regularidade": _regularidade_dezena(df, dezena)}
        for dezena in range(1, 61)
    ]
    return pd.DataFrame(registros).sort_values(
        ["Regularidade", "Dezena"],
        ascending=[False, True],
    ).reset_index(drop=True)


def analisar_correlacao_dezenas(df: pd.DataFrame) -> pd.DataFrame:
    mapa_pares, _mapa_trincas = _mapas_correlacao(df)
    registros = [
        {"Dezena A": par[0], "Dezena B": par[1], "Frequência conjunta": frequencia}
        for par, frequencia in sorted(mapa_pares.items())
    ]
    return pd.DataFrame(registros)


def aplicar_aprendizado_historico(
    df: pd.DataFrame,
    quantidade_concursos: int = 100,
    quantidade_candidatos: int = 2000,
    top: int = 20,
) -> dict:
    return analisar_padroes_vencedores(
        df,
        quantidade_concursos=quantidade_concursos,
        quantidade_candidatos=quantidade_candidatos,
        top=top,
    )


def jogo_existe_no_historico(df: pd.DataFrame, jogo: list[int] | tuple[int, ...]) -> bool:
    return tuple(sorted(int(dezena) for dezena in jogo)) in _jogos_sorteados(df)


def aplicar_filtros_estatisticos(
    df: pd.DataFrame,
    jogo: list[int] | tuple[int, ...],
    evitar_historico: bool = True,
) -> bool:
    jogos_sorteados = _jogos_sorteados(df) if evitar_historico else set()
    return _jogo_valido_motor_elite(
        sorted(int(dezena) for dezena in jogo),
        jogos_sorteados,
        _dezenas_ultimo_concurso(df),
    )


def pontuar_dezenas_motor_elite_7(df: pd.DataFrame) -> pd.DataFrame:
    _validar_base_motor_elite(df)
    return calcular_score_dezenas(df)


def pontuar_jogo_motor_elite_7(df: pd.DataFrame, jogo: list[int] | tuple[int, ...]) -> dict:
    _validar_base_motor_elite(df)
    jogo_ordenado = sorted(int(dezena) for dezena in jogo)
    if len(jogo_ordenado) != 6 or len(set(jogo_ordenado)) != 6:
        raise ValueError("Informe exatamente 6 dezenas únicas para pontuar um jogo.")
    score_dezenas = calcular_score_dezenas(df)
    mapa_pares, mapa_trincas = _mapas_correlacao(df)
    return _linha_motor_elite(df, score_dezenas, mapa_pares, mapa_trincas, jogo_ordenado)


def gerar_jogos_inteligentes_motor_elite_7(
    df: pd.DataFrame,
    quantidade: int = 10,
    quantidade_candidatos: int = 50000,
) -> pd.DataFrame:
    return gerar_motor_elite_7(
        df,
        quantidade_candidatos=quantidade_candidatos,
        top=quantidade,
    )


def gerar_motor_elite_7(
    df: pd.DataFrame,
    quantidade_candidatos: int = 50000,
    top: int = 50,
) -> pd.DataFrame:
    ranking = gerar_motor_elite_6(
        df,
        quantidade_candidatos=quantidade_candidatos,
        top=top,
    )
    if ranking.empty:
        return ranking
    ranking = ranking.copy()
    ranking.insert(1, "Motor", "Elite 7")
    return ranking


def _resumo_backtest(contagem_acertos: dict[int, int], total_jogos: int, concursos_analisados: int) -> dict:
    melhor_resultado = max((acertos for acertos, total in contagem_acertos.items() if total > 0), default=0)
    resumo = {
        "concursos_analisados": concursos_analisados,
        "total_jogos": total_jogos,
        "melhor_resultado": melhor_resultado,
    }
    for acertos in range(2, 7):
        total_acertos = contagem_acertos.get(acertos, 0)
        resumo[f"jogos_{acertos}"] = total_acertos
        resumo[f"taxa_{acertos}"] = round((total_acertos / total_jogos * 100) if total_jogos else 0.0, 2)
    for piso in range(2, 6):
        total_piso = sum(contagem_acertos.get(acertos, 0) for acertos in range(piso, 7))
        resumo[f"jogos_{piso}_mais"] = total_piso
        resumo[f"taxa_{piso}_mais"] = round((total_piso / total_jogos * 100) if total_jogos else 0.0, 2)
    resumo["jogos_6"] = contagem_acertos.get(6, 0)
    resumo["taxa_6"] = round((contagem_acertos.get(6, 0) / total_jogos * 100) if total_jogos else 0.0, 2)
    return resumo


def backtest_motor_elite_7_por_concurso(
    df: pd.DataFrame,
    concurso: int,
    quantidade_candidatos: int = 5000,
    top: int = 20,
) -> dict:
    _validar_base_motor_elite(df)
    dados = df.sort_values("Concurso", ascending=True).reset_index(drop=True)
    concurso = int(concurso)
    linha_real = dados[dados["Concurso"].astype(int) == concurso]
    if linha_real.empty:
        raise ValueError(f"Concurso {concurso} não encontrado na base histórica.")

    historico = dados[dados["Concurso"].astype(int) < concurso]
    if historico.empty:
        raise ValueError(f"Concurso {concurso} não possui histórico anterior para backtest.")

    ranking = gerar_motor_elite_7(
        historico,
        quantidade_candidatos=quantidade_candidatos,
        top=top,
    )
    resultado_real = {int(linha_real.iloc[0][coluna]) for coluna in COLUNAS_DEZENAS}
    detalhes = []
    contagem_acertos = {acertos: 0 for acertos in range(7)}
    for _, linha in ranking.iterrows():
        jogo = _parse_jogo_formatado(str(linha["Jogo"]))
        acertos = len(set(jogo) & resultado_real)
        contagem_acertos[acertos] += 1
        registro = linha.to_dict()
        registro["Concurso"] = concurso
        registro["Resultado Real"] = " - ".join(f"{dezena:02d}" for dezena in sorted(resultado_real))
        registro["Acertos"] = acertos
        detalhes.append(registro)

    detalhes_df = pd.DataFrame(detalhes)
    resumo = _resumo_backtest(contagem_acertos, len(detalhes), 1 if detalhes else 0)
    return {"resumo": resumo, "detalhes": detalhes_df, "ranking": ranking}


def backtest_motor_elite_7_completo(
    df: pd.DataFrame,
    quantidade_concursos: int = 100,
    quantidade_candidatos: int = 5000,
    top: int = 20,
) -> dict:
    _validar_base_motor_elite(df)
    dados = df.sort_values("Concurso", ascending=True).reset_index(drop=True)
    quantidade_concursos = max(1, min(int(quantidade_concursos), len(dados)))
    concursos_teste = dados.tail(quantidade_concursos)
    detalhes = []
    contagem_acertos = {acertos: 0 for acertos in range(7)}
    concursos_analisados = 0
    total_jogos = 0

    for _, concurso_real in concursos_teste.iterrows():
        concurso = int(concurso_real["Concurso"])
        historico = dados[dados["Concurso"].astype(int) < concurso]
        if historico.empty:
            continue

        ranking = gerar_motor_elite_7(
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
            total_jogos += 1
            registro = linha.to_dict()
            registro["Concurso"] = concurso
            registro["Resultado Real"] = " - ".join(f"{dezena:02d}" for dezena in sorted(resultado_real))
            registro["Acertos"] = acertos
            detalhes.append(registro)

    detalhes_df = pd.DataFrame(detalhes)
    resumo = _resumo_backtest(contagem_acertos, total_jogos, concursos_analisados)
    ranking_acertos = (
        detalhes_df.sort_values(["Acertos", "Score Elite"], ascending=[False, False]).reset_index(drop=True)
        if not detalhes_df.empty
        else pd.DataFrame()
    )
    return {"resumo": resumo, "detalhes": detalhes_df, "ranking": ranking_acertos}


def exportar_resultados_backtest(resultado: dict) -> bytes:
    detalhes = resultado.get("detalhes", pd.DataFrame())
    if not isinstance(detalhes, pd.DataFrame):
        detalhes = pd.DataFrame(detalhes)
    return detalhes.to_csv(index=False).encode("utf-8-sig")


def validar_motor_elite_7(
    df: pd.DataFrame,
    quantidade_concursos: int = 100,
    quantidade_candidatos: int = 50000,
    top: int = 50,
) -> dict:
    resultado = backtest_motor_elite_7_completo(
        df,
        quantidade_concursos=quantidade_concursos,
        quantidade_candidatos=quantidade_candidatos,
        top=top,
    )
    return resultado["resumo"]


def testar_motor_elite_7_basico(df: pd.DataFrame) -> dict:
    resultado = testar_motor_elite_6_basico(df)
    resultado["motor_elite_7"] = True
    return resultado


def testar_motor_elite_6_basico(df: pd.DataFrame) -> dict:
    resultado = {
        "base_carregada": False,
        "jogos_gerados": False,
        "scores_validos": False,
        "sem_duplicidade": False,
        "formato_saida": False,
    }
    _validar_base_motor_elite(df)
    resultado["base_carregada"] = True

    ranking = gerar_motor_elite_6(df, quantidade_candidatos=100, top=10)
    resultado["jogos_gerados"] = not ranking.empty
    if ranking.empty:
        return resultado

    jogos = ranking["Jogo"].astype(str).tolist()
    resultado["sem_duplicidade"] = len(jogos) == len(set(jogos))
    resultado["scores_validos"] = bool(ranking["Score Final"].between(0, 100).all())

    def jogo_formatado_valido(valor: str) -> bool:
        dezenas = _parse_jogo_formatado(valor)
        return (
            len(dezenas) == 6
            and len(set(dezenas)) == 6
            and dezenas == sorted(dezenas)
            and all(1 <= dezena <= 60 for dezena in dezenas)
        )

    colunas_obrigatorias = {"Ranking", "Jogo", "Score Final", "Classificacao", "Justificativa"}
    resultado["formato_saida"] = (
        colunas_obrigatorias.issubset(set(ranking.columns))
        and all(jogo_formatado_valido(jogo) for jogo in jogos)
    )
    return resultado


def analisar_padroes_vencedores(
    df: pd.DataFrame,
    quantidade_concursos: int = 100,
    quantidade_candidatos: int = 5000,
    top: int = 20,
) -> dict:
    dados = df.sort_values("Concurso", ascending=True).reset_index(drop=True)
    quantidade_concursos = max(1, min(int(quantidade_concursos), len(dados)))
    quantidade_candidatos = max(1, int(quantidade_candidatos))
    top = max(1, min(int(top), quantidade_candidatos))
    concursos_teste = dados.tail(quantidade_concursos)
    faixas_nomes = FAIXAS_APRENDIZADO
    registros: list[dict[str, float]] = []

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
        for _, linha in ranking.iterrows():
            jogo = _parse_jogo_formatado(str(linha["Jogo"]))
            acertos = len(set(jogo) & resultado_real)
            if acertos not in {3, 4, 5}:
                continue

            distribuicao = _distribuicao_faixas(jogo)
            pares = sum(dezena % 2 == 0 for dezena in jogo)
            registro = {
                "soma": float(sum(jogo)),
                "pares": float(pares),
                "impares": float(6 - pares),
                "score_base": float(linha.get("Score Base", 0.0)),
                "score_correlacao": float(linha.get("Score Correlação", 0.0)),
                "score_final": float(linha.get("Score Final", linha.get("Score", 0.0))),
            }
            for indice, nome in enumerate(faixas_nomes):
                registro[f"faixa_{nome}"] = float(distribuicao.get(indice, 0))
            registros.append(registro)

    jogos_analisados = len(registros)
    if jogos_analisados == 0:
        return _registrar_aprendizado_historico({
            "jogos_analisados": 0,
            "media_soma": 0.0,
            "media_pares": 0.0,
            "media_impares": 0.0,
            "media_score_base": 0.0,
            "media_score_correlacao": 0.0,
            "media_score_final": 0.0,
            "faixas_medias": {nome: 0.0 for nome in faixas_nomes},
        })

    def media(campo: str) -> float:
        return round(sum(registro[campo] for registro in registros) / jogos_analisados, 2)

    return _registrar_aprendizado_historico({
        "jogos_analisados": jogos_analisados,
        "media_soma": media("soma"),
        "media_pares": media("pares"),
        "media_impares": media("impares"),
        "media_score_base": media("score_base"),
        "media_score_correlacao": media("score_correlacao"),
        "media_score_final": media("score_final"),
        "faixas_medias": {
            nome: media(f"faixa_{nome}")
            for nome in faixas_nomes
        },
    })


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

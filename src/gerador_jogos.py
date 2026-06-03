from __future__ import annotations

import random

import pandas as pd

from src.carregar_dados import COLUNAS_DEZENAS
from src.estatisticas import dezenas_atrasadas, frequencia_dezenas, ultimos_concursos


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


def _normalizar_serie(serie: pd.Series) -> pd.Series:
    maior = float(serie.max())
    if maior <= 0:
        return pd.Series([0.0] * len(serie), index=serie.index)
    return (serie.astype(float) / maior) * 100


def calcular_score_dezenas(df: pd.DataFrame) -> pd.DataFrame:
    frequencia_geral = frequencia_dezenas(df).rename(
        columns={"Frequência": "Frequência geral"}
    )
    frequencia_20 = frequencia_dezenas(ultimos_concursos(df, 20)).rename(
        columns={"Frequência": "Frequência últimos 20"}
    )
    frequencia_50 = frequencia_dezenas(ultimos_concursos(df, 50)).rename(
        columns={"Frequência": "Frequência últimos 50"}
    )
    atrasadas = dezenas_atrasadas(df)[["Dezena", "Atraso"]]

    score = frequencia_geral[["Dezena", "Dezena formatada", "Frequência geral"]]
    score = score.merge(frequencia_20[["Dezena", "Frequência últimos 20"]], on="Dezena")
    score = score.merge(frequencia_50[["Dezena", "Frequência últimos 50"]], on="Dezena")
    score = score.merge(atrasadas, on="Dezena")

    freq_geral_norm = _normalizar_serie(score["Frequência geral"])
    freq_20_norm = _normalizar_serie(score["Frequência últimos 20"])
    freq_50_norm = _normalizar_serie(score["Frequência últimos 50"])
    atraso_norm = _normalizar_serie(score["Atraso"])
    equilibrio_norm = 100 - (freq_50_norm - atraso_norm).abs()

    score["Score"] = (
        (freq_geral_norm * 0.25)
        + (freq_20_norm * 0.25)
        + (freq_50_norm * 0.20)
        + (atraso_norm * 0.15)
        + (equilibrio_norm * 0.15)
    ).round(2)

    return score.sort_values(["Score", "Dezena"], ascending=[False, True]).reset_index(drop=True)


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


def _jogo_valido(
    df: pd.DataFrame,
    jogo: list[int],
    jogos_sorteados: set[tuple[int, ...]],
    exigir_tres_pares: bool,
) -> bool:
    pares = sum(dezena % 2 == 0 for dezena in jogo)
    soma = sum(jogo)

    if exigir_tres_pares and pares != 3:
        return False
    if not exigir_tres_pares and pares not in {2, 3, 4}:
        return False
    if soma < 150 or soma > 220:
        return False
    if _tem_mais_de_duas_consecutivas(jogo):
        return False
    return tuple(jogo) not in jogos_sorteados


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

    for exigir_tres_pares in (True, False):
        for _ in range(5000):
            jogo = _sortear_dezenas_ponderadas(score)
            if _jogo_valido(df, jogo, jogos_sorteados, exigir_tres_pares):
                return jogo

    dezenas_ordenadas = score["Dezena"].astype(int).tolist()
    for inicio in range(0, len(dezenas_ordenadas) - 5):
        jogo = sorted(dezenas_ordenadas[inicio : inicio + 6])
        if _jogo_valido(df, jogo, jogos_sorteados, exigir_tres_pares=False):
            return jogo

    return sorted(dezenas_ordenadas[:6])


def gerar_varios_jogos_inteligentes(df: pd.DataFrame, quantidade: int = 5) -> list[list[int]]:
    jogos: list[list[int]] = []
    combinacoes: set[tuple[int, ...]] = set()
    tentativas = 0

    while len(jogos) < quantidade and tentativas < quantidade * 1000:
        jogo = gerar_jogo_inteligente(df)
        combinacao = tuple(jogo)
        if combinacao not in combinacoes:
            jogos.append(jogo)
            combinacoes.add(combinacao)
        tentativas += 1

    return jogos


def score_jogo(df: pd.DataFrame, jogo: list[int]) -> float:
    score = calcular_score_dezenas(df).set_index("Dezena")
    scores = [float(score.loc[int(dezena), "Score"]) for dezena in jogo]
    return round(sum(scores) / len(scores), 2)


def _formatar_dezenas(dezenas: list[int] | set[int]) -> str:
    return " - ".join(f"{int(dezena):02d}" for dezena in sorted(dezenas))


def _simular_backtest_historico(df: pd.DataFrame, quantidade_concursos: int = 500) -> pd.DataFrame:
    dados = df.sort_values("Concurso", ascending=True).reset_index(drop=True)
    quantidade_teste = min(int(quantidade_concursos), len(dados))
    concursos_teste = dados.tail(quantidade_teste)
    registros = []

    for _, concurso_real in concursos_teste.iterrows():
        concurso = int(concurso_real["Concurso"])
        historico = dados[dados["Concurso"].astype(int) < concurso]
        if historico.empty:
            continue

        jogo = gerar_jogo_inteligente(historico)
        resultado_real = {int(concurso_real[coluna]) for coluna in COLUNAS_DEZENAS}
        acertos = len(set(jogo) & resultado_real)
        registros.append(
            {
                "Concurso": concurso,
                "Data": concurso_real["Data"],
                "Jogo gerado": _formatar_dezenas(jogo),
                "Resultado oficial": _formatar_dezenas(resultado_real),
                "Acertos": acertos,
                "Score do jogo": score_jogo(historico, jogo),
            }
        )

    return pd.DataFrame(
        registros,
        columns=["Concurso", "Data", "Jogo gerado", "Resultado oficial", "Acertos", "Score do jogo"],
    )


def validar_algoritmo_historico(df: pd.DataFrame, quantidade_concursos: int = 500) -> dict:
    simulacao = _simular_backtest_historico(df, quantidade_concursos)
    total_jogos = int(len(simulacao))
    contagem = simulacao["Acertos"].value_counts().to_dict() if total_jogos else {}
    resultados = {acertos: int(contagem.get(acertos, 0)) for acertos in range(7)}
    melhor_resultado = int(simulacao["Acertos"].max()) if total_jogos else 0
    jogos_3_mais = sum(resultados[acertos] for acertos in range(3, 7))
    jogos_4_mais = sum(resultados[acertos] for acertos in range(4, 7))

    return {
        "concursos analisados": total_jogos,
        "total de jogos simulados": total_jogos,
        "quantidade de 0 acertos": resultados[0],
        "quantidade de 1 acerto": resultados[1],
        "quantidade de 2 acertos": resultados[2],
        "quantidade de 3 acertos": resultados[3],
        "quantidade de 4 acertos": resultados[4],
        "quantidade de 5 acertos": resultados[5],
        "quantidade de 6 acertos": resultados[6],
        "melhor resultado": melhor_resultado,
        "taxa de jogos com 3+ acertos": round((jogos_3_mais / total_jogos * 100) if total_jogos else 0.0, 2),
        "taxa de jogos com 4+ acertos": round((jogos_4_mais / total_jogos * 100) if total_jogos else 0.0, 2),
    }


def backtest_completo(df: pd.DataFrame, quantidade_concursos: int = 500) -> pd.DataFrame:
    simulacao = _simular_backtest_historico(df, quantidade_concursos)
    if simulacao.empty:
        return simulacao
    return simulacao.sort_values(["Acertos", "Concurso"], ascending=[False, False]).head(20).reset_index(drop=True)


def dados_grafico_backtest(df: pd.DataFrame, quantidade_concursos: int = 500) -> pd.DataFrame:
    simulacao = _simular_backtest_historico(df, quantidade_concursos)
    if simulacao.empty:
        return pd.DataFrame(columns=["Concurso", "Data", "Acertos"])
    return simulacao[["Concurso", "Data", "Acertos"]].sort_values("Concurso").reset_index(drop=True)

from __future__ import annotations

from collections import Counter
from itertools import combinations
import random

import pandas as pd

from src.carregar_dados import COLUNAS_DEZENAS
from src.estatisticas import dezenas_atrasadas, frequencia_dezenas, ultimos_concursos


def _coluna_frequencia(df: pd.DataFrame) -> str:
    for coluna in df.columns:
        if str(coluna).lower().startswith("frequ"):
            return str(coluna)
    raise ValueError("Coluna de frequencia nao encontrada.")


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


def _classificar_tendencia(score: float) -> str:
    if score >= 70:
        return "Quente"
    if score <= 45:
        return "Fria"
    return "Neutra"


def _padrao_par_impar_por_dezena(df: pd.DataFrame, dezena: int) -> float:
    pares_historicos = df[COLUNAS_DEZENAS].apply(
        lambda linha: int(sum(int(valor) % 2 == 0 for valor in linha)),
        axis=1,
    )
    media_pares = float(pares_historicos.mean()) if not pares_historicos.empty else 3.0
    if int(dezena) % 2 == 0:
        return (media_pares / 6) * 100
    return ((6 - media_pares) / 6) * 100


def _padrao_soma_por_dezena(df: pd.DataFrame, dezena: int) -> float:
    soma_media = float(df[COLUNAS_DEZENAS].sum(axis=1).mean()) if not df.empty else 183.0
    dezena_media_esperada = soma_media / 6
    distancia_maxima = max(abs(1 - dezena_media_esperada), abs(60 - dezena_media_esperada), 1)
    score = 100 - ((abs(float(dezena) - dezena_media_esperada) / distancia_maxima) * 100)
    return max(0.0, min(100.0, score))


def calcular_score_dezenas(df: pd.DataFrame) -> pd.DataFrame:
    frequencia_geral = _frequencia_janela(df, None, "Frequencia geral")
    frequencia_50 = _frequencia_janela(df, 50, "Frequencia ultimos 50")
    frequencia_20 = _frequencia_janela(df, 20, "Frequencia ultimos 20")
    atrasadas = dezenas_atrasadas(df)[["Dezena", "Atraso"]]

    score = frequencia_geral[["Dezena", "Dezena formatada", "Frequencia geral"]].copy()
    score = score.merge(frequencia_50[["Dezena", "Frequencia ultimos 50"]], on="Dezena")
    score = score.merge(frequencia_20[["Dezena", "Frequencia ultimos 20"]], on="Dezena")
    score = score.merge(atrasadas, on="Dezena")

    freq_geral_norm = _normalizar_serie(score["Frequencia geral"])
    freq_20_norm = _normalizar_serie(score["Frequencia ultimos 20"])
    freq_50_norm = _normalizar_serie(score["Frequencia ultimos 50"])
    atraso_norm = _normalizar_serie(score["Atraso"])
    score["Padrao par impar"] = score["Dezena"].apply(lambda dezena: _padrao_par_impar_por_dezena(df, int(dezena)))
    score["Padrao soma"] = score["Dezena"].apply(lambda dezena: _padrao_soma_por_dezena(df, int(dezena)))

    score["Score"] = (
        (freq_geral_norm * 0.20)
        + (freq_20_norm * 0.25)
        + (freq_50_norm * 0.25)
        + (atraso_norm * 0.15)
        + (score["Padrao par impar"] * 0.05)
        + (score["Padrao soma"] * 0.10)
    ).clip(lower=0, upper=100).round(2)
    score["Tendencia"] = score["Score"].apply(_classificar_tendencia)

    return score.sort_values(["Score", "Dezena"], ascending=[False, True]).reset_index(drop=True)


def _jogos_sorteados(df: pd.DataFrame) -> set[tuple[int, ...]]:
    return {
        tuple(sorted(int(dezena) for dezena in linha))
        for linha in df[COLUNAS_DEZENAS].to_numpy()
    }


def _tem_sequencia_consecutiva(jogo: list[int], tamanho_minimo: int = 4) -> bool:
    sequencia = 1
    for anterior, atual in zip(jogo, jogo[1:]):
        if atual == anterior + 1:
            sequencia += 1
            if sequencia >= tamanho_minimo:
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
    impares = 6 - pares
    soma = sum(jogo)

    if exigir_tres_pares and pares != 3:
        return False
    if pares not in {2, 3, 4} or impares not in {2, 3, 4}:
        return False
    if soma < 120 or soma > 240:
        return False
    if _tem_sequencia_consecutiva(jogo, tamanho_minimo=4):
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


def _gerar_jogo_por_estrategia(df: pd.DataFrame, estrategia: str = "Equilibrado") -> list[int]:
    score = calcular_score_dezenas(df)
    jogos_sorteados = _jogos_sorteados(df)
    configuracoes = {
        "Conservador": [(24, True), (30, True), (36, False)],
        "Equilibrado": [(35, True), (42, False), (50, False)],
        "Agressivo": [(50, False), (60, False)],
    }

    for tamanho_pool, exigir_tres_pares in configuracoes.get(estrategia, configuracoes["Equilibrado"]):
        for _ in range(5000):
            jogo = _sortear_dezenas_ponderadas(score, tamanho_pool=tamanho_pool)
            if _jogo_valido(df, jogo, jogos_sorteados, exigir_tres_pares):
                return jogo

    dezenas_ordenadas = score["Dezena"].astype(int).tolist()
    for inicio in range(0, len(dezenas_ordenadas) - 5):
        jogo = sorted(dezenas_ordenadas[inicio : inicio + 6])
        if _jogo_valido(df, jogo, jogos_sorteados, exigir_tres_pares=False):
            return jogo

    return sorted(dezenas_ordenadas[:6])


def gerar_jogo_inteligente(df: pd.DataFrame) -> list[int]:
    return _gerar_jogo_por_estrategia(df, "Equilibrado")


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


def score_jogo(df: pd.DataFrame, jogo: list[int]) -> float:
    score = calcular_score_dezenas(df).set_index("Dezena")
    scores = [float(score.loc[int(dezena), "Score"]) for dezena in jogo]
    return round(sum(scores) / len(scores), 2)


def classificar_confianca(score: float) -> str:
    if score >= 95:
        return "Elite"
    if score >= 90:
        return "Excelente"
    if score >= 80:
        return "Muito Forte"
    if score >= 70:
        return "Forte"
    if score >= 60:
        return "Moderado"
    return "Fraco"


def _montar_registro_jogo(
    df: pd.DataFrame,
    jogo: list[int],
    indice: int | None = None,
    estrategia: str | None = None,
) -> dict:
    pares = sum(dezena % 2 == 0 for dezena in jogo)
    score = score_jogo(df, jogo)
    registro = {
        "dezenas": jogo,
        "score": score,
        "soma": sum(jogo),
        "pares": pares,
        "impares": 6 - pares,
        "classificacao": classificar_confianca(score),
    }
    if estrategia is not None:
        registro = {"estrategia": estrategia, **registro}
    if indice is not None:
        registro = {"jogo": indice, **registro}
    return registro


def gerar_jogos_premium(df: pd.DataFrame, quantidade: int = 10) -> list[dict]:
    jogos: list[dict] = []
    combinacoes: set[tuple[int, ...]] = set()
    estrategias = ["Conservador", "Equilibrado", "Agressivo"]

    while len(jogos) < quantidade:
        houve_insercao = False
        for estrategia in estrategias:
            jogo = _gerar_jogo_por_estrategia(df, estrategia)
            combinacao = tuple(jogo)
            if combinacao in combinacoes:
                continue
            jogos.append(_montar_registro_jogo(df, jogo, len(jogos) + 1, estrategia))
            combinacoes.add(combinacao)
            houve_insercao = True
            if len(jogos) >= quantidade:
                break
        if not houve_insercao:
            break

    if len(jogos) < quantidade:
        score = calcular_score_dezenas(df)
        dezenas_ordenadas = score["Dezena"].astype(int).tolist()
        jogos_sorteados = _jogos_sorteados(df)
        for inicio in range(0, len(dezenas_ordenadas) - 5):
            jogo = sorted(dezenas_ordenadas[inicio : inicio + 6])
            combinacao = tuple(jogo)
            if combinacao in combinacoes or not _jogo_valido(df, jogo, jogos_sorteados, False):
                continue
            jogos.append(_montar_registro_jogo(df, jogo, len(jogos) + 1, "Equilibrado"))
            combinacoes.add(combinacao)
            if len(jogos) >= quantidade:
                break

    return jogos


def simular_monte_carlo(df: pd.DataFrame, quantidade_simulacoes: int = 10000) -> dict[str, pd.DataFrame]:
    score = calcular_score_dezenas(df)
    jogos_sorteados = _jogos_sorteados(df)
    contagem_dezenas: Counter[int] = Counter()
    contagem_pares: Counter[tuple[int, int]] = Counter()
    contagem_trincas: Counter[tuple[int, int, int]] = Counter()
    simulacoes_validas = 0
    tentativas = 0
    limite_tentativas = int(quantidade_simulacoes) * 20

    while simulacoes_validas < int(quantidade_simulacoes) and tentativas < limite_tentativas:
        jogo = _sortear_dezenas_ponderadas(score, tamanho_pool=45)
        tentativas += 1
        if not _jogo_valido(df, jogo, jogos_sorteados, exigir_tres_pares=False):
            continue

        simulacoes_validas += 1
        contagem_dezenas.update(jogo)
        contagem_pares.update(combinations(jogo, 2))
        contagem_trincas.update(combinations(jogo, 3))

    dezenas = pd.DataFrame(
        [
            {"Dezena": dezena, "Dezena formatada": f"{dezena:02d}", "Ocorrencias": ocorrencias}
            for dezena, ocorrencias in contagem_dezenas.most_common(20)
        ]
    )
    pares = pd.DataFrame(
        [
            {"Par": _formatar_dezenas(list(par)), "Ocorrencias": ocorrencias}
            for par, ocorrencias in contagem_pares.most_common(20)
        ]
    )
    trincas = pd.DataFrame(
        [
            {"Trinca": _formatar_dezenas(list(trinca)), "Ocorrencias": ocorrencias}
            for trinca, ocorrencias in contagem_trincas.most_common(20)
        ]
    )

    return {
        "simulacoes": pd.DataFrame(
            [{"Simulacoes solicitadas": int(quantidade_simulacoes), "Simulacoes validas": simulacoes_validas}]
        ),
        "dezenas": dezenas,
        "pares": pares,
        "trincas": trincas,
    }


def _gerar_jogo_validacao_historica(df: pd.DataFrame) -> list[int]:
    score = calcular_score_dezenas(df)
    dezenas_ordenadas = score["Dezena"].astype(int).tolist()
    jogos_sorteados = _jogos_sorteados(df)

    for tamanho_pool in (18, 24, 30, 36, 42, 60):
        pool = dezenas_ordenadas[:tamanho_pool]
        for inicio in range(0, len(pool) - 5):
            jogo = sorted(pool[inicio : inicio + 6])
            if _jogo_valido(df, jogo, jogos_sorteados, exigir_tres_pares=False):
                return jogo

    return sorted(dezenas_ordenadas[:6])


def _formatar_dezenas(dezenas: list[int] | set[int]) -> str:
    return " - ".join(f"{int(dezena):02d}" for dezena in sorted(dezenas))


def _simular_backtest(df: pd.DataFrame, quantidade_concursos: int = 500) -> pd.DataFrame:
    dados = df.sort_values("Concurso", ascending=True).reset_index(drop=True)
    quantidade_teste = min(int(quantidade_concursos), max(0, len(dados) - 20))
    concursos_teste = dados.tail(quantidade_teste)
    registros = []

    for _, concurso_real in concursos_teste.iterrows():
        concurso = int(concurso_real["Concurso"])
        historico = dados[dados["Concurso"].astype(int) < concurso]
        if len(historico) < 20:
            continue

        jogo = _gerar_jogo_validacao_historica(historico)
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
    simulacao = _simular_backtest(df, quantidade_concursos)
    total_jogos = int(len(simulacao))
    contagem = simulacao["Acertos"].value_counts().to_dict() if total_jogos else {}
    resultados = {acertos: int(contagem.get(acertos, 0)) for acertos in range(0, 7)}
    melhor_resultado = int(simulacao["Acertos"].max()) if total_jogos else 0
    jogos_3_mais = sum(resultados[acertos] for acertos in range(3, 7))
    jogos_4_mais = sum(resultados[acertos] for acertos in range(4, 7))
    taxa_3_mais = (jogos_3_mais / total_jogos * 100) if total_jogos else 0.0
    taxa_4_mais = (jogos_4_mais / total_jogos * 100) if total_jogos else 0.0

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
        "taxa de jogos com 3+ acertos": round(taxa_3_mais, 2),
        "taxa de jogos com 4+ acertos": round(taxa_4_mais, 2),
    }


def backtest_completo(df: pd.DataFrame, quantidade_concursos: int = 500) -> pd.DataFrame:
    simulacao = _simular_backtest(df, quantidade_concursos)
    if simulacao.empty:
        return simulacao
    return simulacao.sort_values(["Acertos", "Concurso"], ascending=[False, False]).head(20).reset_index(drop=True)


def dados_grafico_backtest(df: pd.DataFrame, quantidade_concursos: int = 500) -> pd.DataFrame:
    simulacao = _simular_backtest(df, quantidade_concursos)
    if simulacao.empty:
        return pd.DataFrame(columns=["Concurso", "Data", "Acertos"])
    return simulacao[["Concurso", "Data", "Acertos"]].sort_values("Concurso").reset_index(drop=True)

from __future__ import annotations

from collections import Counter
from itertools import combinations
import random

import pandas as pd

from src.carregar_dados import COLUNAS_DEZENAS
from src.gerador_jogos import (
    analisar_atraso,
    analisar_regularidade,
    calcular_score_dezenas,
    gerar_ranking_melhores_jogos,
    score_jogo,
)


def parse_jogo(valor: object) -> list[int]:
    dezenas = []
    for parte in str(valor).replace(",", "-").split("-"):
        texto = parte.strip()
        if texto.isdigit():
            dezenas.append(int(texto))
    return sorted(dezenas)


def _normalizar_serie(serie: pd.Series, inverter: bool = False) -> pd.Series:
    numeros = pd.to_numeric(serie, errors="coerce").fillna(0.0).astype(float)
    minimo = float(numeros.min())
    maximo = float(numeros.max())
    if maximo == minimo:
        normalizada = pd.Series([50.0] * len(numeros), index=numeros.index)
    else:
        normalizada = (numeros - minimo) / (maximo - minimo) * 100.0
    if inverter:
        return 100.0 - normalizada
    return normalizada


def _coluna_existente(df: pd.DataFrame, *candidatas: str) -> str | None:
    for coluna in candidatas:
        if coluna in df.columns:
            return coluna
    return None


def aprendizado_historico(df: pd.DataFrame) -> dict:
    dados = df.sort_values("Concurso", ascending=False).reset_index(drop=True)
    ultimos_100 = dados.head(100)
    ultimos_500 = dados.head(500)

    def perfil(base: pd.DataFrame) -> dict:
        somas = base[COLUNAS_DEZENAS].sum(axis=1)
        pares = base[COLUNAS_DEZENAS].apply(lambda linha: sum(int(dezena) % 2 == 0 for dezena in linha), axis=1)
        repeticoes = []
        ordenado = base.sort_values("Concurso", ascending=True).reset_index(drop=True)
        for indice in range(1, len(ordenado)):
            atual = {int(ordenado.loc[indice, coluna]) for coluna in COLUNAS_DEZENAS}
            anterior = {int(ordenado.loc[indice - 1, coluna]) for coluna in COLUNAS_DEZENAS}
            repeticoes.append(len(atual & anterior))
        return {
            "Concursos": int(len(base)),
            "Soma media": round(float(somas.mean()) if len(somas) else 0.0, 2),
            "Pares medios": round(float(pares.mean()) if len(pares) else 0.0, 2),
            "Repeticao media": round(float(sum(repeticoes) / len(repeticoes)) if repeticoes else 0.0, 2),
        }

    return {
        "Historico completo": perfil(dados),
        "Ultimos 100": perfil(ultimos_100),
        "Ultimos 500": perfil(ultimos_500),
    }


def correlacao_dezenas(df: pd.DataFrame, limite: int = 100) -> pd.DataFrame:
    contador: Counter[tuple[int, int]] = Counter()
    for _, linha in df.iterrows():
        dezenas = sorted(int(linha[coluna]) for coluna in COLUNAS_DEZENAS)
        contador.update(combinations(dezenas, 2))
    registros = [
        {"Dezena A": par[0], "Dezena B": par[1], "Frequencia conjunta": freq}
        for par, freq in contador.most_common(int(limite))
    ]
    return pd.DataFrame(registros)


def banco_mestre_inteligente(df: pd.DataFrame, tamanho: int = 30) -> pd.DataFrame:
    tamanho = max(6, min(int(tamanho), 60))
    scores = calcular_score_dezenas(df).copy()
    atraso_base = analisar_atraso(df).copy()
    atraso_coluna = _coluna_existente(atraso_base, "Atraso", "Atraso atual")
    if atraso_coluna is None:
        atraso_base["Atraso"] = 0.0
        atraso_coluna = "Atraso"
    atraso = atraso_base[["Dezena", atraso_coluna]].rename(columns={atraso_coluna: "Atraso"}).copy()
    regularidade = analisar_regularidade(df)[["Dezena", "Regularidade"]].copy()
    correlacoes = correlacao_dezenas(df, limite=300)

    for tabela in (scores, atraso, regularidade):
        tabela["Dezena"] = tabela["Dezena"].astype(int)

    for coluna in scores.columns:
        if "Score" in coluna and coluna != "Score":
            scores[coluna] = pd.to_numeric(scores[coluna], errors="coerce").fillna(0.0)

    corr_por_dezena = Counter()
    if not correlacoes.empty:
        for _, linha in correlacoes.iterrows():
            corr_por_dezena[int(linha["Dezena A"])] += int(linha["Frequencia conjunta"])
            corr_por_dezena[int(linha["Dezena B"])] += int(linha["Frequencia conjunta"])

    banco = scores.merge(atraso, on="Dezena", how="left").merge(regularidade, on="Dezena", how="left")
    if "Atraso" not in banco.columns:
        atraso_merge = _coluna_existente(banco, "Atraso_y", "Atraso_x")
        banco["Atraso"] = banco[atraso_merge] if atraso_merge else 0.0
    if "Regularidade" not in banco.columns:
        regularidade_merge = _coluna_existente(banco, "Regularidade_y", "Regularidade_x")
        banco["Regularidade"] = banco[regularidade_merge] if regularidade_merge else 0.0
    banco["Forca correlacao"] = banco["Dezena"].map(lambda dezena: corr_por_dezena[int(dezena)]).astype(float)

    score_coluna = "Score" if "Score" in banco.columns else next((c for c in banco.columns if "Score" in c), None)
    banco["Score base normalizado"] = _normalizar_serie(banco[score_coluna] if score_coluna else banco["Dezena"])
    banco["Score atraso"] = _normalizar_serie(banco["Atraso"].fillna(0.0))
    banco["Score regularidade"] = _normalizar_serie(banco["Regularidade"].fillna(0.0))
    banco["Score correlacao"] = _normalizar_serie(banco["Forca correlacao"].fillna(0.0))
    banco["Score Mestre"] = (
        banco["Score base normalizado"] * 0.42
        + banco["Score correlacao"] * 0.25
        + banco["Score regularidade"] * 0.20
        + banco["Score atraso"] * 0.13
    ).round(2)
    banco = banco.sort_values(["Score Mestre", "Dezena"], ascending=[False, True]).head(tamanho).reset_index(drop=True)
    banco.insert(0, "Ranking", range(1, len(banco) + 1))
    return banco[
        [
            "Ranking",
            "Dezena",
            "Score Mestre",
            "Score base normalizado",
            "Score correlacao",
            "Score regularidade",
            "Score atraso",
            "Atraso",
            "Regularidade",
        ]
    ]


def _score_neural_linha(linha: pd.Series) -> float:
    score_final = float(linha.get("Score Final", linha.get("Score", 0.0)) or 0.0)
    score_base = float(linha.get("Score Base", 0.0) or 0.0)
    score_corr = float(linha.get("Score Correlação", linha.get("Score CorrelaÃ§Ã£o", 0.0)) or 0.0)
    score_div = float(linha.get("Score Diversidade", 0.0) or 0.0)
    score_rep = float(linha.get("Score Repetição", linha.get("Score RepetiÃ§Ã£o", 0.0)) or 0.0)
    soma = float(linha.get("Soma", 0.0) or 0.0)
    pares = float(linha.get("Pares", 0.0) or 0.0)
    equilibrio_soma = max(0.0, 100.0 - abs(soma - 183.0) * 1.2)
    equilibrio_pares = 100.0 if pares == 3 else 82.0 if pares in (2, 4) else 58.0
    neural = (
        score_final * 0.38
        + score_base * 0.16
        + score_corr * 0.14
        + score_div * 0.12
        + score_rep * 0.08
        + equilibrio_soma * 0.07
        + equilibrio_pares * 0.05
    )
    return round(max(0.0, min(100.0, neural)), 2)


def classificar_confianca(score: float) -> str:
    if score >= 88:
        return "Elite"
    if score >= 76:
        return "Alta"
    if score >= 62:
        return "Media"
    return "Baixa"


def gerar_ranking_elite_x_pro(
    df: pd.DataFrame,
    quantidade_candidatos: int = 20000,
    top: int = 1000,
    janela: int | None = None,
) -> pd.DataFrame:
    historico = df.sort_values("Concurso", ascending=False).head(int(janela)) if janela else df
    top = max(1, min(int(top), int(quantidade_candidatos)))
    ranking = gerar_ranking_melhores_jogos(
        historico,
        quantidade_candidatos=int(quantidade_candidatos),
        top=top,
    )
    if ranking.empty:
        return ranking
    ranking = ranking.copy()
    ranking["Score Neural Elite X"] = ranking.apply(_score_neural_linha, axis=1)
    ranking["Confianca"] = ranking["Score Neural Elite X"].map(classificar_confianca)
    ranking["Motor"] = "Elite X PRO"
    ranking = ranking.sort_values(["Score Neural Elite X", "Score Final"], ascending=[False, False]).reset_index(drop=True)
    ranking["Ranking"] = range(1, len(ranking) + 1)
    colunas = ["Ranking", "Motor", "Jogo", "Score Neural Elite X", "Confianca"]
    colunas += [coluna for coluna in ranking.columns if coluna not in colunas]
    return ranking[colunas]


def gerar_bolao_profissional(df: pd.DataFrame, dezenas_banco: int, quantidade_jogos: int = 40) -> dict:
    banco = banco_mestre_inteligente(df, tamanho=dezenas_banco)
    dezenas = sorted(banco["Dezena"].astype(int).tolist())
    quantidade_jogos = max(1, int(quantidade_jogos))
    vistos: set[tuple[int, ...]] = set()
    jogos = []
    tentativas = 0
    limite = quantidade_jogos * 300
    pesos = dict(zip(banco["Dezena"].astype(int), banco["Score Mestre"].astype(float)))

    while len(jogos) < quantidade_jogos and tentativas < limite:
        tentativas += 1
        pool = random.choices(dezenas, weights=[weights for weights in [pesos[d] for d in dezenas]], k=12)
        candidatos = sorted(set(pool))
        while len(candidatos) < 6:
            candidatos.append(random.choice(dezenas))
            candidatos = sorted(set(candidatos))
        jogo = tuple(sorted(random.sample(candidatos, 6)))
        if jogo in vistos:
            continue
        vistos.add(jogo)
        score = score_jogo(df, list(jogo))
        jogos.append(
            {
                "Ranking": len(jogos) + 1,
                "Banco": f"{dezenas_banco} dezenas",
                "Jogo": " - ".join(f"{dezena:02d}" for dezena in jogo),
                "Score Final": score,
                "Score Neural Elite X": round(score * 0.88 + min(100.0, sum(pesos[d] for d in jogo) / 6.0) * 0.12, 2),
                "Confianca": classificar_confianca(score),
                "Soma": sum(jogo),
                "Pares": sum(dezena % 2 == 0 for dezena in jogo),
            }
        )

    jogos_df = pd.DataFrame(jogos).sort_values(["Score Neural Elite X", "Score Final"], ascending=[False, False])
    jogos_df = jogos_df.reset_index(drop=True)
    if not jogos_df.empty:
        jogos_df["Ranking"] = range(1, len(jogos_df) + 1)
    return {"banco": banco, "jogos": jogos_df}


def simular_jogo_unico_20_dezenas(df: pd.DataFrame) -> dict:
    banco = banco_mestre_inteligente(df, tamanho=20)
    dezenas = sorted(banco["Dezena"].astype(int).tolist())
    conjunto = set(dezenas)
    registros = []

    for _, linha in df.sort_values("Concurso", ascending=True).iterrows():
        sorteadas = sorted(int(linha[coluna]) for coluna in COLUNAS_DEZENAS)
        acertadas = sorted(conjunto & set(sorteadas))
        registros.append(
            {
                "Concurso": int(linha["Concurso"]),
                "Data": linha.get("Data", ""),
                "Dezenas sorteadas": " - ".join(f"{dezena:02d}" for dezena in sorteadas),
                "Acertos dentro das 20": len(acertadas),
                "Dezenas acertadas": " - ".join(f"{dezena:02d}" for dezena in acertadas),
            }
        )

    detalhes = pd.DataFrame(registros)
    if detalhes.empty:
        melhor = pd.Series(dtype=object)
        melhor_pico = 0
    else:
        melhor_indice = detalhes["Acertos dentro das 20"].astype(int).idxmax()
        melhor = detalhes.loc[melhor_indice]
        melhor_pico = int(melhor["Acertos dentro das 20"])

    score_final = round(float(banco["Score Mestre"].mean()), 2) if not banco.empty else 0.0
    resumo = {
        "Dezenas geradas": " - ".join(f"{dezena:02d}" for dezena in dezenas),
        "Total de concursos analisados": int(len(detalhes)),
        "Concursos com 6 acertos": int((detalhes["Acertos dentro das 20"] == 6).sum()) if not detalhes.empty else 0,
        "Concursos com 5 acertos": int((detalhes["Acertos dentro das 20"] == 5).sum()) if not detalhes.empty else 0,
        "Concursos com 4 acertos": int((detalhes["Acertos dentro das 20"] == 4).sum()) if not detalhes.empty else 0,
        "Melhor pico de acertos": melhor_pico,
        "Concurso de melhor desempenho": int(melhor.get("Concurso", 0)) if not melhor.empty else 0,
        "Dezenas acertadas no melhor concurso": str(melhor.get("Dezenas acertadas", "")) if not melhor.empty else "",
        "Score final do jogo": score_final,
    }
    return {"dezenas": dezenas, "banco": banco, "detalhes": detalhes, "resumo": resumo}


def dashboard_melhores_jogos(df: pd.DataFrame, candidatos: int = 3000) -> dict[str, pd.Series | None]:
    dados = df.sort_values("Concurso", ascending=False).reset_index(drop=True)
    recortes = {
        "Melhor jogo historico": None,
        "Melhor jogo dos ultimos 100 concursos": 100,
        "Melhor jogo dos ultimos 500 concursos": 500,
    }
    resultado: dict[str, pd.Series | None] = {}
    for nome, janela in recortes.items():
        ranking = gerar_ranking_elite_x_pro(
            dados.head(janela) if janela else dados,
            quantidade_candidatos=candidatos,
            top=1,
        )
        resultado[nome] = ranking.iloc[0] if not ranking.empty else None
    return resultado


def backtest_elite_x_pro(
    df: pd.DataFrame,
    concursos: int = 1000,
    candidatos: int = 300,
    top: int = 10,
) -> dict:
    dados = df.sort_values("Concurso", ascending=True).reset_index(drop=True)
    concursos_teste = dados.tail(min(int(concursos), max(1, len(dados) - 1)))
    detalhes = []
    score_por_concurso = []
    melhor = {"Acertos": -1, "Jogo": "", "Concurso": 0, "Motor": ""}
    candidatos = max(20, int(candidatos))
    top = max(1, int(top))

    def score_rapido(score_dezenas: pd.DataFrame, jogo: list[int]) -> float:
        mapa = dict(zip(score_dezenas["Dezena"].astype(int), pd.to_numeric(score_dezenas["Score"], errors="coerce").fillna(0.0)))
        base = sum(float(mapa.get(dezena, 0.0)) for dezena in jogo) / 6.0
        soma = sum(jogo)
        pares = sum(dezena % 2 == 0 for dezena in jogo)
        equilibrio_soma = max(0.0, 100.0 - abs(soma - 183.0) * 1.2)
        equilibrio_pares = 100.0 if pares == 3 else 82.0 if pares in (2, 4) else 58.0
        return round(max(0.0, min(100.0, base * 0.70 + equilibrio_soma * 0.18 + equilibrio_pares * 0.12)), 2)

    def candidatos_rapidos(score_dezenas: pd.DataFrame, concurso: int, modo: str) -> list[tuple[list[int], float]]:
        ordenadas = score_dezenas["Dezena"].astype(int).tolist()
        if modo == "xpro":
            pool = ordenadas[: min(32, len(ordenadas))]
        else:
            pool = ordenadas[: min(45, len(ordenadas))]
        rng = random.Random(concurso + (17 if modo == "xpro" else 91))
        vistos: set[tuple[int, ...]] = set()
        gerados: list[tuple[list[int], float]] = []

        for inicio in range(0, max(1, len(pool) - 5)):
            jogo = tuple(sorted(pool[inicio : inicio + 6]))
            if len(jogo) == 6 and len(set(jogo)) == 6:
                vistos.add(jogo)

        tentativas = 0
        while len(vistos) < candidatos and tentativas < candidatos * 20:
            tentativas += 1
            tamanho_pool = min(len(pool), rng.choice([18, 22, 26, 30, len(pool)]))
            jogo = tuple(sorted(rng.sample(pool[:tamanho_pool], 6)))
            vistos.add(jogo)

        for jogo in vistos:
            score = score_rapido(score_dezenas, list(jogo))
            if modo == "xpro":
                score = round(min(100.0, score * 1.03), 2)
            gerados.append((list(jogo), score))
        return sorted(gerados, key=lambda item: item[1], reverse=True)[:top]

    def registrar(motor: str, concurso: int, jogo: list[int], score: float, real: set[int]) -> None:
        acertos = len(set(jogo) & real)
        registro = {
            "Motor": motor,
            "Concurso": concurso,
            "Jogo": " - ".join(f"{dezena:02d}" for dezena in jogo),
            "Resultado": " - ".join(f"{dezena:02d}" for dezena in sorted(real)),
            "Acertos": acertos,
            "Score": round(float(score), 2),
        }
        detalhes.append(registro)
        if acertos > melhor["Acertos"] or (acertos == melhor["Acertos"] and score > melhor.get("Score", 0)):
            melhor.update(registro)

    for _, concurso_real in concursos_teste.iterrows():
        concurso = int(concurso_real["Concurso"])
        historico = dados[dados["Concurso"].astype(int) < concurso]
        if len(historico) < 50:
            continue
        real = {int(concurso_real[coluna]) for coluna in COLUNAS_DEZENAS}
        score_dezenas = calcular_score_dezenas(historico)

        jogos_x = candidatos_rapidos(score_dezenas, concurso, "xpro")
        for jogo_x, score_x in jogos_x:
            registrar("Elite X PRO", concurso, jogo_x, score_x, real)
        if jogos_x:
            scores_x = [score for _jogo, score in jogos_x]
            score_por_concurso.append(
                {
                    "Concurso": concurso,
                    "Score medio Elite X PRO": round(sum(scores_x) / len(scores_x), 2),
                    "Melhor score Elite X PRO": round(max(scores_x), 2),
                }
            )

        for jogo_9, score_9 in candidatos_rapidos(score_dezenas, concurso, "elite9"):
            registrar("Elite 9", concurso, jogo_9, score_9, real)

    detalhes_df = pd.DataFrame(detalhes)
    evolucao_df = pd.DataFrame(score_por_concurso)
    if detalhes_df.empty:
        resumo = pd.DataFrame()
    else:
        resumo = detalhes_df.groupby("Motor", as_index=False).agg(
            Concursos=("Concurso", "nunique"),
            Jogos=("Jogo", "count"),
            Media_acertos=("Acertos", "mean"),
            Melhor_acerto=("Acertos", "max"),
            Taxa_3_mais=("Acertos", lambda s: round(float((s >= 3).mean() * 100), 2)),
            Taxa_4_mais=("Acertos", lambda s: round(float((s >= 4).mean() * 100), 2)),
            Taxa_5_mais=("Acertos", lambda s: round(float((s >= 5).mean() * 100), 2)),
            Score_medio=("Score", "mean"),
        )
        resumo["Media_acertos"] = resumo["Media_acertos"].round(4)
        resumo["Score_medio"] = resumo["Score_medio"].round(2)

    return {
        "resumo": resumo,
        "detalhes": detalhes_df,
        "evolucao": evolucao_df,
        "melhor": melhor if melhor["Acertos"] >= 0 else {},
    }

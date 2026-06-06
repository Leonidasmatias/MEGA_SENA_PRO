from __future__ import annotations

from pathlib import Path
import random

import pandas as pd

from src.auditoria_elite8 import formatar_jogo, gerar_jogos_aleatorios, parse_jogo
from src.carregar_dados import COLUNAS_DEZENAS, carregar_base
from src.elite8_cobertura import gerar_portfolio_elite8_completo
from src.elite9_motor import PONTOS_PREMIACAO, gerar_portfolio_elite9
from src.gerador_jogos import gerar_motor_elite_7


def _medir(
    concurso: int,
    motor: str,
    jogos: list[list[int]],
    resultado_real: set[int],
) -> dict:
    contagem = {acertos: 0 for acertos in range(7)}
    total_acertos = 0
    score_premiacao = 0
    melhor_acerto = 0
    melhor_jogo: list[int] = []
    for jogo in jogos:
        acertos = len(set(jogo) & resultado_real)
        contagem[acertos] += 1
        total_acertos += acertos
        score_premiacao += PONTOS_PREMIACAO.get(acertos, 0)
        if acertos > melhor_acerto:
            melhor_acerto = acertos
            melhor_jogo = jogo

    total_jogos = len(jogos)
    linha = {
        "Concurso": concurso,
        "Motor": motor,
        "Jogos": total_jogos,
        "Total de acertos": total_acertos,
        "Media de acertos por jogo": round(total_acertos / total_jogos, 6) if total_jogos else 0.0,
        "Melhor acerto": melhor_acerto,
        "Melhor jogo": formatar_jogo(melhor_jogo),
        "Resultado real": formatar_jogo(resultado_real),
        "Score total premiacao": score_premiacao,
        "Score medio premiacao por jogo": round(score_premiacao / total_jogos, 6) if total_jogos else 0.0,
    }
    for acertos in range(2, 7):
        quantidade = contagem[acertos]
        linha[f"Jogos com {acertos} acertos"] = quantidade
        linha[f"Taxa {acertos} acertos (%)"] = round((quantidade / total_jogos * 100) if total_jogos else 0.0, 6)
    return linha


def resumir_auditoria_elite9(detalhes: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for motor, grupo in detalhes.groupby("Motor", sort=False):
        total_jogos = int(grupo["Jogos"].sum())
        total_acertos = int(grupo["Total de acertos"].sum())
        total_premiacao = int(grupo["Score total premiacao"].sum())
        melhor_idx = grupo["Melhor acerto"].astype(int).idxmax()
        linha = {
            "Motor": motor,
            "Concursos analisados": int(grupo["Concurso"].nunique()),
            "Total de jogos": total_jogos,
            "Total de acertos": total_acertos,
            "Media de acertos por jogo": round(total_acertos / total_jogos, 6) if total_jogos else 0.0,
            "Melhor acerto": int(grupo.loc[melhor_idx, "Melhor acerto"]),
            "Melhor jogo": grupo.loc[melhor_idx, "Melhor jogo"],
            "Concurso do melhor jogo": int(grupo.loc[melhor_idx, "Concurso"]),
            "Score total premiacao": total_premiacao,
            "Score medio premiacao por jogo": round(total_premiacao / total_jogos, 6) if total_jogos else 0.0,
        }
        for acertos in range(2, 7):
            coluna = f"Jogos com {acertos} acertos"
            quantidade = int(grupo[coluna].sum())
            linha[coluna] = quantidade
            linha[f"Taxa {acertos} acertos (%)"] = round((quantidade / total_jogos * 100) if total_jogos else 0.0, 6)
        linhas.append(linha)

    resumo = pd.DataFrame(linhas)
    if resumo.empty:
        return resumo
    vencedor_media = resumo.loc[resumo["Media de acertos por jogo"].idxmax(), "Motor"]
    vencedor_pico = resumo.loc[resumo["Melhor acerto"].idxmax(), "Motor"]
    vencedor_premiacao = resumo.loc[resumo["Score total premiacao"].idxmax(), "Motor"]
    resumo["Conclusao media"] = f"{vencedor_media} venceu na media de acertos."
    resumo["Conclusao pico"] = f"{vencedor_pico} teve o melhor pico de acertos."
    resumo["Conclusao premiacao"] = f"{vencedor_premiacao} venceu no score total de premiacao."
    return resumo


def executar_auditoria_elite9(
    quantidade_concursos: int = 1000,
    jogos_por_concurso: int = 100,
    candidatos_elite7: int = 100,
    candidatos_elite9: int = 20000,
    geracoes_elite9: int = 8,
    populacao_elite9: int = 200,
    taxa_mutacao_elite9: float = 0.12,
    seed: int = 20260604,
    export_dir: str | Path = "exports",
    incluir_elite7: bool = True,
    incluir_elite8: bool = True,
    log_progresso: bool = True,
) -> dict[str, pd.DataFrame | Path]:
    rng = random.Random(seed)
    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)
    df = carregar_base().sort_values("Concurso", ascending=True).reset_index(drop=True)
    concursos = df.tail(max(1, min(int(quantidade_concursos), len(df))))
    registros: list[dict] = []

    portfolio_elite8 = gerar_portfolio_elite8_completo(quantidade_candidatos=100000, seed=8) if incluir_elite8 else pd.DataFrame()
    jogos_elite8 = [parse_jogo(jogo) for jogo in portfolio_elite8.get("Jogo", pd.Series(dtype=str)).astype(str).head(jogos_por_concurso)]

    for posicao, (_, concurso_real) in enumerate(concursos.iterrows(), start=1):
        concurso = int(concurso_real["Concurso"])
        historico = df[df["Concurso"].astype(int) < concurso]
        resultado_real = {int(concurso_real[coluna]) for coluna in COLUNAS_DEZENAS}
        jogos_aleatorios = gerar_jogos_aleatorios(jogos_por_concurso, rng)
        registros.append(_medir(concurso, "Aleatorio", jogos_aleatorios, resultado_real))

        if incluir_elite7:
            ranking_elite7 = gerar_motor_elite_7(historico, quantidade_candidatos=candidatos_elite7, top=jogos_por_concurso)
            jogos_elite7 = [parse_jogo(jogo) for jogo in ranking_elite7["Jogo"].astype(str).tolist()]
            registros.append(_medir(concurso, "Motor Elite 7", jogos_elite7, resultado_real))

        if incluir_elite8:
            registros.append(_medir(concurso, "Motor Elite 8", jogos_elite8, resultado_real))

        portfolio_elite9 = gerar_portfolio_elite9(
            historico,
            quantidade_candidatos=candidatos_elite9,
            geracoes=geracoes_elite9,
            tamanho_populacao=populacao_elite9,
            taxa_mutacao=taxa_mutacao_elite9,
            quantidade_final=jogos_por_concurso,
            seed=seed + concurso,
        )
        jogos_elite9 = [parse_jogo(jogo) for jogo in portfolio_elite9["Jogo"].astype(str).tolist()]
        registros.append(_medir(concurso, "Motor Elite 9", jogos_elite9, resultado_real))

        if log_progresso and (posicao == 1 or posicao % 25 == 0):
            print(f"progresso={posicao}/{len(concursos)}", flush=True)

    detalhes = pd.DataFrame(registros)
    resumo = resumir_auditoria_elite9(detalhes)
    sufixo = f"{len(concursos)}_{jogos_por_concurso}"
    caminho_detalhes = export_path / f"auditoria_elite9_{sufixo}_detalhada.csv"
    caminho_resumo = export_path / f"auditoria_elite9_{sufixo}_resumo.csv"
    detalhes.to_csv(caminho_detalhes, index=False, encoding="utf-8-sig")
    resumo.to_csv(caminho_resumo, index=False, encoding="utf-8-sig")
    return {"detalhes": detalhes, "resumo": resumo, "caminho_detalhes": caminho_detalhes, "caminho_resumo": caminho_resumo}


if __name__ == "__main__":
    resultado = executar_auditoria_elite9()
    print(resultado["resumo"].to_string(index=False))
    print(f"RESUMO={Path(resultado['caminho_resumo']).resolve()}")
    print(f"DETALHES={Path(resultado['caminho_detalhes']).resolve()}")

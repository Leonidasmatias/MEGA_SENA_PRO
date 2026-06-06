from __future__ import annotations

from pathlib import Path
import random
import time

import pandas as pd

from src.carregar_dados import COLUNAS_DEZENAS, carregar_base
from src.elite8_cobertura import gerar_portfolio_elite8_completo
from src.gerador_jogos import gerar_motor_elite_7


def parse_jogo(valor: str) -> list[int]:
    return [int(parte.strip()) for parte in str(valor).split("-") if parte.strip()]


def formatar_jogo(jogo: list[int] | set[int]) -> str:
    return " - ".join(f"{dezena:02d}" for dezena in sorted(int(dezena) for dezena in jogo))


def gerar_jogos_aleatorios(quantidade: int, rng: random.Random) -> list[list[int]]:
    return [sorted(rng.sample(range(1, 61), 6)) for _ in range(int(quantidade))]


def medir_jogos(
    concurso: int,
    motor: str,
    jogos: list[list[int]],
    resultado_real: set[int],
) -> dict:
    contagem = {acertos: 0 for acertos in range(7)}
    total_acertos = 0
    melhor_acerto = 0
    melhor_jogo: list[int] = []
    for jogo in jogos:
        acertos = len(set(jogo) & resultado_real)
        contagem[acertos] += 1
        total_acertos += acertos
        if acertos > melhor_acerto:
            melhor_acerto = acertos
            melhor_jogo = jogo

    total_jogos = len(jogos)
    linha = {
        "Concurso": int(concurso),
        "Motor": motor,
        "Jogos": total_jogos,
        "Total de acertos": total_acertos,
        "Media de acertos por jogo": round(total_acertos / total_jogos, 6) if total_jogos else 0.0,
        "Melhor acerto": melhor_acerto,
        "Melhor jogo": formatar_jogo(melhor_jogo),
        "Resultado real": formatar_jogo(resultado_real),
    }
    for acertos in range(2, 7):
        quantidade = contagem[acertos]
        linha[f"Jogos com {acertos} acertos"] = quantidade
        linha[f"Taxa {acertos} acertos (%)"] = round((quantidade / total_jogos * 100) if total_jogos else 0.0, 6)
    return linha


def resumir_auditoria(detalhes: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for motor, grupo in detalhes.groupby("Motor", sort=False):
        total_jogos = int(grupo["Jogos"].sum())
        total_acertos = int(grupo["Total de acertos"].sum())
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
        }
        for acertos in range(2, 7):
            coluna = f"Jogos com {acertos} acertos"
            quantidade = int(grupo[coluna].sum())
            linha[coluna] = quantidade
            linha[f"Taxa {acertos} acertos (%)"] = round((quantidade / total_jogos * 100) if total_jogos else 0.0, 6)
        linhas.append(linha)

    resumo = pd.DataFrame(linhas)
    if not resumo.empty:
        melhor_media = resumo["Media de acertos por jogo"].max()
        vencedor = resumo.loc[resumo["Media de acertos por jogo"].idxmax(), "Motor"]
        resumo["Conclusao automatica"] = resumo["Motor"].apply(
            lambda motor: (
                f"{motor} teve a maior media de acertos por jogo."
                if motor == vencedor
                else f"{motor} nao superou {vencedor} na media de acertos por jogo."
            )
        )
        resumo["Vantagem sobre aleatorio"] = 0.0
        aleatorio = resumo.loc[resumo["Motor"] == "Aleatorio", "Media de acertos por jogo"]
        if not aleatorio.empty:
            media_aleatoria = float(aleatorio.iloc[0])
            resumo["Vantagem sobre aleatorio"] = resumo["Media de acertos por jogo"].astype(float) - media_aleatoria
        resumo["Melhor media geral"] = melhor_media
    return resumo


def executar_auditoria_comparativa(
    quantidade_concursos: int = 1000,
    jogos_por_concurso: int = 100,
    quantidade_candidatos_elite7: int = 100,
    seed: int = 20260604,
    export_dir: str | Path = "exports",
    log_progresso: bool = True,
) -> dict[str, pd.DataFrame | Path]:
    rng = random.Random(seed)
    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)
    df = carregar_base().sort_values("Concurso", ascending=True).reset_index(drop=True)
    concursos_teste = df.tail(max(1, min(int(quantidade_concursos), len(df))))
    registros: list[dict] = []
    inicio = time.time()

    portfolio_elite8 = gerar_portfolio_elite8_completo(quantidade_candidatos=100000, seed=8)
    jogos_elite8 = [parse_jogo(jogo) for jogo in portfolio_elite8["Jogo"].astype(str).head(jogos_por_concurso)]

    for posicao, (_, concurso_real) in enumerate(concursos_teste.iterrows(), start=1):
        concurso = int(concurso_real["Concurso"])
        historico = df[df["Concurso"].astype(int) < concurso]
        resultado_real = {int(concurso_real[coluna]) for coluna in COLUNAS_DEZENAS}

        ranking_elite7 = gerar_motor_elite_7(
            historico,
            quantidade_candidatos=quantidade_candidatos_elite7,
            top=jogos_por_concurso,
        )
        jogos_elite7 = [parse_jogo(jogo) for jogo in ranking_elite7["Jogo"].astype(str).tolist()]
        jogos_aleatorios = gerar_jogos_aleatorios(jogos_por_concurso, rng)

        registros.append(medir_jogos(concurso, "Aleatorio", jogos_aleatorios, resultado_real))
        registros.append(medir_jogos(concurso, "Motor Elite 7", jogos_elite7, resultado_real))
        registros.append(medir_jogos(concurso, "Motor Elite 8", jogos_elite8, resultado_real))

        if log_progresso and (posicao == 1 or posicao % 25 == 0):
            print(f"progresso={posicao}/{len(concursos_teste)} elapsed_s={time.time() - inicio:.1f}", flush=True)

    detalhes = pd.DataFrame(registros)
    resumo = resumir_auditoria(detalhes)
    sufixo = f"{len(concursos_teste)}_{jogos_por_concurso}"
    caminho_detalhes = export_path / f"auditoria_elite8_comparativa_{sufixo}_detalhada.csv"
    caminho_resumo = export_path / f"auditoria_elite8_comparativa_{sufixo}_resumo.csv"
    caminho_portfolio = export_path / f"portfolio_elite8_{jogos_por_concurso}.csv"
    detalhes.to_csv(caminho_detalhes, index=False, encoding="utf-8-sig")
    resumo.to_csv(caminho_resumo, index=False, encoding="utf-8-sig")
    portfolio_elite8.to_csv(caminho_portfolio, index=False, encoding="utf-8-sig")
    return {
        "detalhes": detalhes,
        "resumo": resumo,
        "portfolio_elite8": portfolio_elite8,
        "caminho_detalhes": caminho_detalhes,
        "caminho_resumo": caminho_resumo,
        "caminho_portfolio": caminho_portfolio,
    }


if __name__ == "__main__":
    resultado = executar_auditoria_comparativa()
    print(resultado["resumo"].to_string(index=False))
    print(f"RESUMO={Path(resultado['caminho_resumo']).resolve()}")
    print(f"DETALHES={Path(resultado['caminho_detalhes']).resolve()}")
    print(f"PORTFOLIO={Path(resultado['caminho_portfolio']).resolve()}")

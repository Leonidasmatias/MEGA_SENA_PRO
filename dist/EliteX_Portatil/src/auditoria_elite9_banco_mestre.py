from __future__ import annotations

from pathlib import Path
import math
import random

import pandas as pd

from src.auditoria_elite9 import PONTOS_PREMIACAO
from src.auditoria_elite9_20_dezenas import PontuadorElite9Expandido, _formatar_dezenas, _faixa
from src.carregar_dados import COLUNAS_DEZENAS, carregar_base


TAMANHOS_BANCO = (20, 25, 30)


def _selecionar_top_n_diverso(ranking: pd.DataFrame, tamanho: int) -> list[int]:
    scores = {
        int(linha["Dezena"]): float(linha["Score Elite 9 Expandido"])
        for _, linha in ranking.iterrows()
    }
    ordenadas = sorted(range(1, 61), key=lambda dezena: (scores.get(dezena, 0.0), -dezena), reverse=True)
    selecionadas: list[int] = []
    por_faixa = {indice: 0 for indice in range(6)}
    limite_faixa = max(4, math.ceil(int(tamanho) / 6) + 1)

    for dezena in ordenadas:
        faixa = _faixa(dezena)
        if por_faixa[faixa] >= limite_faixa:
            continue
        selecionadas.append(dezena)
        por_faixa[faixa] += 1
        if len(selecionadas) >= tamanho:
            break

    for dezena in ordenadas:
        if len(selecionadas) >= tamanho:
            break
        if dezena not in selecionadas:
            selecionadas.append(dezena)
    return sorted(selecionadas[:tamanho])


def _linha(
    janela: str,
    motor: str,
    tamanho: int,
    concurso: int,
    banco: list[int],
    resultado_real: set[int],
) -> dict:
    acertos = len(set(banco) & resultado_real)
    return {
        "Janela": janela,
        "Motor": motor,
        "Tamanho banco": int(tamanho),
        "Concurso": int(concurso),
        "Banco dezenas": _formatar_dezenas(banco),
        "Resultado real": _formatar_dezenas(resultado_real),
        "Acertos": acertos,
        "Cobertura (%)": round(acertos / 6 * 100, 6),
        "Score premiacao": PONTOS_PREMIACAO.get(acertos, 0),
    }


def _conclusao_por_janela(resumo_janela: pd.DataFrame) -> str:
    melhor_media = resumo_janela.loc[resumo_janela["Media de acertos"].idxmax()]
    mais_4 = resumo_janela.loc[resumo_janela["Concursos com 4 acertos"].idxmax()]
    mais_5 = resumo_janela.loc[resumo_janela["Concursos com 5 acertos"].idxmax()]
    mais_6 = resumo_janela.loc[resumo_janela["Concursos com 6 acertos"].idxmax()]
    comparacoes = []
    for tamanho in TAMANHOS_BANCO:
        elite = resumo_janela[
            (resumo_janela["Motor"] == "Elite 9 Banco Mestre")
            & (resumo_janela["Tamanho banco"] == tamanho)
        ]
        aleatorio = resumo_janela[
            (resumo_janela["Motor"] == "Aleatorio Banco Mestre")
            & (resumo_janela["Tamanho banco"] == tamanho)
        ]
        if elite.empty or aleatorio.empty:
            continue
        elite_media = float(elite.iloc[0]["Media de cobertura (%)"])
        aleatorio_media = float(aleatorio.iloc[0]["Media de cobertura (%)"])
        status = "superou" if elite_media > aleatorio_media else "nao superou" if elite_media < aleatorio_media else "empatou"
        comparacoes.append(f"{tamanho}: Elite 9 {status} o aleatorio")
    return (
        f"Maior media: {melhor_media['Motor']} banco {int(melhor_media['Tamanho banco'])}. "
        f"Mais 4 acertos: {mais_4['Motor']} banco {int(mais_4['Tamanho banco'])}. "
        f"Mais 5 acertos: {mais_5['Motor']} banco {int(mais_5['Tamanho banco'])}. "
        f"Mais 6 acertos: {mais_6['Motor']} banco {int(mais_6['Tamanho banco'])}. "
        + "; ".join(comparacoes)
    )


def _resumir(detalhes: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for (janela, motor, tamanho), grupo in detalhes.groupby(["Janela", "Motor", "Tamanho banco"], sort=False):
        total = len(grupo)
        melhor_idx = grupo["Acertos"].astype(int).idxmax()
        linha = {
            "Janela": janela,
            "Motor": motor,
            "Tamanho banco": int(tamanho),
            "Concursos analisados": total,
            "Media de acertos": round(float(grupo["Acertos"].mean()), 6),
            "Media de cobertura (%)": round(float(grupo["Cobertura (%)"].mean()), 6),
            "Melhor acerto": int(grupo.loc[melhor_idx, "Acertos"]),
            "Melhor concurso": int(grupo.loc[melhor_idx, "Concurso"]),
            "Melhor banco": grupo.loc[melhor_idx, "Banco dezenas"],
            "Resultado melhor concurso": grupo.loc[melhor_idx, "Resultado real"],
            "Score premiacao": int(grupo["Score premiacao"].sum()),
            "Score medio premiacao": round(float(grupo["Score premiacao"].mean()), 6),
        }
        for acertos in range(7):
            linha[f"Concursos com {acertos} acertos"] = int((grupo["Acertos"] == acertos).sum())
        linhas.append(linha)

    resumo = pd.DataFrame(linhas)
    conclusoes = {
        janela: _conclusao_por_janela(grupo)
        for janela, grupo in resumo.groupby("Janela", sort=False)
    }
    resumo["Conclusao automatica"] = resumo["Janela"].map(conclusoes).fillna("")
    return resumo


def executar_banco_mestre_elite9(
    janelas: tuple[int | str, ...] = (500, 1000, "toda_base"),
    seed: int = 20260604,
    export_dir: str | Path = "exports",
) -> dict[str, pd.DataFrame | Path]:
    rng = random.Random(seed)
    dados = carregar_base().sort_values("Concurso", ascending=True).reset_index(drop=True)
    pontuador = PontuadorElite9Expandido()
    avaliacoes = []

    for _, linha in dados.iterrows():
        concurso = int(linha["Concurso"])
        resultado_real = {int(linha[coluna]) for coluna in COLUNAS_DEZENAS}
        ranking = pontuador.pontuar_dezenas()
        bancos_elite = {
            tamanho: _selecionar_top_n_diverso(ranking, tamanho)
            for tamanho in TAMANHOS_BANCO
        }
        bancos_aleatorios = {
            tamanho: sorted(rng.sample(range(1, 61), tamanho))
            for tamanho in TAMANHOS_BANCO
        }
        avaliacoes.append(
            {
                "Concurso": concurso,
                "Resultado": resultado_real,
                "Elite": bancos_elite,
                "Aleatorio": bancos_aleatorios,
            }
        )
        pontuador.adicionar_concurso(concurso, tuple(sorted(resultado_real)))

    registros = []
    total_base = len(avaliacoes)
    for janela in janelas:
        if isinstance(janela, str):
            tamanho_janela = total_base
            nome = "Toda a base"
        else:
            tamanho_janela = max(1, min(int(janela), total_base))
            nome = f"Ultimos {tamanho_janela}"
        for item in avaliacoes[-tamanho_janela:]:
            for tamanho in TAMANHOS_BANCO:
                registros.append(
                    _linha(
                        nome,
                        "Elite 9 Banco Mestre",
                        tamanho,
                        int(item["Concurso"]),
                        item["Elite"][tamanho],
                        set(item["Resultado"]),
                    )
                )
                registros.append(
                    _linha(
                        nome,
                        "Aleatorio Banco Mestre",
                        tamanho,
                        int(item["Concurso"]),
                        item["Aleatorio"][tamanho],
                        set(item["Resultado"]),
                    )
                )

    detalhes = pd.DataFrame(registros)
    resumo = _resumir(detalhes)
    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)
    caminho_resumo = export_path / "elite9_banco_mestre_resumo.csv"
    caminho_detalhado = export_path / "elite9_banco_mestre_detalhado.csv"
    resumo.to_csv(caminho_resumo, index=False, encoding="utf-8-sig")
    detalhes.to_csv(caminho_detalhado, index=False, encoding="utf-8-sig")
    return {
        "resumo": resumo,
        "detalhes": detalhes,
        "caminho_resumo": caminho_resumo,
        "caminho_detalhado": caminho_detalhado,
    }


if __name__ == "__main__":
    resultado = executar_banco_mestre_elite9()
    print(resultado["resumo"].to_string(index=False))
    print(f"RESUMO={Path(resultado['caminho_resumo']).resolve()}")
    print(f"DETALHADO={Path(resultado['caminho_detalhado']).resolve()}")

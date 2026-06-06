from __future__ import annotations

from collections import Counter, deque
from itertools import combinations
from pathlib import Path
import random

import pandas as pd

from src.carregar_dados import COLUNAS_DEZENAS, carregar_base


JANELA_RECENTE = 100
FAIXAS = ["01-10", "11-20", "21-30", "31-40", "41-50", "51-60"]


def _faixa(dezena: int) -> int:
    return min((int(dezena) - 1) // 10, 5)


def _formatar_dezenas(dezenas: list[int] | set[int] | tuple[int, ...]) -> str:
    return " - ".join(f"{int(dezena):02d}" for dezena in sorted(dezenas))


def _normalizar_mapa(valores: dict[int, float]) -> dict[int, float]:
    maior = max(valores.values(), default=0.0)
    if maior <= 0:
        return {dezena: 0.0 for dezena in range(1, 61)}
    return {dezena: (float(valores.get(dezena, 0.0)) / maior) * 100.0 for dezena in range(1, 61)}


def _selecionar_top20_diverso(scores: dict[int, float]) -> list[int]:
    selecionadas: list[int] = []
    por_faixa = {indice: 0 for indice in range(6)}
    ordenadas = sorted(range(1, 61), key=lambda dezena: (scores.get(dezena, 0.0), -dezena), reverse=True)

    for dezena in ordenadas:
        faixa = _faixa(dezena)
        if por_faixa[faixa] >= 4:
            continue
        selecionadas.append(dezena)
        por_faixa[faixa] += 1
        if len(selecionadas) >= 20:
            break

    for dezena in ordenadas:
        if len(selecionadas) >= 20:
            break
        if dezena not in selecionadas:
            selecionadas.append(dezena)

    return sorted(selecionadas[:20])


class PontuadorElite9Expandido:
    def __init__(self, janela_recente: int = JANELA_RECENTE) -> None:
        self.janela_recente = max(1, int(janela_recente))
        self.frequencia_geral: Counter[int] = Counter()
        self.frequencia_recente: Counter[int] = Counter()
        self.pares: Counter[tuple[int, int]] = Counter()
        self.trincas: Counter[tuple[int, int, int]] = Counter()
        self.forca_pares: Counter[int] = Counter()
        self.forca_trincas: Counter[int] = Counter()
        self.ultimo_aparecimento: dict[int, int] = {}
        self.recentes: deque[tuple[int, ...]] = deque()
        self.total_concursos = 0

    def adicionar_concurso(self, concurso: int, dezenas: tuple[int, ...]) -> None:
        self.total_concursos += 1
        for dezena in dezenas:
            self.frequencia_geral[dezena] += 1
            self.frequencia_recente[dezena] += 1
            self.ultimo_aparecimento[dezena] = int(concurso)
        for par in combinations(dezenas, 2):
            par = tuple(par)
            self.pares[par] += 1
            for dezena in par:
                self.forca_pares[dezena] += 1
        for trinca in combinations(dezenas, 3):
            trinca = tuple(trinca)
            self.trincas[trinca] += 1
            for dezena in trinca:
                self.forca_trincas[dezena] += 1
        self.recentes.append(dezenas)
        if len(self.recentes) > self.janela_recente:
            removido = self.recentes.popleft()
            for dezena in removido:
                self.frequencia_recente[dezena] -= 1
                if self.frequencia_recente[dezena] <= 0:
                    del self.frequencia_recente[dezena]

    def pontuar_dezenas(self) -> pd.DataFrame:
        if self.total_concursos == 0:
            registros = [
                {
                    "Dezena": dezena,
                    "Score Elite 9 Expandido": 100.0 - abs(30.5 - dezena),
                    "Frequencia geral": 0,
                    "Frequencia recente": 0,
                    "Atraso": 0,
                    "Forca pares": 0.0,
                    "Forca trincas": 0.0,
                }
                for dezena in range(1, 61)
            ]
            return pd.DataFrame(registros).sort_values("Score Elite 9 Expandido", ascending=False)

        ultimo_indice = self.total_concursos
        forca_pares = {dezena: self.forca_pares[dezena] for dezena in range(1, 61)}
        forca_trincas = {dezena: self.forca_trincas[dezena] for dezena in range(1, 61)}
        atrasos = {
            dezena: ultimo_indice - self.ultimo_aparecimento.get(dezena, 0)
            for dezena in range(1, 61)
        }
        freq_norm = _normalizar_mapa({dezena: float(self.frequencia_geral[dezena]) for dezena in range(1, 61)})
        recente_norm = _normalizar_mapa({dezena: float(self.frequencia_recente[dezena]) for dezena in range(1, 61)})
        pares_norm = _normalizar_mapa({dezena: float(forca_pares[dezena]) for dezena in range(1, 61)})
        trincas_norm = _normalizar_mapa({dezena: float(forca_trincas[dezena]) for dezena in range(1, 61)})
        atraso_norm = _normalizar_mapa({dezena: float(atrasos[dezena]) for dezena in range(1, 61)})

        registros = []
        for dezena in range(1, 61):
            faixa = _faixa(dezena)
            equilibrio_faixa = 100.0 - abs(2.5 - faixa) * 8.0
            score = (
                freq_norm[dezena] * 0.18
                + recente_norm[dezena] * 0.20
                + pares_norm[dezena] * 0.22
                + trincas_norm[dezena] * 0.25
                + atraso_norm[dezena] * 0.10
                + equilibrio_faixa * 0.05
            )
            registros.append(
                {
                    "Dezena": dezena,
                    "Score Elite 9 Expandido": round(score, 6),
                    "Frequencia geral": int(self.frequencia_geral[dezena]),
                    "Frequencia recente": int(self.frequencia_recente[dezena]),
                    "Atraso": int(atrasos[dezena]),
                    "Forca pares": float(forca_pares[dezena]),
                    "Forca trincas": float(forca_trincas[dezena]),
                }
            )
        return pd.DataFrame(registros).sort_values(
            ["Score Elite 9 Expandido", "Dezena"],
            ascending=[False, True],
        ).reset_index(drop=True)

    def top20(self) -> tuple[list[int], pd.DataFrame]:
        ranking = self.pontuar_dezenas()
        scores = {
            int(linha["Dezena"]): float(linha["Score Elite 9 Expandido"])
            for _, linha in ranking.iterrows()
        }
        return _selecionar_top20_diverso(scores), ranking


def _linha_resultado(
    janela: str,
    motor: str,
    concurso: int,
    dezenas_selecionadas: list[int],
    resultado_real: set[int],
) -> dict:
    acertos = len(set(dezenas_selecionadas) & resultado_real)
    return {
        "Janela": janela,
        "Motor": motor,
        "Concurso": int(concurso),
        "Dezenas selecionadas": _formatar_dezenas(dezenas_selecionadas),
        "Resultado real": _formatar_dezenas(resultado_real),
        "Acertos": acertos,
        "Cobertura (%)": round((acertos / 6) * 100, 6),
    }


def _resumir(detalhes: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for (janela, motor), grupo in detalhes.groupby(["Janela", "Motor"], sort=False):
        total = len(grupo)
        melhor_idx = grupo["Acertos"].astype(int).idxmax()
        linha = {
            "Janela": janela,
            "Motor": motor,
            "Concursos analisados": total,
            "Media de acertos nas 20 dezenas": round(float(grupo["Acertos"].mean()), 6),
            "Media de cobertura (%)": round(float(grupo["Cobertura (%)"].mean()), 6),
            "Melhor acerto": int(grupo.loc[melhor_idx, "Acertos"]),
            "Melhor concurso": int(grupo.loc[melhor_idx, "Concurso"]),
            "Melhor dezenas": grupo.loc[melhor_idx, "Dezenas selecionadas"],
            "Resultado melhor concurso": grupo.loc[melhor_idx, "Resultado real"],
        }
        for acertos in range(7):
            quantidade = int((grupo["Acertos"] == acertos).sum())
            linha[f"Concursos com {acertos} acertos"] = quantidade
            linha[f"Taxa {acertos} acertos (%)"] = round((quantidade / total * 100) if total else 0.0, 6)
        linhas.append(linha)

    resumo = pd.DataFrame(linhas)
    conclusoes = {}
    for janela, grupo in resumo.groupby("Janela", sort=False):
        elite = grupo[group_motor := (grupo["Motor"] == "Elite 9 Expandido 20 dezenas")]
        aleatorio = grupo[grupo["Motor"] == "Aleatorio 20 dezenas"]
        if not elite.empty and not aleatorio.empty:
            elite_media = float(elite.iloc[0]["Media de cobertura (%)"])
            aleatorio_media = float(aleatorio.iloc[0]["Media de cobertura (%)"])
            if elite_media > aleatorio_media:
                conclusoes[janela] = "Elite 9 superou a selecao aleatoria de 20 dezenas."
            elif elite_media < aleatorio_media:
                conclusoes[janela] = "Elite 9 nao superou a selecao aleatoria de 20 dezenas."
            else:
                conclusoes[janela] = "Elite 9 empatou com a selecao aleatoria de 20 dezenas."
    resumo["Conclusao automatica"] = resumo["Janela"].map(conclusoes).fillna("")
    return resumo


def executar_teste_elite9_aposta_expandida(
    janelas: tuple[int | str, ...] = (500, 1000, "toda_base"),
    seed: int = 20260604,
    export_dir: str | Path = "exports",
) -> dict[str, pd.DataFrame | Path]:
    rng = random.Random(seed)
    dados = carregar_base().sort_values("Concurso", ascending=True).reset_index(drop=True)
    pontuador = PontuadorElite9Expandido()
    avaliacoes_por_concurso: list[dict] = []

    for _, linha in dados.iterrows():
        concurso = int(linha["Concurso"])
        resultado_real = {int(linha[coluna]) for coluna in COLUNAS_DEZENAS}
        top20, _ranking = pontuador.top20()
        aleatorio = sorted(rng.sample(range(1, 61), 20))
        avaliacoes_por_concurso.append(
            {
                "Concurso": concurso,
                "Elite": top20,
                "Aleatorio": aleatorio,
                "Resultado": resultado_real,
            }
        )
        pontuador.adicionar_concurso(concurso, tuple(sorted(resultado_real)))

    registros = []
    total_base = len(avaliacoes_por_concurso)
    for janela in janelas:
        if isinstance(janela, str):
            tamanho = total_base
            nome = "Toda a base"
        else:
            tamanho = max(1, min(int(janela), total_base))
            nome = f"Ultimos {tamanho}"
        alvo = avaliacoes_por_concurso[-tamanho:]
        for item in alvo:
            registros.append(
                _linha_resultado(
                    nome,
                    "Elite 9 Expandido 20 dezenas",
                    int(item["Concurso"]),
                    list(item["Elite"]),
                    set(item["Resultado"]),
                )
            )
            registros.append(
                _linha_resultado(
                    nome,
                    "Aleatorio 20 dezenas",
                    int(item["Concurso"]),
                    list(item["Aleatorio"]),
                    set(item["Resultado"]),
                )
            )

    detalhes = pd.DataFrame(registros)
    resumo = _resumir(detalhes)
    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)
    caminho_detalhes = export_path / "teste_elite9_aposta_expandida_20_dezenas_detalhado.csv"
    caminho_resumo = export_path / "teste_elite9_aposta_expandida_20_dezenas_resumo.csv"
    detalhes.to_csv(caminho_detalhes, index=False, encoding="utf-8-sig")
    resumo.to_csv(caminho_resumo, index=False, encoding="utf-8-sig")
    return {
        "detalhes": detalhes,
        "resumo": resumo,
        "caminho_detalhes": caminho_detalhes,
        "caminho_resumo": caminho_resumo,
    }


if __name__ == "__main__":
    resultado = executar_teste_elite9_aposta_expandida()
    print(resultado["resumo"].to_string(index=False))
    print(f"RESUMO={Path(resultado['caminho_resumo']).resolve()}")
    print(f"DETALHES={Path(resultado['caminho_detalhes']).resolve()}")

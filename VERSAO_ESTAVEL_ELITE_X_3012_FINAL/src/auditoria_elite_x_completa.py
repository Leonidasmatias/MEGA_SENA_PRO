from __future__ import annotations

from itertools import combinations
from pathlib import Path
import random
import time

import pandas as pd

from src.auditoria_elite8 import formatar_jogo, gerar_jogos_aleatorios, parse_jogo
from src.auditoria_elite9 import PONTOS_PREMIACAO
from src.auditoria_elite9_20_dezenas import PontuadorElite9Expandido
from src.auditoria_elite9_banco_mestre import _selecionar_top_n_diverso
from src.carregar_dados import COLUNAS_DEZENAS, carregar_base
from src.elite9_motor import gerar_portfolio_elite9
from src.elite_x_fechamento import (
    calcular_cobertura_duplas,
    calcular_cobertura_quadras,
    calcular_cobertura_trincas,
    calcular_quantidade_jogos_por_orcamento,
    calcular_redundancia,
    gerar_combinacoes_30_dezenas,
)


JANELAS_PADRAO: tuple[int | str, ...] = (500, 1000, "toda_base")
UNIVERSO_60 = tuple(range(1, 61))
TOTAL_DUPLAS_60 = len(list(combinations(UNIVERSO_60, 2)))
TOTAL_TRINCAS_60 = len(list(combinations(UNIVERSO_60, 3)))
TOTAL_QUADRAS_60 = len(list(combinations(UNIVERSO_60, 4)))


def _nome_janela(janela: int | str, total: int) -> tuple[str, int]:
    if isinstance(janela, str):
        return "Toda a base", int(total)
    tamanho = max(1, min(int(janela), int(total)))
    return f"Ultimos {tamanho}", tamanho


def _cobertura_dezenas(jogos: list[list[int]], universo: list[int] | tuple[int, ...]) -> float:
    if not jogos or not universo:
        return 0.0
    dezenas = set()
    for jogo in jogos:
        dezenas.update(int(dezena) for dezena in jogo)
    return round(len(dezenas & set(universo)) / len(set(universo)) * 100, 6)


def _cobertura_combinacoes(jogos: list[list[int]], tamanho: int, universo_total: int) -> float:
    if not jogos or universo_total <= 0:
        return 0.0
    cobertas = set()
    for jogo in jogos:
        cobertas.update(tuple(comb) for comb in combinations(sorted(jogo), tamanho))
    return round(len(cobertas) / universo_total * 100, 6)


def _metricas_cobertura(
    motor: str,
    jogos: list[list[int]],
    banco_mestre: list[int] | None = None,
) -> dict[str, float]:
    if motor == "Elite X" and banco_mestre:
        return {
            "Cobertura de dezenas": _cobertura_dezenas(jogos, banco_mestre),
            "Cobertura de duplas": calcular_cobertura_duplas(jogos, banco_mestre) if jogos else 0.0,
            "Cobertura de trincas": calcular_cobertura_trincas(jogos, banco_mestre) if jogos else 0.0,
            "Cobertura de quadras": calcular_cobertura_quadras(jogos, banco_mestre) if jogos else 0.0,
            "Redundancia": calcular_redundancia(jogos) if jogos else 0.0,
        }

    return {
        "Cobertura de dezenas": _cobertura_dezenas(jogos, UNIVERSO_60),
        "Cobertura de duplas": _cobertura_combinacoes(jogos, 2, TOTAL_DUPLAS_60),
        "Cobertura de trincas": _cobertura_combinacoes(jogos, 3, TOTAL_TRINCAS_60),
        "Cobertura de quadras": _cobertura_combinacoes(jogos, 4, TOTAL_QUADRAS_60),
        "Redundancia": calcular_redundancia(jogos) if jogos else 0.0,
    }


def _indices_combinacoes(banco_mestre: list[int]) -> tuple[dict[tuple[int, ...], int], dict[tuple[int, ...], int], dict[tuple[int, ...], int]]:
    banco = tuple(sorted(int(dezena) for dezena in banco_mestre))
    pares = {tuple(comb): indice for indice, comb in enumerate(combinations(banco, 2))}
    trincas = {tuple(comb): indice for indice, comb in enumerate(combinations(banco, 3))}
    quadras = {tuple(comb): indice for indice, comb in enumerate(combinations(banco, 4))}
    return pares, trincas, quadras


def _mask_combinacoes(jogo: tuple[int, ...], indices: dict[tuple[int, ...], int], tamanho: int) -> int:
    mascara = 0
    for combinacao in combinations(jogo, tamanho):
        mascara |= 1 << indices[tuple(combinacao)]
    return mascara


def _otimizar_fechamento_rapido(
    banco_mestre: list[int],
    quantidade_jogos: int,
    quantidade_candidatos: int,
    seed: int,
) -> list[list[int]]:
    candidatos = gerar_combinacoes_30_dezenas(
        banco_mestre,
        quantidade_candidatos=quantidade_candidatos,
        seed=seed,
    )
    if not candidatos or quantidade_jogos <= 0:
        return []

    pares_idx, trincas_idx, quadras_idx = _indices_combinacoes(banco_mestre)
    itens = []
    for jogo in candidatos:
        jogo = tuple(sorted(int(dezena) for dezena in jogo))
        jogo_mask = sum(1 << (dezena - 1) for dezena in jogo)
        itens.append(
            {
                "jogo": jogo,
                "jogo_mask": jogo_mask,
                "pares": _mask_combinacoes(jogo, pares_idx, 2),
                "trincas": _mask_combinacoes(jogo, trincas_idx, 3),
                "quadras": _mask_combinacoes(jogo, quadras_idx, 4),
            }
        )

    selecionados: list[dict] = []
    restantes = list(range(len(itens)))
    pares_cobertos = 0
    trincas_cobertas = 0
    quadras_cobertas = 0

    while restantes and len(selecionados) < quantidade_jogos:
        melhor_posicao = 0
        melhor_score = None
        for posicao, indice in enumerate(restantes):
            item = itens[indice]
            novas_duplas = (item["pares"] & ~pares_cobertos).bit_count()
            novas_trincas = (item["trincas"] & ~trincas_cobertas).bit_count()
            novas_quadras = (item["quadras"] & ~quadras_cobertas).bit_count()
            penalidade = 0.0
            if selecionados:
                maior_sobreposicao = max((item["jogo_mask"] & outro["jogo_mask"]).bit_count() for outro in selecionados)
                penalidade = maior_sobreposicao * 2.5
            score = novas_duplas * 1.0 + novas_trincas * 2.2 + novas_quadras * 4.5 - penalidade
            if melhor_score is None or score > melhor_score:
                melhor_score = score
                melhor_posicao = posicao

        escolhido = itens[restantes.pop(melhor_posicao)]
        selecionados.append(escolhido)
        pares_cobertos |= escolhido["pares"]
        trincas_cobertas |= escolhido["trincas"]
        quadras_cobertas |= escolhido["quadras"]

    return [list(item["jogo"]) for item in selecionados]


def _medir_jogos(
    concurso: int,
    motor: str,
    jogos: list[list[int]],
    resultado_real: set[int],
    banco_mestre: list[int] | None = None,
) -> dict:
    contagem = {acertos: 0 for acertos in range(7)}
    total_acertos = 0
    melhor_acerto = 0
    melhor_jogo: list[int] = []
    score_premiacao = 0

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
        "Concurso": int(concurso),
        "Motor": motor,
        "Jogos": total_jogos,
        "Total de acertos": total_acertos,
        "Media de acertos": round(total_acertos / total_jogos, 6) if total_jogos else 0.0,
        "Melhor acerto": melhor_acerto,
        "Melhor jogo": formatar_jogo(melhor_jogo),
        "Resultado real": formatar_jogo(resultado_real),
        "Score de premiacao": score_premiacao,
    }
    for acertos in range(4, 7):
        quantidade = contagem[acertos]
        linha[f"Jogos com {acertos} acertos"] = quantidade
        linha[f"Taxa {acertos} acertos (%)"] = round((quantidade / total_jogos * 100) if total_jogos else 0.0, 6)
    linha.update(_metricas_cobertura(motor, jogos, banco_mestre=banco_mestre))
    return linha


def _conclusao_janela(resumo_janela: pd.DataFrame) -> str:
    vencedor_media = resumo_janela.loc[resumo_janela["Media de acertos"].idxmax(), "Motor"]
    vencedor_4 = resumo_janela.loc[resumo_janela["Jogos com 4 acertos"].idxmax(), "Motor"]
    vencedor_5 = resumo_janela.loc[resumo_janela["Jogos com 5 acertos"].idxmax(), "Motor"]
    vencedor_6 = resumo_janela.loc[resumo_janela["Jogos com 6 acertos"].idxmax(), "Motor"]
    vencedor_score = resumo_janela.loc[resumo_janela["Score de premiacao"].idxmax(), "Motor"]

    elite_x = resumo_janela[resumo_janela["Motor"] == "Elite X"]
    elite9 = resumo_janela[resumo_janela["Motor"] == "Elite 9"]
    aleatorio = resumo_janela[resumo_janela["Motor"] == "Aleatorio"]
    agrega = "indeterminado"
    if not elite_x.empty and not elite9.empty and not aleatorio.empty:
        x = elite_x.iloc[0]
        e9 = elite9.iloc[0]
        rnd = aleatorio.iloc[0]
        agrega = (
            "sim"
            if float(x["Media de acertos"]) > max(float(e9["Media de acertos"]), float(rnd["Media de acertos"]))
            or int(x["Score de premiacao"]) > max(int(e9["Score de premiacao"]), int(rnd["Score de premiacao"]))
            else "nao"
        )

    return (
        f"Media: {vencedor_media}. "
        f"4 acertos: {vencedor_4}. "
        f"5 acertos: {vencedor_5}. "
        f"6 acertos: {vencedor_6}. "
        f"Score premiacao: {vencedor_score}. "
        f"Elite X agrega valor ao Banco Mestre: {agrega}."
    )


def resumir_auditoria_elite_x(detalhes_base: pd.DataFrame, janelas: tuple[int | str, ...] = JANELAS_PADRAO) -> pd.DataFrame:
    linhas = []
    concursos_ordenados = sorted(detalhes_base["Concurso"].astype(int).unique())
    total_concursos = len(concursos_ordenados)

    for janela in janelas:
        nome, tamanho = _nome_janela(janela, total_concursos)
        concursos_janela = set(concursos_ordenados[-tamanho:])
        detalhes = detalhes_base[detalhes_base["Concurso"].astype(int).isin(concursos_janela)]
        for motor, grupo in detalhes.groupby("Motor", sort=False):
            total_jogos = int(grupo["Jogos"].sum())
            total_acertos = int(grupo["Total de acertos"].sum())
            melhor_idx = grupo["Melhor acerto"].astype(int).idxmax()
            linha = {
                "Janela": nome,
                "Motor": motor,
                "Concursos analisados": int(grupo["Concurso"].nunique()),
                "Total de jogos": total_jogos,
                "Total de acertos": total_acertos,
                "Media de acertos": round(total_acertos / total_jogos, 6) if total_jogos else 0.0,
                "Melhor acerto": int(grupo.loc[melhor_idx, "Melhor acerto"]),
                "Melhor jogo": grupo.loc[melhor_idx, "Melhor jogo"],
                "Concurso do melhor jogo": int(grupo.loc[melhor_idx, "Concurso"]),
                "Resultado melhor concurso": grupo.loc[melhor_idx, "Resultado real"],
                "Score de premiacao": int(grupo["Score de premiacao"].sum()),
                "Cobertura de dezenas": round(float(grupo["Cobertura de dezenas"].mean()), 6),
                "Cobertura de duplas": round(float(grupo["Cobertura de duplas"].mean()), 6),
                "Cobertura de trincas": round(float(grupo["Cobertura de trincas"].mean()), 6),
                "Cobertura de quadras": round(float(grupo["Cobertura de quadras"].mean()), 6),
                "Redundancia": round(float(grupo["Redundancia"].mean()), 6),
            }
            for acertos in range(4, 7):
                coluna = f"Jogos com {acertos} acertos"
                quantidade = int(grupo[coluna].sum())
                linha[coluna] = quantidade
                linha[f"Taxa {acertos} acertos (%)"] = round((quantidade / total_jogos * 100) if total_jogos else 0.0, 6)
            linhas.append(linha)

    resumo = pd.DataFrame(linhas)
    conclusoes = {
        janela: _conclusao_janela(grupo)
        for janela, grupo in resumo.groupby("Janela", sort=False)
    }
    resumo["Conclusao automatica"] = resumo["Janela"].map(conclusoes).fillna("")
    return resumo


def executar_auditoria_elite_x_completa(
    orcamento: float = 500.0,
    valor_aposta_simples: float = 5.0,
    candidatos_elite9: int = 1000,
    geracoes_elite9: int = 1,
    populacao_elite9: int = 100,
    candidatos_elite_x: int = 3000,
    seed: int = 20260604,
    export_dir: str | Path = "exports",
    log_progresso: bool = True,
) -> dict[str, pd.DataFrame | Path]:
    rng = random.Random(seed)
    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)

    dados = carregar_base().sort_values("Concurso", ascending=True).reset_index(drop=True)
    quantidade_jogos = calcular_quantidade_jogos_por_orcamento(orcamento, valor_aposta_simples)
    pontuador = PontuadorElite9Expandido()
    registros: list[dict] = []
    inicio = time.time()

    for posicao, (_, linha) in enumerate(dados.iterrows(), start=1):
        concurso = int(linha["Concurso"])
        resultado_real = {int(linha[coluna]) for coluna in COLUNAS_DEZENAS}
        historico = dados[dados["Concurso"].astype(int) < concurso]

        jogos_aleatorios = gerar_jogos_aleatorios(quantidade_jogos, rng)
        registros.append(_medir_jogos(concurso, "Aleatorio", jogos_aleatorios, resultado_real))

        elite9 = gerar_portfolio_elite9(
            historico,
            quantidade_candidatos=candidatos_elite9,
            geracoes=geracoes_elite9,
            tamanho_populacao=max(50, int(populacao_elite9)),
            quantidade_final=quantidade_jogos,
            seed=seed + concurso,
            janela_historico=300,
        )
        jogos_elite9 = [parse_jogo(jogo) for jogo in elite9["Jogo"].astype(str).tolist()]
        registros.append(_medir_jogos(concurso, "Elite 9", jogos_elite9, resultado_real))

        ranking_banco = pontuador.pontuar_dezenas()
        banco_mestre = _selecionar_top_n_diverso(ranking_banco, 30)
        jogos_elite_x = _otimizar_fechamento_rapido(
            banco_mestre,
            quantidade_jogos,
            candidatos_elite_x,
            seed + concurso,
        )
        registros.append(_medir_jogos(concurso, "Elite X", jogos_elite_x, resultado_real, banco_mestre=banco_mestre))

        pontuador.adicionar_concurso(concurso, tuple(sorted(resultado_real)))
        if log_progresso and (posicao == 1 or posicao % 25 == 0 or posicao == len(dados)):
            print(f"progresso={posicao}/{len(dados)} elapsed_s={time.time() - inicio:.1f}", flush=True)

    detalhes_base = pd.DataFrame(registros)
    detalhes_base["Orcamento"] = float(orcamento)
    detalhes_base["Valor aposta simples"] = float(valor_aposta_simples)
    detalhes_base["Jogos por concurso planejados"] = int(quantidade_jogos)
    detalhes_base["Candidatos Elite 9"] = int(candidatos_elite9)
    detalhes_base["Geracoes Elite 9"] = int(geracoes_elite9)
    detalhes_base["Populacao Elite 9"] = int(populacao_elite9)
    detalhes_base["Candidatos Elite X"] = int(candidatos_elite_x)
    detalhes = []
    concursos_ordenados = sorted(detalhes_base["Concurso"].astype(int).unique())
    total_concursos = len(concursos_ordenados)
    for janela in JANELAS_PADRAO:
        nome, tamanho = _nome_janela(janela, total_concursos)
        concursos_janela = set(concursos_ordenados[-tamanho:])
        recorte = detalhes_base[detalhes_base["Concurso"].astype(int).isin(concursos_janela)].copy()
        recorte.insert(0, "Janela", nome)
        detalhes.append(recorte)

    detalhes_final = pd.concat(detalhes, ignore_index=True)
    resumo = resumir_auditoria_elite_x(detalhes_base)
    caminho_resumo = export_path / "auditoria_elite_x_resumo.csv"
    caminho_detalhado = export_path / "auditoria_elite_x_detalhada.csv"
    resumo.to_csv(caminho_resumo, index=False, encoding="utf-8-sig")
    detalhes_final.to_csv(caminho_detalhado, index=False, encoding="utf-8-sig")
    return {
        "resumo": resumo,
        "detalhes": detalhes_final,
        "caminho_resumo": caminho_resumo,
        "caminho_detalhado": caminho_detalhado,
    }


if __name__ == "__main__":
    resultado = executar_auditoria_elite_x_completa()
    print(resultado["resumo"].to_string(index=False))
    print(f"RESUMO={Path(resultado['caminho_resumo']).resolve()}")
    print(f"DETALHADO={Path(resultado['caminho_detalhado']).resolve()}")

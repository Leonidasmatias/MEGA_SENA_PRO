from __future__ import annotations

from itertools import combinations
from pathlib import Path
import random

import pandas as pd

from src.auditoria_elite8 import parse_jogo
from src.auditoria_elite9 import PONTOS_PREMIACAO
from src.auditoria_elite9_banco_mestre import _selecionar_top_n_diverso
from src.auditoria_elite9_20_dezenas import PontuadorElite9Expandido
from src.carregar_dados import COLUNAS_DEZENAS, carregar_base
from src.elite9_motor import gerar_portfolio_elite9


def _normalizar_banco(banco: list[int] | tuple[int, ...]) -> tuple[int, ...]:
    dezenas = tuple(sorted(int(dezena) for dezena in banco))
    if len(dezenas) != 30 or len(set(dezenas)) != 30:
        raise ValueError("O Banco Mestre do Elite X deve conter exatamente 30 dezenas unicas.")
    if any(dezena < 1 or dezena > 60 for dezena in dezenas):
        raise ValueError("As dezenas do banco devem estar entre 1 e 60.")
    return dezenas


def _normalizar_jogo(jogo: list[int] | tuple[int, ...]) -> tuple[int, ...]:
    dezenas = tuple(sorted(int(dezena) for dezena in jogo))
    if len(dezenas) != 6 or len(set(dezenas)) != 6:
        raise ValueError("Cada jogo deve conter exatamente 6 dezenas unicas.")
    return dezenas


def _formatar(dezenas: list[int] | tuple[int, ...] | set[int]) -> str:
    return " - ".join(f"{int(dezena):02d}" for dezena in sorted(dezenas))


def gerar_banco_mestre_30(historico: pd.DataFrame | None = None) -> list[int]:
    dados = historico if historico is not None else carregar_base()
    dados = dados.sort_values("Concurso", ascending=True).reset_index(drop=True)
    pontuador = PontuadorElite9Expandido()
    for _, linha in dados.iterrows():
        dezenas = tuple(sorted(int(linha[coluna]) for coluna in COLUNAS_DEZENAS))
        pontuador.adicionar_concurso(int(linha["Concurso"]), dezenas)
    ranking = pontuador.pontuar_dezenas()
    return _selecionar_top_n_diverso(ranking, 30)


def calcular_quantidade_jogos_por_orcamento(orcamento: float, valor_aposta_simples: float = 5.0) -> int:
    if valor_aposta_simples <= 0:
        raise ValueError("O valor da aposta simples deve ser maior que zero.")
    if orcamento < 0:
        raise ValueError("O orcamento nao pode ser negativo.")
    return int(float(orcamento) // float(valor_aposta_simples))


def gerar_combinacoes_30_dezenas(
    banco_mestre: list[int] | tuple[int, ...],
    quantidade_candidatos: int = 20000,
    seed: int | None = 10,
) -> list[tuple[int, ...]]:
    banco = _normalizar_banco(banco_mestre)
    total_combinacoes = 593775
    quantidade_candidatos = max(1, min(int(quantidade_candidatos), total_combinacoes))
    if quantidade_candidatos >= total_combinacoes:
        return [tuple(comb) for comb in combinations(banco, 6)]

    rng = random.Random(seed)
    candidatos: set[tuple[int, ...]] = set()
    tentativas = 0
    limite = quantidade_candidatos * 12
    while len(candidatos) < quantidade_candidatos and tentativas < limite:
        tentativas += 1
        candidatos.add(tuple(sorted(rng.sample(banco, 6))))
    return list(candidatos)


def calcular_cobertura_duplas(jogos: list[list[int] | tuple[int, ...]], banco_mestre: list[int] | tuple[int, ...]) -> float:
    banco = _normalizar_banco(banco_mestre)
    cobertas = set()
    for jogo in jogos:
        cobertas.update(tuple(par) for par in combinations(_normalizar_jogo(jogo), 2))
    total = len(list(combinations(banco, 2)))
    return round(len(cobertas) / total * 100 if total else 0.0, 6)


def calcular_cobertura_trincas(jogos: list[list[int] | tuple[int, ...]], banco_mestre: list[int] | tuple[int, ...]) -> float:
    banco = _normalizar_banco(banco_mestre)
    cobertas = set()
    for jogo in jogos:
        cobertas.update(tuple(trinca) for trinca in combinations(_normalizar_jogo(jogo), 3))
    total = len(list(combinations(banco, 3)))
    return round(len(cobertas) / total * 100 if total else 0.0, 6)


def calcular_cobertura_quadras(jogos: list[list[int] | tuple[int, ...]], banco_mestre: list[int] | tuple[int, ...]) -> float:
    banco = _normalizar_banco(banco_mestre)
    cobertas = set()
    for jogo in jogos:
        cobertas.update(tuple(quadra) for quadra in combinations(_normalizar_jogo(jogo), 4))
    total = len(list(combinations(banco, 4)))
    return round(len(cobertas) / total * 100 if total else 0.0, 6)


def calcular_redundancia(jogos: list[list[int] | tuple[int, ...]]) -> float:
    normalizados = [_normalizar_jogo(jogo) for jogo in jogos]
    if len(normalizados) < 2:
        return 0.0
    sobreposicoes = []
    for jogo_a, jogo_b in combinations(normalizados, 2):
        sobreposicoes.append(len(set(jogo_a) & set(jogo_b)) / 6)
    return round(sum(sobreposicoes) / len(sobreposicoes) * 100, 6)


def score_fechamento(jogos: list[list[int] | tuple[int, ...]], banco_mestre: list[int] | tuple[int, ...]) -> float:
    if not jogos:
        return 0.0
    duplas = calcular_cobertura_duplas(jogos, banco_mestre)
    trincas = calcular_cobertura_trincas(jogos, banco_mestre)
    quadras = calcular_cobertura_quadras(jogos, banco_mestre)
    redundancia = calcular_redundancia(jogos)
    score = duplas * 0.25 + trincas * 0.35 + quadras * 0.30 + max(0.0, 100.0 - redundancia) * 0.10
    return round(max(0.0, min(100.0, score)), 6)


def _margem_cobertura(
    jogo: tuple[int, ...],
    duplas: set[tuple[int, int]],
    trincas: set[tuple[int, int, int]],
    quadras: set[tuple[int, int, int, int]],
    selecionados: list[tuple[int, ...]],
) -> float:
    novas_duplas = len(set(combinations(jogo, 2)) - duplas)
    novas_trincas = len(set(combinations(jogo, 3)) - trincas)
    novas_quadras = len(set(combinations(jogo, 4)) - quadras)
    penalidade = 0.0
    if selecionados:
        maior_sobreposicao = max(len(set(jogo) & set(outro)) for outro in selecionados)
        penalidade = maior_sobreposicao * 2.5
    return novas_duplas * 1.0 + novas_trincas * 2.2 + novas_quadras * 4.5 - penalidade


def otimizar_fechamento(
    banco_mestre: list[int] | tuple[int, ...],
    quantidade_jogos: int,
    quantidade_candidatos: int = 20000,
    seed: int | None = 10,
) -> pd.DataFrame:
    banco = _normalizar_banco(banco_mestre)
    quantidade_jogos = max(0, int(quantidade_jogos))
    if quantidade_jogos == 0:
        return pd.DataFrame()

    candidatos = gerar_combinacoes_30_dezenas(banco, quantidade_candidatos=quantidade_candidatos, seed=seed)
    selecionados: list[tuple[int, ...]] = []
    duplas: set[tuple[int, int]] = set()
    trincas: set[tuple[int, int, int]] = set()
    quadras: set[tuple[int, int, int, int]] = set()
    restantes = set(candidatos)

    while restantes and len(selecionados) < quantidade_jogos:
        melhor = max(restantes, key=lambda jogo: _margem_cobertura(jogo, duplas, trincas, quadras, selecionados))
        selecionados.append(melhor)
        restantes.remove(melhor)
        duplas.update(tuple(item) for item in combinations(melhor, 2))
        trincas.update(tuple(item) for item in combinations(melhor, 3))
        quadras.update(tuple(item) for item in combinations(melhor, 4))

    linhas = []
    parciais: list[tuple[int, ...]] = []
    for ranking, jogo in enumerate(selecionados, start=1):
        parciais.append(jogo)
        linhas.append(
            {
                "Ranking": ranking,
                "Jogo": _formatar(jogo),
                "Score cobertura": score_fechamento(parciais, banco),
                "Soma": sum(jogo),
                "Pares": sum(dezena % 2 == 0 for dezena in jogo),
                "Impares": sum(dezena % 2 != 0 for dezena in jogo),
            }
        )
    return pd.DataFrame(linhas)


def gerar_fechamento_elite_x(
    historico: pd.DataFrame | None = None,
    orcamento: float = 100.0,
    valor_aposta_simples: float = 5.0,
    quantidade_candidatos: int = 20000,
    seed: int | None = 10,
) -> dict[str, object]:
    dados = historico if historico is not None else carregar_base()
    banco = gerar_banco_mestre_30(dados)
    quantidade_jogos = calcular_quantidade_jogos_por_orcamento(orcamento, valor_aposta_simples)
    jogos = otimizar_fechamento(
        banco,
        quantidade_jogos=quantidade_jogos,
        quantidade_candidatos=quantidade_candidatos,
        seed=seed,
    )
    lista_jogos = [parse_jogo(jogo) for jogo in jogos["Jogo"].astype(str).tolist()] if not jogos.empty else []
    indicadores = {
        "Quantidade de jogos": quantidade_jogos,
        "Cobertura de dezenas": round(len(set().union(*[set(jogo) for jogo in lista_jogos])) / 30 * 100, 6) if lista_jogos else 0.0,
        "Cobertura de duplas": calcular_cobertura_duplas(lista_jogos, banco) if lista_jogos else 0.0,
        "Cobertura de trincas": calcular_cobertura_trincas(lista_jogos, banco) if lista_jogos else 0.0,
        "Cobertura de quadras": calcular_cobertura_quadras(lista_jogos, banco) if lista_jogos else 0.0,
        "Redundancia": calcular_redundancia(lista_jogos) if lista_jogos else 0.0,
        "Score final": score_fechamento(lista_jogos, banco) if lista_jogos else 0.0,
    }
    return {"banco_mestre": banco, "jogos": jogos, "indicadores": indicadores}


def exportar_fechamento_csv(fechamento: dict[str, object]) -> bytes:
    jogos = fechamento.get("jogos", pd.DataFrame())
    if not isinstance(jogos, pd.DataFrame):
        jogos = pd.DataFrame(jogos)
    return jogos.to_csv(index=False).encode("utf-8-sig")


def _medir_jogos(motor: str, concurso: int, jogos: list[list[int]], resultado: set[int]) -> dict:
    contagem = {acertos: 0 for acertos in range(7)}
    total_acertos = 0
    score_premiacao = 0
    melhor = 0
    for jogo in jogos:
        acertos = len(set(jogo) & resultado)
        contagem[acertos] += 1
        total_acertos += acertos
        score_premiacao += PONTOS_PREMIACAO.get(acertos, 0)
        melhor = max(melhor, acertos)
    total = len(jogos)
    return {
        "Motor": motor,
        "Concurso": concurso,
        "Total jogos": total,
        "Media de acertos": round(total_acertos / total, 6) if total else 0.0,
        "Melhor acerto": melhor,
        "Jogos com 4 acertos": contagem[4],
        "Jogos com 5 acertos": contagem[5],
        "Jogos com 6 acertos": contagem[6],
        "Score premiacao": score_premiacao,
        "Cobertura media": round((total_acertos / (total * 6) * 100), 6) if total else 0.0,
    }


def auditar_elite_x(
    quantidade_concursos: int = 50,
    orcamento: float = 100.0,
    valor_aposta_simples: float = 5.0,
    seed: int = 20260604,
) -> dict[str, pd.DataFrame]:
    rng = random.Random(seed)
    dados = carregar_base().sort_values("Concurso", ascending=True).reset_index(drop=True)
    concursos = dados.tail(max(1, min(int(quantidade_concursos), len(dados))))
    registros = []
    for _, linha in concursos.iterrows():
        concurso = int(linha["Concurso"])
        historico = dados[dados["Concurso"].astype(int) < concurso]
        resultado = {int(linha[coluna]) for coluna in COLUNAS_DEZENAS}
        quantidade_jogos = calcular_quantidade_jogos_por_orcamento(orcamento, valor_aposta_simples)

        banco_random = sorted(rng.sample(range(1, 61), 30))
        jogos_random = [sorted(rng.sample(banco_random, 6)) for _ in range(quantidade_jogos)]
        registros.append(_medir_jogos("Aleatorio 30 dezenas", concurso, jogos_random, resultado))

        elite9 = gerar_portfolio_elite9(
            historico,
            quantidade_candidatos=1000,
            geracoes=1,
            tamanho_populacao=max(50, quantidade_jogos),
            quantidade_final=quantidade_jogos,
            seed=seed + concurso,
            janela_historico=300,
        )
        jogos_elite9 = [parse_jogo(jogo) for jogo in elite9["Jogo"].astype(str).tolist()]
        registros.append(_medir_jogos("Elite 9 normal", concurso, jogos_elite9, resultado))

        fechamento = gerar_fechamento_elite_x(
            historico,
            orcamento=orcamento,
            valor_aposta_simples=valor_aposta_simples,
            quantidade_candidatos=3000,
            seed=seed + concurso,
        )
        jogos_x = [parse_jogo(jogo) for jogo in fechamento["jogos"]["Jogo"].astype(str).tolist()]
        medicao_x = _medir_jogos("Elite X Fechamento", concurso, jogos_x, resultado)
        medicao_x["Score combinatorio"] = fechamento["indicadores"]["Score final"]
        registros.append(medicao_x)

    detalhes = pd.DataFrame(registros)
    resumo = detalhes.groupby("Motor", as_index=False).agg(
        Concursos=("Concurso", "nunique"),
        Media_acertos=("Media de acertos", "mean"),
        Melhor_acerto=("Melhor acerto", "max"),
        Jogos_4=("Jogos com 4 acertos", "sum"),
        Jogos_5=("Jogos com 5 acertos", "sum"),
        Jogos_6=("Jogos com 6 acertos", "sum"),
        Score_premiacao=("Score premiacao", "sum"),
        Cobertura_media=("Cobertura media", "mean"),
    )
    return {"detalhes": detalhes, "resumo": resumo}

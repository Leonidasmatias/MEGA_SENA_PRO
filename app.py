from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from src.carregar_dados import (
    CAMINHO_BASE_PADRAO,
    FONTE_CAIXA_URL,
    atualizar_base_local,
    carregar_base,
    carregar_upload,
)
from src.estatisticas import (
    dezenas_atrasadas,
    dezenas_mais_sorteadas_ultimos_concursos,
    dezenas_mais_sorteadas,
    dezenas_menos_sorteadas_ultimos_concursos,
    dezenas_menos_sorteadas,
    estatistica_pares_impares,
    estatistica_soma_dezenas,
    padrao_jogo,
    resumo_base,
)
from src.gerador_jogos import gerar_jogo
from src.gerador_jogos import (
    backtest_completo,
    calcular_score_dezenas,
    classificar_confianca,
    dados_grafico_backtest,
    gerar_jogos_premium,
    gerar_varios_jogos_inteligentes,
    score_jogo,
    simular_monte_carlo,
    validar_algoritmo_historico,
)
from src.visualizacoes import grafico_frequencia


st.set_page_config(
    page_title="Mega Sena Analytics",
    page_icon="🎲",
    layout="wide",
)


def mostrar_jogo(dezenas: list[int]) -> None:
    colunas = st.columns(6)
    for coluna, dezena in zip(colunas, dezenas):
        coluna.markdown(
            f"""
            <div style="
                background:#0f8f4f;
                color:white;
                border-radius:8px;
                padding:14px 0;
                text-align:center;
                font-size:24px;
                font-weight:800;
            ">{dezena:02d}</div>
            """,
            unsafe_allow_html=True,
        )


def formatar_dezenas(dezenas: list[int]) -> str:
    return " - ".join(f"{dezena:02d}" for dezena in dezenas)


def obter_dados() -> pd.DataFrame | None:
    upload = st.file_uploader(
        "Upload opcional de CSV historico",
        type=["csv"],
        help="Use colunas: Concurso, Data, D1, D2, D3, D4, D5, D6.",
    )

    try:
        if upload is not None:
            return carregar_upload(upload)
        return carregar_base(CAMINHO_BASE_PADRAO)
    except FileNotFoundError:
        st.error(
            "Arquivo dados/mega_sena_historico.csv nao encontrado. "
            "Inclua a base historica no projeto antes do deploy."
        )
    except Exception as erro:
        st.error(f"Nao foi possivel carregar a base historica: {erro}")
    return None


def render_analise_avancada(df: pd.DataFrame) -> None:
    atrasadas = dezenas_atrasadas(df)
    pares_impares = estatistica_pares_impares(df)
    soma_dezenas = estatistica_soma_dezenas(df)
    padrao = padrao_jogo(df)

    st.markdown("### Ranking de dezenas atrasadas")
    st.dataframe(atrasadas.head(20), width="stretch", hide_index=True)

    st.markdown("### Estatistica de pares e impares")
    col_par, col_impar = st.columns(2)
    col_par.metric("Media de pares por concurso", f"{padrao['média de pares']:.2f}")
    col_impar.metric("Media de impares por concurso", f"{padrao['média de ímpares']:.2f}")
    st.dataframe(pares_impares.head(30), width="stretch", hide_index=True)

    st.markdown("### Soma das dezenas")
    col_soma1, col_soma2, col_soma3 = st.columns(3)
    col_soma1.metric("Soma media", f"{soma_dezenas['média']:.2f}")
    col_soma2.metric("Soma minima", soma_dezenas["mínima"])
    col_soma3.metric("Soma maxima", soma_dezenas["máxima"])
    st.dataframe(soma_dezenas["por_concurso"].head(30), width="stretch", hide_index=True)

    st.markdown("### Padrao geral de jogo")
    resumo_padrao = pd.DataFrame(
        [
            {
                "Media da soma": round(float(padrao["média da soma"]), 2),
                "Media de pares": round(float(padrao["média de pares"]), 2),
                "Media de impares": round(float(padrao["média de ímpares"]), 2),
            }
        ]
    )
    st.dataframe(resumo_padrao, width="stretch", hide_index=True)

    col_freq1, col_freq2, col_freq3 = st.columns(3)
    with col_freq1:
        st.caption("Mais frequentes")
        st.dataframe(padrao["dezenas mais frequentes"], width="stretch", hide_index=True)
    with col_freq2:
        st.caption("Menos frequentes")
        st.dataframe(padrao["dezenas menos frequentes"], width="stretch", hide_index=True)
    with col_freq3:
        st.caption("Mais atrasadas")
        st.dataframe(padrao["dezenas mais atrasadas"], width="stretch", hide_index=True)


def render_dezenas_quentes_frias(df: pd.DataFrame) -> None:
    mais_20 = dezenas_mais_sorteadas_ultimos_concursos(df, quantidade_concursos=20, limite=10)
    mais_50 = dezenas_mais_sorteadas_ultimos_concursos(df, quantidade_concursos=50, limite=10)
    menos_50 = dezenas_menos_sorteadas_ultimos_concursos(df, quantidade_concursos=50, limite=10)

    st.markdown("### Top 10 dezenas mais sorteadas nos ultimos 20 concursos")
    st.dataframe(mais_20, width="stretch", hide_index=True)

    st.markdown("### Top 10 dezenas mais sorteadas nos ultimos 50 concursos")
    st.dataframe(mais_50, width="stretch", hide_index=True)

    st.markdown("### Top 10 dezenas menos sorteadas nos ultimos 50 concursos")
    st.dataframe(menos_50, width="stretch", hide_index=True)


def render_gerador_inteligente(df: pd.DataFrame) -> None:
    ranking = calcular_score_dezenas(df)

    st.warning("Este gerador usa estatistica historica e nao garante premiacao.")
    st.markdown("### Ranking das 20 dezenas com maior score inteligente V2")
    st.dataframe(ranking.head(20), width="stretch", hide_index=True)

    quantidade = st.number_input("Quantidade de jogos", min_value=1, max_value=20, value=5, step=1)

    if st.button("Gerar Jogo Inteligente", type="primary"):
        st.session_state.jogos_inteligentes = gerar_varios_jogos_inteligentes(df, quantidade=int(quantidade))

    jogos = st.session_state.get("jogos_inteligentes", [])
    if jogos:
        linhas = []
        for indice, jogo in enumerate(jogos, start=1):
            pares = sum(dezena % 2 == 0 for dezena in jogo)
            score = score_jogo(df, jogo)
            linhas.append(
                {
                    "Jogo": indice,
                    "Dezenas": formatar_dezenas(jogo),
                    "Score": score,
                    "Classificacao": classificar_confianca(score),
                    "Soma": sum(jogo),
                    "Pares": pares,
                    "Impares": 6 - pares,
                }
            )

        st.markdown("### Jogos gerados")
        st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)


def render_jogos_premium(df: pd.DataFrame) -> None:
    st.warning("Jogos Premium usam estatistica historica e nao garantem premiacao.")
    st.caption("As estrategias V2 alternam jogos Conservador, Equilibrado e Agressivo.")
    quantidade = st.selectbox("Quantidade de jogos premium", options=[3, 6, 9, 12], index=1)

    if st.button("Gerar Jogos Premium", type="primary"):
        st.session_state.jogos_premium = gerar_jogos_premium(df, quantidade=int(quantidade))

    jogos = st.session_state.get("jogos_premium", [])
    if jogos:
        linhas = [
            {
                "Jogo": jogo["jogo"],
                "Estrategia": jogo["estrategia"],
                "Dezenas": formatar_dezenas(jogo["dezenas"]),
                "Score": jogo["score"],
                "Classificacao": jogo["classificacao"],
                "Soma": jogo["soma"],
                "Pares": jogo["pares"],
                "Impares": jogo["impares"],
            }
            for jogo in jogos
        ]
        st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)


def render_validacao_historica(df: pd.DataFrame) -> None:
    st.warning("Validacao historica nao garante resultado futuro.")
    quantidade = st.selectbox("Quantidade de concursos para testar", options=[100, 300, 500], index=2)

    if st.button("Executar Validacao Historica", type="primary"):
        st.session_state.validacao_historica = validar_algoritmo_historico(df, quantidade_concursos=int(quantidade))

    resultado = st.session_state.get("validacao_historica")
    if resultado:
        col1, col2, col3 = st.columns(3)
        col1.metric("Concursos analisados", resultado["concursos analisados"])
        col2.metric("Total de jogos simulados", resultado["total de jogos simulados"])
        col3.metric("Melhor resultado", f"{resultado['melhor resultado']} acertos")

        cols_acertos = st.columns(7)
        for acertos, coluna in enumerate(cols_acertos):
            chave = "quantidade de 1 acerto" if acertos == 1 else f"quantidade de {acertos} acertos"
            coluna.metric(f"{acertos} acertos", resultado[chave])

        col_taxa_3, col_taxa_4 = st.columns(2)
        col_taxa_3.metric("Taxa 3+ acertos", f"{resultado['taxa de jogos com 3+ acertos']:.2f}%")
        col_taxa_4.metric("Taxa 4+ acertos", f"{resultado['taxa de jogos com 4+ acertos']:.2f}%")


def render_backtest_completo(df: pd.DataFrame) -> None:
    st.warning("Backtest historico nao garante resultado futuro.")
    quantidade = st.selectbox("Quantidade de concursos para o backtest", options=[100, 300, 500], index=2)

    if st.button("Executar Backtest Completo", type="primary"):
        st.session_state.backtest_completo = backtest_completo(df, quantidade_concursos=int(quantidade))
        st.session_state.grafico_backtest = dados_grafico_backtest(df, quantidade_concursos=int(quantidade))

    resultado = st.session_state.get("backtest_completo")
    grafico = st.session_state.get("grafico_backtest")
    if resultado is not None:
        st.markdown("### 20 melhores resultados")
        st.dataframe(resultado, width="stretch", hide_index=True)

    if grafico is not None and not grafico.empty:
        figura = px.bar(grafico, x="Concurso", y="Acertos", title="Acertos por Concurso no Backtest")
        st.plotly_chart(figura, width="stretch")


def render_monte_carlo(df: pd.DataFrame) -> None:
    st.warning("Simulacao Monte Carlo nao garante resultado futuro.")
    quantidade = st.selectbox("Quantidade de simulacoes", options=[10000, 50000, 100000], index=0)

    if st.button("Executar Monte Carlo", type="primary"):
        st.session_state.monte_carlo = simular_monte_carlo(df, quantidade_simulacoes=int(quantidade))

    resultado = st.session_state.get("monte_carlo")
    if resultado:
        st.dataframe(resultado["simulacoes"], width="stretch", hide_index=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("### Dezenas mais recorrentes")
            st.dataframe(resultado["dezenas"], width="stretch", hide_index=True)
            if not resultado["dezenas"].empty:
                st.plotly_chart(px.bar(resultado["dezenas"], x="Dezena formatada", y="Ocorrencias"), width="stretch")
        with col2:
            st.markdown("### Pares mais recorrentes")
            st.dataframe(resultado["pares"], width="stretch", hide_index=True)
        with col3:
            st.markdown("### Trincas mais recorrentes")
            st.dataframe(resultado["trincas"], width="stretch", hide_index=True)


def _pdf_escape(texto: object) -> str:
    return str(texto).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _quebrar_linha(texto: str, limite: int = 96) -> list[str]:
    palavras = texto.split()
    linhas: list[str] = []
    atual = ""
    for palavra in palavras:
        candidato = f"{atual} {palavra}".strip()
        if len(candidato) > limite and atual:
            linhas.append(atual)
            atual = palavra
        else:
            atual = candidato
    if atual:
        linhas.append(atual)
    return linhas or [""]


def criar_pdf_texto(linhas: list[str]) -> bytes:
    linhas_por_pagina = 58
    paginas = [linhas[indice : indice + linhas_por_pagina] for indice in range(0, len(linhas), linhas_por_pagina)]
    if not paginas:
        paginas = [["Relatorio Mega Sena Pro"]]

    objetos: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    ids_paginas: list[int] = []
    proximo_id = 4
    for pagina in paginas:
        page_id = proximo_id
        content_id = proximo_id + 1
        proximo_id += 2
        ids_paginas.append(page_id)
        comandos = ["BT", "/F1 10 Tf", "50 800 Td", "12 TL"]
        for linha in pagina:
            comandos.append(f"({_pdf_escape(linha)}) Tj")
            comandos.append("T*")
        comandos.append("ET")
        conteudo = "\n".join(comandos).encode("latin-1", errors="replace")
        objetos[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("latin-1")
        objetos[content_id] = b"<< /Length " + str(len(conteudo)).encode("ascii") + b" >>\nstream\n" + conteudo + b"\nendstream"

    kids = " ".join(f"{page_id} 0 R" for page_id in ids_paginas)
    objetos[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(ids_paginas)} >>".encode("latin-1")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = {0: 0}
    for obj_id in sorted(objetos):
        offsets[obj_id] = len(pdf)
        pdf.extend(f"{obj_id} 0 obj\n".encode("ascii"))
        pdf.extend(objetos[obj_id])
        pdf.extend(b"\nendobj\n")
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {max(objetos) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for obj_id in range(1, max(objetos) + 1):
        pdf.extend(f"{offsets.get(obj_id, 0):010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {max(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode("ascii")
    )
    return bytes(pdf)


def gerar_relatorio_pdf(df: pd.DataFrame) -> bytes:
    resumo = resumo_base(df)
    ranking = calcular_score_dezenas(df)
    jogos_premium = gerar_jogos_premium(df, quantidade=3)
    validacao = validar_algoritmo_historico(df, quantidade_concursos=100)
    backtest = backtest_completo(df, quantidade_concursos=100)
    soma = estatistica_soma_dezenas(df)

    linhas = [
        "Mega Sena Pro - Relatorio Estatistico",
        f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "Backtests e simulacoes historicas nao garantem resultado futuro.",
        "",
        "Resumo executivo",
        f"Total de concursos: {resumo['total_concursos']}",
        f"Primeiro concurso: {resumo['primeiro_concurso']}",
        f"Ultimo concurso: {resumo['ultimo_concurso']}",
        f"Media da soma dos concursos: {float(soma['média']):.2f}",
        "",
        "Top 10 dezenas por score",
    ]
    for _, linha in ranking.head(10).iterrows():
        linhas.append(f"{linha['Dezena formatada']} - Score {linha['Score']} - {linha['Tendencia']}")

    linhas.extend(["", "Jogos Premium V2"])
    for jogo in jogos_premium:
        linhas.append(
            f"Jogo {jogo['jogo']} ({jogo['estrategia']}): {formatar_dezenas(jogo['dezenas'])} "
            f"- Score {jogo['score']} - {jogo['classificacao']}"
        )

    linhas.extend(
        [
            "",
            "Validacao historica",
            f"Concursos analisados: {validacao['concursos analisados']}",
            f"Melhor resultado: {validacao['melhor resultado']} acertos",
            f"Taxa 3+ acertos: {validacao['taxa de jogos com 3+ acertos']:.2f}%",
            f"Taxa 4+ acertos: {validacao['taxa de jogos com 4+ acertos']:.2f}%",
            "",
            "Backtest - melhores resultados",
        ]
    )
    for _, linha in backtest.head(10).iterrows():
        linhas.append(
            f"Concurso {linha['Concurso']} - {linha['Acertos']} acertos - "
            f"Jogo {linha['Jogo gerado']} - Oficial {linha['Resultado oficial']}"
        )

    linhas_quebradas: list[str] = []
    for linha in linhas:
        linhas_quebradas.extend(_quebrar_linha(linha))
    return criar_pdf_texto(linhas_quebradas)


def render_dashboard(df: pd.DataFrame) -> None:
    resumo = resumo_base(df)
    ranking = calcular_score_dezenas(df)
    atrasadas = dezenas_atrasadas(df)
    soma = estatistica_soma_dezenas(df)
    pares_impares = estatistica_pares_impares(df)

    quentes = ", ".join(ranking.head(5)["Dezena formatada"].astype(str))
    frias = ", ".join(ranking.tail(5).sort_values("Score")["Dezena formatada"].astype(str))
    atraso_maximo = int(atrasadas["Atraso"].max())

    col1, col2, col3 = st.columns(3)
    col1.metric("Total concursos", resumo["total_concursos"])
    col2.metric("Atraso maximo", atraso_maximo)
    col3.metric("Media da soma", f"{float(soma['média']):.2f}")

    col4, col5 = st.columns(2)
    col4.metric("Dezenas mais quentes", quentes)
    col5.metric("Dezenas mais frias", frias)

    distribuicao = pares_impares.groupby("Pares").size().reset_index(name="Concursos")
    distribuicao["Padrao"] = distribuicao["Pares"].astype(str) + " pares / " + (6 - distribuicao["Pares"]).astype(str) + " impares"

    st.plotly_chart(
        px.bar(ranking.head(10), x="Dezena formatada", y="Score", title="Top 10 dezenas por score"),
        width="stretch",
    )
    col_graf1, col_graf2 = st.columns(2)
    with col_graf1:
        st.plotly_chart(px.pie(distribuicao, names="Padrao", values="Concursos", title="Distribuicao par/impar"), width="stretch")
    with col_graf2:
        st.plotly_chart(px.bar(atrasadas.head(10), x="Dezena formatada", y="Atraso", title="Top 10 atrasos"), width="stretch")

    st.download_button(
        "Exportar Relatório",
        data=gerar_relatorio_pdf(df),
        file_name="mega_sena_pro_relatorio.pdf",
        mime="application/pdf",
    )


def main() -> None:
    st.title("Mega Sena Analytics")
    st.caption(
        "Analise estatistica da Mega-Sena com base historica local. "
        "As sugestoes sao estatisticas e nao garantem premiacao."
    )
    st.info("Base historica: dados obtidos da pagina oficial da CAIXA. Consulte a fonte oficial para validacao.")
    st.link_button("Conferir resultados oficiais na CAIXA", FONTE_CAIXA_URL)
    st.caption("Este sistema utiliza estatistica historica e nao possui vinculo oficial com a CAIXA.")

    if st.session_state.pop("base_oficial_atualizada", False):
        st.success("Base oficial atualizada com sucesso.")

    if st.button("Atualizar base oficial"):
        if atualizar_base_local():
            st.session_state.base_oficial_atualizada = True
            st.rerun()
        else:
            st.warning("Nao foi possivel atualizar pela CAIXA neste momento. Usando base local.")

    df = obter_dados()
    if df is None:
        st.stop()

    resumo = resumo_base(df)
    col1, col2, col3 = st.columns(3)
    col1.metric("Concursos carregados", resumo["total_concursos"])
    col2.metric("Primeiro concurso", resumo["primeiro_concurso"])
    col3.metric("Ultimo concurso", resumo["ultimo_concurso"])

    st.subheader("Concursos carregados")
    st.dataframe(df.head(30), width="stretch", hide_index=True)

    st.subheader("Analise estatistica")
    mais = dezenas_mais_sorteadas(df, limite=10)
    menos = dezenas_menos_sorteadas(df, limite=10)

    (
        tab1,
        tab2,
        tab3,
        tab4,
        tab5,
        tab6,
        tab7,
        tab8,
        tab9,
        tab10,
        tab11,
    ) = st.tabs(
        [
            "Dezenas mais sorteadas",
            "Dezenas menos sorteadas",
            "Grafico geral",
            "Analise Avancada",
            "Dezenas Quentes e Frias",
            "Gerador Inteligente",
            "Jogos Premium",
            "Validacao Historica",
            "Backtest Completo",
            "Monte Carlo",
            "Dashboard",
        ]
    )
    with tab1:
        st.dataframe(mais, width="stretch", hide_index=True)
    with tab2:
        st.dataframe(menos, width="stretch", hide_index=True)
    with tab3:
        st.plotly_chart(grafico_frequencia(df), width="stretch")
    with tab4:
        render_analise_avancada(df)
    with tab5:
        render_dezenas_quentes_frias(df)
    with tab6:
        render_gerador_inteligente(df)
    with tab7:
        render_jogos_premium(df)
    with tab8:
        render_validacao_historica(df)
    with tab9:
        render_backtest_completo(df)
    with tab10:
        render_monte_carlo(df)
    with tab11:
        render_dashboard(df)

    st.subheader("Gerador de jogos")
    st.write("Gere jogos com 6 dezenas combinando frequencia historica e aleatoriedade.")

    if "jogo_gerado" not in st.session_state:
        st.session_state.jogo_gerado = gerar_jogo(df)

    if st.button("Gerar novo jogo", type="primary"):
        st.session_state.jogo_gerado = gerar_jogo(df)

    mostrar_jogo(st.session_state.jogo_gerado)

    st.divider()
    st.caption("Este projeto nao possui vinculo com a Caixa Economica Federal. Use com responsabilidade.")


if __name__ == "__main__":
    main()
